import logging
import threading
import time
from datetime import datetime
from langchain.schema.document import Document
from appwrite.query import Query

from .vector_store import get_vector_store, add_documents_with_retry
from .retention import enforce_retention_for_user
from .appwrite_utils import ( rel_id, DOC_PROCESSING, DOC_COMPLETED, DOC_FAILED, JOB_PENDING, JOB_PROCESSING, JOB_COMPLETED, JOB_FAILED )

_worker_started = False
_worker_thread = None
_worker_lock = threading.Lock()

BATCH_SIZE = 16
SLEEP_WHEN_IDLE = 5


def start_worker_once(app):
    """start a single ingestion worker thread. Uses appwrite db"""
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
    """Any job left in processing is set back to pending on startup/restart"""
    from app import databases, db_id, jobs_collection_id
    try:
        stuck = databases.list_documents(
            db_id, jobs_collection_id,
            queries=[Query.equal('status', JOB_PROCESSING)]
        )

        legacy = databases.list_documents(
            db_id, jobs_collection_id,
            queries=[Query.equal('status', 'running')]
        )
        stuck_jobs = {job['$id']: job for job in stuck.get('documents', [])}
        for job in legacy.get('documents', []):
            stuck_jobs[job['$id']] = job
        for job in stuck_jobs.values():
            databases.update_document(
                db_id, jobs_collection_id, job['$id'],
                {'status': JOB_PENDING, 'errorMessage': 'recovered after restart'}
            )
        if stuck_jobs:
            logging.info(f"Recovered {len(stuck_jobs)} stuck jobs")
    except Exception as exc:
        logging.error(f"Failed to recover stuck jobs: {exc}")


def load_pending_jobs(limit=3):
    from app import databases, db_id, jobs_collection_id
    try:
        res = databases.list_documents(
            db_id, jobs_collection_id,
            queries=[
                Query.equal('status', JOB_PENDING),
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
    user_id = rel_id(job.get('userId'))
    document_id = rel_id(job.get('documentId'))
    conversation_id = rel_id(job.get('conversationId'))
    logging.info(f"[job:{job_id}] Starting ingestion for document {document_id}")

    if not document_id:
        logging.error(f"[job:{job_id}] Missing documentId on job")
        databases.update_document(
            db_id, jobs_collection_id, job_id,
            {'status': JOB_FAILED, 'errorMessage': 'missing documentId'}
        )
        return
    
    try:
        logging.info(f"Jobs colln id: {jobs_collection_id}")
        logging.info(f"Job id: {job_id}")
        databases.update_document(
            db_id, jobs_collection_id, job_id,
            {'status': JOB_PROCESSING, 'attempts': (job.get('attempts', 0) + 1)}
        )
        databases.update_document(
            db_id, docs_collection_id, document_id,
            {'status': DOC_PROCESSING}
        )

        doc_record = databases.get_document(db_id, docs_collection_id, document_id)
        file_hash = doc_record.get('fileHash')

        if not user_id:
            user_id = rel_id(doc_record.get('userId'))
        if not conversation_id:
            conversation_id = rel_id(doc_record.get('conversationId'))

        conv_rel = doc_record.get('conversationId')
        auth_user_id = conv_rel.get('userId') if isinstance(conv_rel, dict) else None

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
            meta = {
                'chunk_hash': chunk_hash,
                'file_hash': file_hash,
                'document_id': document_id,
                'conversation_id': conversation_id,
                'user_id': auth_user_id or user_id,
            }
            doc = Document(page_content=ch.get('text', ''), metadata=meta)
            docs_to_add.append(doc)
            ids_to_add.append(chunk_hash)

        for i in range(0, len(docs_to_add), BATCH_SIZE):
            batch_docs = docs_to_add[i:i+BATCH_SIZE]
            batch_ids = ids_to_add[i:i+BATCH_SIZE]
            current_batch = (i // BATCH_SIZE) + 1
            total_batches = (len(docs_to_add) + BATCH_SIZE - 1)
            logging.info(f"[job:{job_id}] processing batch {current_batch}/{total_batches} ({len(batch_docs)} chunks)...")
            add_documents_with_retry(store, batch_docs, batch_ids)
            logging.info(f"[job:{job_id}] batch {current_batch} complete")


        now_iso = datetime.now().isoformat()
        databases.update_document(
            db_id, docs_collection_id, document_id,
            {'status': DOC_COMPLETED, 'lastUsedAt': now_iso, 'chunkCount': len(chunks)}
        )
        databases.update_document(
            db_id, jobs_collection_id, job_id,
            {'status': JOB_COMPLETED, 'errorMessage': ''}
        )
        logging.info(f"[job:{job_id}] Ingestion complete, added {len(docs_to_add)} new chunks")

        if user_id:
            enforce_retention_for_user(user_id)

    except Exception as exc:
        logging.error(f"[job:{job_id}] Failed: {exc}")
        databases.update_document(
            db_id, jobs_collection_id, job_id,
            {'status': JOB_FAILED, 'errorMessage': str(exc)}
        )
        try:
            databases.update_document(
                db_id, docs_collection_id, document_id,
                {'status': DOC_FAILED}
            )
        except Exception as doc_exc:
            logging.error(f"[job:{job_id}] Could not mark document failed: {doc_exc}")