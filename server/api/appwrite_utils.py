from datetime import datetime
from appwrite.id import ID
from appwrite.query import Query
import logging

logger = logging.getLogger(__name__)

# documents.status enum in Appwrite
DOC_PENDING = "pending"
DOC_PROCESSING = "processing"
DOC_COMPLETED = "completed"
DOC_FAILED = "failed"

# ingestion_jobs.status — align with the same enum pattern
JOB_PENDING = "pending"
JOB_PROCESSING = "processing"
JOB_COMPLETED = "completed"
JOB_FAILED = "failed"


def rel_id(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("$id")
    if isinstance(value, list):
        if not value:
            return None
        return rel_id(value[0])
    return None


def get_or_create_user_document_id(databases, db_id, users_collection_id, auth_user_id, email=None):
    """documents/chunks/jobs.userId are relationships to the Users collection. That attribute must be a Users document $id, not the Appwrite Auth user id."""
    if not users_collection_id:
        return auth_user_id

    try:
        result = databases.list_documents(
            db_id,
            users_collection_id,
            queries=[Query.equal("userId", auth_user_id), Query.limit(1)],
        )
        docs = result.get("documents", [])
        if docs:
            return docs[0]["$id"]

        payload = {
            "userId": auth_user_id,
            "email": (email or "unknown@local")[:30],
            "status": True,
            "joined": datetime.now().isoformat(),
        }
        created = databases.create_document(
            db_id, users_collection_id, ID.unique(), payload
        )
        return created["$id"]
    except Exception as exc:
        logger.error("Failed to resolve Users collection document: %s", exc)
        return auth_user_id
