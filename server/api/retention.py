import logging
import os
from datetime import datetime, timedelta
from appwrite.query import Query

from .vector_store import get_vector_store
from .appwrite_utils import DOC_COMPLETED, DOC_FAILED, rel_id

DOCS_KEEP = int(os.getenv("DOCS_KEEP_PER_USER", "3"))
DOCS_MAX_AGE_DAYS = int(os.getenv("DOCS_MAX_AGE_DAYS", "10"))
CHUNK_CAP = int(os.getenv("CHUNK_CAP_PER_USER", "800"))


def enforce_retention_for_user(user_id):
    from app import databases, db_id, docs_collection_id
    try:
        docs_res = databases.list_documents(
            db_id, docs_collection_id,
            queries=[Query.equal('userId', user_id), Query.equal('status', DOC_COMPLETED),
                     Query.order_desc('$createdAt'), Query.limit(100)]
        )
        docs = docs_res.get('documents', [])
        if not docs:
            return

        # recent docs are kept
        keep_ids = {doc['$id'] for doc in docs[:DOCS_KEEP]}

        cutoff = datetime.now() - timedelta(days=DOCS_MAX_AGE_DAYS)
        cutoff_iso = cutoff.isoformat()

        total_chunks = 0
        docs_to_prune = []
        for doc in docs:
            total_chunks += doc.get('chunkCount', 0)
            created_ts = doc.get('$createdAt', '')
            if doc['$id'] not in keep_ids:
                docs_to_prune.append(doc)
            elif created_ts < cutoff_iso:
                docs_to_prune.append(doc)

        # Prune oldest 
        if total_chunks > CHUNK_CAP:
            sorted_old = sorted(docs, key=lambda d: d.get('$createdAt', ''))
            for doc in sorted_old:
                if total_chunks <= CHUNK_CAP:
                    break
                if doc not in docs_to_prune:
                    docs_to_prune.append(doc)
                total_chunks -= doc.get('chunkCount', 0)

        for doc in docs_to_prune:
            prune_document(doc, reason="retention")
    except Exception as exc:
        logging.error(f"Retention enforcement failed for user {user_id}: {exc}")


def prune_document(doc_record, reason="manual"):
    """Delete vectors for a document and mark it pruned in DB"""
    from app import databases, db_id, docs_collection_id, chunks_collection_id
    doc_id = doc_record['$id']
    user_id = rel_id(doc_record.get('userId'))
    try:
        store = get_vector_store()
        store.delete(filter={'document_id': doc_id})        
        chunks_res = databases.list_documents(
            db_id, chunks_collection_id,
            queries=[Query.equal('documentId', doc_id), Query.limit(5000)]
        )
        for ch in chunks_res.get('documents', []):
            databases.delete_document(db_id, chunks_collection_id, ch['$id'])
            
        databases.update_document(
            db_id, docs_collection_id, doc_id,
            {'status': DOC_FAILED}
        )
        logging.info(f"Pruned document {doc_id} for user {user_id} ({reason})")
    except Exception as exc:
        logging.error(f"Failed to prune document {doc_id}: {exc}")
