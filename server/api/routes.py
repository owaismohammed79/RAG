from flask import Blueprint, request, jsonify, Response
import json
import logging
import os
import shutil
from datetime import datetime
from appwrite.id import ID
from appwrite.query import Query

from .auth import auth_required
from .documents import (
    load_documents,
    split_documents,
    calculate_chunk_ids,
    prioritize_chunks,
    compute_sha256_from_stream,
    build_chunk_records,
)
from .vector_store import get_vector_store, reset_vector_store, CHROMA_PATH
from .ai_service import generate_rag_response, generate_fallback_response, save_message_to_db
from .user_service import get_user_prompt_limit, create_conversation, update_conversation_timestamp
from .retention import enforce_retention_for_user, prune_document

logger = logging.getLogger(__name__)
api = Blueprint("api", __name__)

MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", str(5 * 1024 * 1024)))  # 5MB default
MAX_CHUNKS = int(os.getenv("MAX_CHUNKS_PER_DOC", "400"))


def require_admin():
    token = request.headers.get("X-Admin-Token")
    expected = os.getenv("ADMIN_TOKEN")
    return bool(expected and token == expected)


def create_ingestion_job(user_id, document_id, conversation_id, file_hash):
    """Persist ingestion job so worker can resume after restart."""
    from app import databases, db_id, jobs_collection_id

    return databases.create_document(
        db_id,
        jobs_collection_id,
        ID.unique(),
        {
            "userId": user_id,
            "documentId": document_id,
            "conversationId": conversation_id,
            "fileHash": file_hash,
            "status": "pending",
            "attempts": 0,
            "errorMessage": "",
        },
    )


@api.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@api.route("/ping", methods=["GET"])
def ping():
    """A simple endpoint to wake up the server"""
    return jsonify({"status": "awake"}), 200


@api.route("/user/prompt-limit", methods=["GET"])
@auth_required
def get_user_prompt_limit_route(user):
    """Get user's prompt limit"""
    from app import databases, db_id, user_limits_collection_id

    try:
        prompts_remaining, max_prompts = get_user_prompt_limit(
            databases, db_id, user_limits_collection_id, user["$id"]
        )
        return jsonify({"promptsRemaining": prompts_remaining, "maxPrompts": max_prompts})
    except Exception as e:
        logger.error(f"Error fetching user prompt limit: {e}")
        return jsonify({"error": "Failed to fetch prompt limit", "details": str(e)}), 500


@api.route("/conversations", methods=["GET"])
@auth_required
def get_conversations(user):
    """Get user's conversations"""
    from app import databases, db_id, conv_collection_id

    try:
        result = databases.list_documents(
            db_id,
            conv_collection_id,
            queries=[Query.equal("userId", user["$id"]), Query.order_desc("$createdAt")],
        )
        return jsonify(result["documents"])
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        return jsonify({"error": str(e)}), 500


@api.route("/conversations/<conversation_id>", methods=["GET"])
@auth_required
def get_messages(user, conversation_id):
    """Get messages for a conversation"""
    from app import databases, db_id, msg_collection_id, conv_collection_id

    try:
        convo = databases.get_document(db_id, conv_collection_id, conversation_id)
        if convo["userId"] != user["$id"]:
            return jsonify({"error": "Unauthorized"}), 403

        result = databases.list_documents(
            db_id,
            msg_collection_id,
            queries=[Query.equal("conversationId", conversation_id), Query.order_asc("$createdAt")],
        )
        return jsonify(result["documents"])
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return jsonify({"error": str(e)}), 500


@api.route("/conversations/<conversation_id>", methods=["DELETE"])
@auth_required
def delete_conversation(user, conversation_id):
    """Delete a conversation and its messages"""
    from app import databases, db_id, msg_collection_id, conv_collection_id

    try:
        convo = databases.get_document(db_id, conv_collection_id, conversation_id)
        if convo["userId"] != user["$id"]:
            return jsonify({"error": "Unauthorized"}), 403

        messages_to_delete = databases.list_documents(
            db_id, msg_collection_id, queries=[Query.equal("conversationId", conversation_id)]
        )

        for msg in messages_to_delete["documents"]:
            databases.delete_document(db_id, msg_collection_id, msg["$id"])

        databases.delete_document(db_id, conv_collection_id, conversation_id)
        return jsonify({"message": "Conversation and associated messages deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        return jsonify({"error": str(e)}), 500


@api.route("/documents/upload", methods=["POST"])
@auth_required
def upload_documents(user):
    """Upload and queue documents for ingestion (no embeddings in request)."""
    from app import (
        databases,
        db_id,
        conv_collection_id,
        docs_collection_id,
        chunks_collection_id,
    )

    files = request.files.getlist("file")
    conversation_id = request.form.get("conversationId")
    user_question = request.form.get("prompt", "")

    if not files:
        return jsonify({"error": "No files provided"}), 400

    # Basic validation and hashing
    file_hashes = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"error": "Only PDF files are allowed"}), 400
        size = len(file.read())
        if size > MAX_FILE_BYTES:
            return jsonify({"error": f"File size exceeds limit of {MAX_FILE_BYTES//1024//1024}MB"}), 400
        file.seek(0)
        file_hash = compute_sha256_from_stream(file.stream)
        file_hashes.append((file, file_hash))

    # Conversation handling
    if not conversation_id or conversation_id == "null":
        conversation_id = create_conversation(
            databases, db_id, conv_collection_id, user["$id"], user_question or "Document Upload"
        )
    else:
        update_conversation_timestamp(databases, db_id, conv_collection_id, conversation_id)

    responses = []

    for file, file_hash in file_hashes:
        # idempotency: skip existing doc with same hash
        existing = databases.list_documents(
            db_id,
            docs_collection_id,
            queries=[
                Query.equal("userId", user["$id"]),
                Query.equal("conversationId", conversation_id),
                Query.equal("fileHash", file_hash),
            ],
        )
        if existing.get("total", 0) > 0:
            responses.append({"filename": file.filename, "status": "skipped_duplicate"})
            continue

        documents = load_documents([file])
        chunks = split_documents(documents)
        if not chunks:
            return jsonify({"error": f"{file.filename} contained no extractable text"}), 400
        if len(chunks) > MAX_CHUNKS:
            return jsonify({"error": f"Too many chunks ({len(chunks)}) - please upload a smaller file"}), 400

        for chunk in chunks:
            chunk.metadata["user_id"] = user["$id"]
            chunk.metadata["conversation_id"] = conversation_id

        chunks_with_ids = calculate_chunk_ids(chunks)
        sorted_chunks = prioritize_chunks(chunks_with_ids, user_question)

        uploaded_at = datetime.now().isoformat()
        doc_record = databases.create_document(
            db_id,
            docs_collection_id,
            ID.unique(),
            {
                "userId": user["$id"],
                "conversationId": conversation_id,
                "fileHash": file_hash,
                "filename": file.filename,
                "uploadedAt": uploaded_at,
                "lastUsedAt": uploaded_at,
                "status": "pending",
                "chunkCount": len(sorted_chunks),
            },
        )

        chunk_records = build_chunk_records(
            sorted_chunks, file_hash, user["$id"], conversation_id, doc_record["$id"]
        )
        for rec in chunk_records:
            databases.create_document(
                db_id,
                chunks_collection_id,
                ID.unique(),
                rec,
            )

        create_ingestion_job(user["$id"], doc_record["$id"], conversation_id, file_hash)
        responses.append({"filename": file.filename, "status": "queued"})

    enforce_retention_for_user(user["$id"])

    return (
        jsonify(
            {
                "message": "Documents accepted and queued for ingestion",
                "conversationId": conversation_id,
                "files": responses,
            }
        ),
        202,
    )


@api.route("/prompt/text-file", methods=["POST"])
@auth_required
def process_documents_without_voice(user):
    """Chat route; no ingestion occurs here."""
    from app import databases, db_id, msg_collection_id, conv_collection_id, user_limits_collection_id, docs_collection_id

    user_id = user["$id"]
    user_prompt = request.form.get("prompt")
    files = request.files.getlist("file")
    conversation_id = request.form.get("conversationId")
    history_str = request.form.get("history", "[]")

    try:
        history = json.loads(history_str)
    except json.JSONDecodeError:
        history = []

    if files:
        return jsonify({"error": "Uploads must be sent to /api/documents/upload"}), 400

    if not user_prompt:
        return jsonify({"error": "Missing question argument"}), 400

    prompts_remaining, max_prompts = get_user_prompt_limit(
        databases, db_id, user_limits_collection_id, user_id
    )

    if prompts_remaining <= 0:
        return jsonify(
            {"error": f"Daily prompt limit of {max_prompts} reached. Please try again tomorrow."}
        ), 429

    if not conversation_id or conversation_id == "null":
        conversation_id = create_conversation(databases, db_id, conv_collection_id, user_id, user_prompt)
    else:
        update_conversation_timestamp(databases, db_id, conv_collection_id, conversation_id)

    save_message_to_db(databases, db_id, msg_collection_id, conversation_id, "user", user_prompt)

    # Determine whether we have ready documents
    docs_ready = databases.list_documents(
        db_id,
        docs_collection_id,
        queries=[
            Query.equal("userId", user_id),
            Query.equal("conversationId", conversation_id),
            Query.equal("status", "ready"),
            Query.limit(1),
        ],
    )

    context_documents = []
    if docs_ready.get("total", 0) > 0:
        try:
            search_filter = {"$and": [{"user_id": user_id}, {"conversation_id": conversation_id}]}
            store = get_vector_store()
            retriever = store.as_retriever(search_kwargs={"k": 5, "filter": search_filter})
            docs = retriever.invoke(user_prompt)
            context_documents = docs if docs else []
        except Exception as e:
            logger.error(f"Vector retrieval failed: {e}")
            context_documents = []

    def generate_stream():
        final_answer_for_db = ""
        rag_response_buffer = ""

        try:
            logger.info("Starting RAG stream...")
            if context_documents:
                rag_stream = generate_rag_response(user_prompt, context_documents, history)
                for chunk in rag_stream:
                    chunk_content = chunk.content
                    if chunk_content:
                        rag_response_buffer += chunk_content
                        yield json.dumps({"type": "rag_chunk", "content": chunk_content}) + "\n"
            else:
                rag_response_buffer = "Answer is not available in the context"

            if "Answer is not available in the context" in rag_response_buffer:
                prefix = "No indexed documents found. Response from Gemini:\n"
                yield json.dumps({"type": "fallback_start", "content": prefix}) + "\n"
                fallback_stream = generate_fallback_response(user_prompt, history)
                fallback_buffer = ""
                for chunk in fallback_stream:
                    chunk_content = chunk.content
                    if chunk_content:
                        fallback_buffer += chunk_content
                        yield json.dumps({"type": "fallback_chunk", "content": chunk_content}) + "\n"
                final_answer_for_db = prefix + fallback_buffer
            else:
                final_answer_for_db = rag_response_buffer

            save_message_to_db(databases, db_id, msg_collection_id, conversation_id, "bot", final_answer_for_db)

        except Exception as e:
            logger.error(f"Error during AI stream generation: {e}")
            yield json.dumps({"type": "error", "content": f"An error occurred: {str(e)}"}) + "\n"

        metadata = {"type": "metadata", "conversationId": conversation_id, "promptsRemaining": prompts_remaining - 1}
        yield json.dumps(metadata) + "\n"

    response = Response(generate_stream(), mimetype="application/x-ndjson")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@api.route("/admin/prune", methods=["POST"])
def admin_prune():
    if not require_admin():
        return jsonify({"error": "Unauthorized"}), 403
    from app import databases, db_id, docs_collection_id

    data = request.get_json() or {}
    user_id = data.get("userId")
    conversation_id = data.get("conversationId")
    file_hash = data.get("fileHash")

    queries = []
    if user_id:
        queries.append(Query.equal("userId", user_id))
    if conversation_id:
        queries.append(Query.equal("conversationId", conversation_id))
    if file_hash:
        queries.append(Query.equal("fileHash", file_hash))
    if not queries:
        return jsonify({"error": "Specify userId, conversationId or fileHash"}), 400

    docs_res = databases.list_documents(db_id, docs_collection_id, queries=queries + [Query.limit(500)])
    count = 0
    for doc in docs_res.get("documents", []):
        prune_document(doc, reason="admin")
        count += 1
    return jsonify({"pruned": count})


@api.route("/admin/rebuild-index", methods=["POST"])
def admin_rebuild():
    if not require_admin():
        return jsonify({"error": "Unauthorized"}), 403
    from app import databases, db_id, docs_collection_id

    data = request.get_json() or {}
    drop_vectors = data.get("dropVectors", False)

    if drop_vectors and os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH, ignore_errors=True)
    reset_vector_store()

    docs_res = databases.list_documents(
        db_id, docs_collection_id, queries=[Query.equal("status", "ready"), Query.limit(500)]
    )
    jobs_created = 0
    for doc in docs_res.get("documents", []):
        create_ingestion_job(doc["userId"], doc["$id"], doc["conversationId"], doc["fileHash"])
        databases.update_document(db_id, docs_collection_id, doc["$id"], {"status": "pending"})
        jobs_created += 1

    return jsonify({"jobsCreated": jobs_created, "droppedVectors": bool(drop_vectors)})


@api.route("/admin/stats", methods=["GET"])
def admin_stats():
    if not require_admin():
        return jsonify({"error": "Unauthorized"}), 403
    from app import databases, db_id, docs_collection_id, chunks_collection_id, jobs_collection_id

    docs_count = databases.list_documents(db_id, docs_collection_id, queries=[Query.limit(1)])["total"]
    chunks_count = databases.list_documents(db_id, chunks_collection_id, queries=[Query.limit(1)])["total"]
    jobs_pending = databases.list_documents(
        db_id, jobs_collection_id, queries=[Query.equal("status", "pending"), Query.limit(1)]
    )["total"]
    jobs_running = databases.list_documents(
        db_id, jobs_collection_id, queries=[Query.equal("status", "running"), Query.limit(1)]
    )["total"]
    return jsonify(
        {
            "docs": docs_count,
            "chunks": chunks_count,
            "jobsPending": jobs_pending,
            "jobsRunning": jobs_running,
        }
    )
