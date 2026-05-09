import logging
import threading
import time
from datetime import datetime
from langchain.schema.document import Document
from appwrite.query import Query
from appwrite.id import ID

from .vector_store import get_vector_store, add_documents_with_retry
from .retention import enforce_retention_for_user

_worker_started = False
_worker_thread = None
_worker_lock = threading.Lock()

BATCH_SIZE = 16
SLEEP_WHEN_IDLE = 5


def start_worker_once(app):
    """start a single ingestion worker thread. Uses appwriteDB as queue"""
    global _worker_started, _worker_thread
    if _worker_started:
        return

    with _worker_lock:
        if _worker_started:
            return

        def _run():
            with app.app_context():
                logging.info("Ingestion worker loop starting")
                recover_stuck_jobs()
                while True:
                    try:
                        jobs = load_pending_jobs(limit=3)
                        if not jobs:
                            time.sleep(SLEEP_WHEN_IDLE)
                            continue
                        for job in jobs:
                            process_job(job)
                    except Exception as loop_err:
                        logging.error(f"Ingestion worker loop error: {loop_err}")
                        time.sleep(2)

        _worker_thread = threading.Thread(target=_run, name="ingestion-worker", daemon=True)
        _worker_thread.start()
        _worker_started = True


def recover_stuck_jobs():
    """Any job left in running is set back to pending on startup/restart"""
    from app import databases, db_id, jobs_collection_id
    try:
        stuck = databases.list_documents(
            db_id, jobs_collection_id,
            queries=[Query.equal('status', 'running')]
        )
        for job in stuck['documents']:
            databases.update_document(
                db_id, jobs_collection_id, job['$id'],
                {'status': 'pending', 'errorMessage': 'recovered after restart'}
            )
        if stuck.get('total', 0) > 0:
            logging.info(f"Recovered {stuck['total']} stuck jobs")
    except Exception as exc:
        logging.error(f"Failed to recover stuck jobs: {exc}")


def load_pending_jobs(limit=3):
    from app import databases, db_id, jobs_collection_id
    try:
        res = databases.list_documents(
            db_id, jobs_collection_id,
            queries=[
                Query.equal('status', 'pending'),
                Query.order_asc('$createdAt'),
                Query.limit(limit)
            ]
        )
        return res.get('documents', [])
    except Exception as exc:
        logging.error(f"Failed to load pending jobs: {exc}")
        return []


def process_job(job):
    from app import databases, db_id, docs_collection_id, chunks_collection_id, jobs_collection_id
    job_id = job['$id']
    user_id = job.get('userId')
    document_id = job.get('documentId')
    conversation_id = job.get('conversationId')
    logging.info(f"[job:{job_id}] Starting ingestion for document {document_id}")

    try:
        databases.update_document(
            db_id, jobs_collection_id, job_id,
            {'status': 'running', 'attempts': (job.get('attempts', 0) + 1)}
        )
        # mark doc ingesting
        databases.update_document(
            db_id, docs_collection_id, document_id,
            {'status': 'ingesting'}
        )

        doc_record = databases.get_document(db_id, docs_collection_id, document_id)
        file_hash = doc_record.get('fileHash')

        chunks_res = databases.list_documents(
            db_id, chunks_collection_id,
            queries=[Query.equal('documentId', document_id), Query.limit(500)]
        )
        chunks = chunks_res.get('documents', [])
        if not chunks:
            raise RuntimeError("No chunks found for document")

        store = get_vector_store()

        docs_to_add = []
        ids_to_add = []
        for ch in chunks:
            chunk_hash = ch.get('chunkHash')
            # skip if already present
            existing = store.get(where={'chunk_hash': chunk_hash}, include=[])
            if existing and existing.get('ids'):
                continue
            meta = {
                'chunk_hash': chunk_hash,
                'file_hash': file_hash,
                'document_id': document_id,
                'conversation_id': conversation_id,
                'user_id': user_id,
            }
            doc = Document(page_content=ch.get('text', ''), metadata=meta)
            docs_to_add.append(doc)
            ids_to_add.append(chunk_hash)

        # batch writes
        for i in range(0, len(docs_to_add), BATCH_SIZE):
            batch_docs = docs_to_add[i:i+BATCH_SIZE]
            batch_ids = ids_to_add[i:i+BATCH_SIZE]
            add_documents_with_retry(store, batch_docs, batch_ids)

        now_iso = datetime.now().isoformat()
        databases.update_document(
            db_id, docs_collection_id, document_id,
            {'status': 'ready', 'lastUsedAt': now_iso, 'chunkCount': len(chunks)}
        )
        databases.update_document(
            db_id, jobs_collection_id, job_id,
            {'status': 'done', 'errorMessage': ''}
        )
        logging.info(f"[job:{job_id}] Ingestion complete, added {len(docs_to_add)} new chunks")

        enforce_retention_for_user(user_id)

    except Exception as exc:
        logging.error(f"[job:{job_id}] Failed: {exc}")
        databases.update_document(
            db_id, jobs_collection_id, job_id,
            {'status': 'failed', 'errorMessage': str(exc)}
        )
        if document_id:
            databases.update_document(
                db_id, docs_collection_id, document_id,
                {'status': 'failed'}
            )
