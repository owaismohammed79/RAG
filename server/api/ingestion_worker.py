import logging
import threading
import time
from datetime import datetime
from langchain.schema.document import Document

from .vector_store import get_vector_store, add_documents_with_retry
from .retention import enforce_retention_for_user

_worker_started = False
_worker_thread = None
_worker_lock = threading.Lock()

BATCH_SIZE = 16
SLEEP_WHEN_IDLE = 5


def start_worker_once(app):
    """Start a single ingestion worker thread. Using supabase db"""
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
    from flask import current_app
    supabase = current_app.supabase
    try:
        res = supabase.table("ingestion_jobs").select("*").in_("status", ["processing", "running"]).execute()
        
        stuck_jobs = res.data or []
        for job in stuck_jobs:
            supabase.table("ingestion_jobs").update({
                "status": "pending",
                "error_message": "recovered after restart"
            }).eq("id", job["id"]).execute()

        if stuck_jobs:
            logging.info(f"Recovered {len(stuck_jobs)} stuck jobs")
    except Exception as exc:
        logging.error(f"Failed to recover stuck jobs: {exc}")


def load_pending_jobs(limit=3):
    from flask import current_app
    supabase = current_app.supabase
    try:
        res = supabase.table("ingestion_jobs").select("*").eq("status", "pending").order("created_at", desc=False).limit(limit).execute()
        return res.data or []
    except Exception as exc:
        logging.error(f"Failed to load pending jobs: {exc}")
        return []


def process_job(job):
    from flask import current_app
    supabase = current_app.supabase
    
    job_id = job["id"]
    user_id = job.get("user_id")
    document_id = job.get("document_id")
    conversation_id = job.get("conversation_id")
    logging.info(f"[job:{job_id}] Starting ingestion for document {document_id}")

    if not document_id:
        logging.error(f"[job:{job_id}] Missing documentId on job")
        supabase.table("ingestion_jobs").update({
            "status": "failed",
            "error_message": "missing documentId"
        }).eq("id", job_id).execute()
        return
    
    try:
        supabase.table("ingestion_jobs").update({
            "status": "processing",
            "attempts": (job.get("attempts", 0) + 1)
        }).eq("id", job_id).execute()

        supabase.table("documents").update({
            "status": "processing"
        }).eq("id", document_id).execute()

        doc_res = supabase.table("documents").select("*").eq("id", document_id).execute()
        if not doc_res.data:
            raise RuntimeError(f"Document {document_id} not found")
        doc_record = doc_res.data[0]
        file_hash = doc_record.get("file_hash")

        if not user_id:
            user_id = doc_record.get("user_id")
        if not conversation_id:
            conversation_id = doc_record.get("conversation_id")

        chunks_res = supabase.table("chunks").select("*").eq("document_id", document_id).limit(500).execute()
        chunks = chunks_res.data or []
        if not chunks:
            raise RuntimeError("No chunks found for document")

        store = get_vector_store()

        docs_to_add = []
        ids_to_add = []
        for ch in chunks:
            chunk_hash = ch.get("chunk_hash")
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

        for i in range(0, len(docs_to_add), BATCH_SIZE):
            batch_docs = docs_to_add[i:i+BATCH_SIZE]
            batch_ids = ids_to_add[i:i+BATCH_SIZE]
            current_batch = (i // BATCH_SIZE) + 1
            total_batches = (len(docs_to_add) + BATCH_SIZE - 1)
            logging.info(f"[job:{job_id}] processing batch {current_batch}/{total_batches} ({len(batch_docs)} chunks)...")
            add_documents_with_retry(store, batch_docs, batch_ids)
            logging.info(f"[job:{job_id}] batch {current_batch} complete")

        now_iso = datetime.now().isoformat()
        supabase.table("documents").update({
            "status": "completed",
            "last_used_at": now_iso,
            "chunk_count": len(chunks)
        }).eq("id", document_id).execute()

        supabase.table("ingestion_jobs").update({
            "status": "completed",
            "error_message": ""
        }).eq("id", job_id).execute()

        logging.info(f"[job:{job_id}] Ingestion complete, added {len(docs_to_add)} new chunks")

        if user_id:
            enforce_retention_for_user(user_id)

    except Exception as exc:
        logging.error(f"[job:{job_id}] Failed: {exc}")
        supabase.table("ingestion_jobs").update({
            "status": "failed",
            "error_message": str(exc)
        }).eq("id", job_id).execute()
        try:
            supabase.table("documents").update({"status": "failed"}).eq("id", document_id).execute()
        except Exception as doc_exc:
            logging.error(f"[job:{job_id}] Could not mark document failed: {doc_exc}")