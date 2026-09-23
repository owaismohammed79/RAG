import logging
import os
from datetime import datetime, timedelta
from .vector_store import get_vector_store

DOCS_KEEP = int(os.getenv("DOCS_KEEP_PER_USER", "3"))
DOCS_MAX_AGE_DAYS = int(os.getenv("DOCS_MAX_AGE_DAYS", "10"))
CHUNK_CAP = int(os.getenv("CHUNK_CAP_PER_USER", "800"))


def enforce_retention_for_user(user_id):
    from flask import current_app
    supabase = current_app.supabase
    try:
        res = supabase.table("documents").select("*").eq("user_id", user_id).eq("status", "completed").order("created_at", desc=True).limit(100).execute()
        
        docs = res.data or []
        if not docs:
            return

        keep_ids = {doc["id"] for doc in docs[:DOCS_KEEP]}

        cutoff = datetime.now() - timedelta(days=DOCS_MAX_AGE_DAYS)
        cutoff_iso = cutoff.isoformat()

        total_chunks = 0
        docs_to_prune = []
        for doc in docs:
            total_chunks += doc.get("chunk_count", 0)
            created_ts = doc.get("created_at", "")
            if doc["id"] not in keep_ids:
                docs_to_prune.append(doc)
            elif created_ts < cutoff_iso:
                docs_to_prune.append(doc)

        if total_chunks > CHUNK_CAP:
            sorted_old = sorted(docs, key=lambda d: d.get("created_at", ""))
            for doc in sorted_old:
                if total_chunks <= CHUNK_CAP:
                    break
                if doc not in docs_to_prune:
                    docs_to_prune.append(doc)
                total_chunks -= doc.get("chunk_count", 0)

        for doc in docs_to_prune:
            prune_document(doc, reason="retention")
    except Exception as exc:
        logging.error(f"Retention enforcement failed for user {user_id}: {exc}")


def prune_document(doc_record, reason="manual"):
    """Delete vectors for a document and mark it pruned in DB"""
    from flask import current_app
    supabase = current_app.supabase
    doc_id = doc_record["id"]
    user_id = doc_record.get("user_id")
    try:
        store = get_vector_store()
        store.delete(filter={"document_id": doc_id})        
        
        supabase.table("chunks").delete().eq("document_id", doc_id).execute()
        supabase.table("documents").update({"status": "failed"}).eq("id", doc_id).execute()
        
        logging.info(f"Pruned document {doc_id} for user {user_id} ({reason})")
    except Exception as exc:
        logging.error(f"Failed to prune document {doc_id}: {exc}")