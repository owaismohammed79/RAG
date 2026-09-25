from flask import Blueprint, request, jsonify, Response, current_app
import json
import logging
import os
from datetime import datetime

# Initialize Flask-Limiter for IP tracking
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .auth import auth_required
from .documents import (
    load_documents,
    split_documents,
    calculate_chunk_ids,
    prioritize_chunks,
    compute_sha256_from_stream,
    build_chunk_records,
)
from .vector_store import get_vector_store, reset_vector_store
from .ai_service import generate_rag_response, generate_fallback_response, save_message_to_db
from .user_service import get_user_prompt_limit, create_conversation, update_conversation_timestamp
from .retention import enforce_retention_for_user, prune_document

logger = logging.getLogger(__name__)
api = Blueprint("api", __name__)

# IP based limiter
limiter = Limiter(key_func=get_remote_address)

MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", str(5 * 1024 * 1024)))  # 5MB default
MAX_CHUNKS = int(os.getenv("MAX_CHUNKS_PER_DOC", "70"))


def require_admin():
    token = request.headers.get("X-Admin-Token")
    expected = os.getenv("ADMIN_TOKEN")
    return bool(expected and token == expected)


def create_ingestion_job(user_id, document_id, conversation_id, file_hash):
    supabase = current_app.supabase
    res = supabase.table("ingestion_jobs").insert({
        "user_id": user_id,
        "document_id": document_id,
        "conversation_id": conversation_id,
        "file_hash": file_hash,
        "status": "pending",
        "attempts": 0,
        "error_message": ""
    }).execute()
    return res.data[0]

@api.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@api.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "awake"}), 200


@api.route("/user/prompt-limit", methods=["GET"])
@auth_required
def get_user_prompt_limit_route(user):
    supabase = current_app.supabase
    try:
        prompts_remaining, max_prompts = get_user_prompt_limit(supabase, user["id"], increment=False)
        return jsonify({"promptsRemaining": prompts_remaining, "maxPrompts": max_prompts})
    except Exception as e:
        logger.error(f"Error fetching user prompt limit: {e}")
        return jsonify({"error": "Failed to fetch prompt limit", "details": str(e)}), 500


@api.route("/conversations", methods=["GET"])
@auth_required
def get_conversations(user):
    supabase = current_app.supabase
    try:
        res = supabase.table("conversations").select("*").eq("user_id", user["id"]).order("created_at", desc=True).execute()
        return jsonify(res.data or [])
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        return jsonify({"error": str(e)}), 500


@api.route("/conversations/<conversation_id>", methods=["GET"])
@auth_required
def get_messages(user, conversation_id):
    supabase = current_app.supabase
    try:
        convo_res = supabase.table("conversations").select("*").eq("id", conversation_id).execute()
        if not convo_res.data or convo_res.data[0]["user_id"] != user["id"]:
            return jsonify({"error": "Unauthorized"}), 403

        res = supabase.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at", desc=False).execute()
        return jsonify(res.data or [])
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return jsonify({"error": str(e)}), 500


@api.route("/conversations/<conversation_id>", methods=["DELETE"])
@auth_required
def delete_conversation(user, conversation_id):
    supabase = current_app.supabase
    try:
        conv_res = supabase.table("conversations").select("*").eq("id", conversation_id).execute()
        if not conv_res.data or conv_res.data[0]["user_id"] != user["id"]:
            return jsonify({"error": "Unauthorized"}), 403
    except Exception:
        return jsonify({"error": "Conversation not found"}), 404

    try:
        store = get_vector_store()
        store.delete(filter={'conversation_id': conversation_id})
    except Exception as e:
        logger.warning(f"Failed to delete Pinecone vectors for {conversation_id}: {e}")

    try:
        supabase.table("chunks").delete().eq("conversation_id", conversation_id).execute()
        supabase.table("ingestion_jobs").delete().eq("conversation_id", conversation_id).execute()
        supabase.table("documents").delete().eq("conversation_id", conversation_id).execute()
        supabase.table("messages").delete().eq("conversation_id", conversation_id).execute()
        supabase.table("conversations").delete().eq("id", conversation_id).execute()
        return jsonify({"success": True, "message": "Conversation and all orphans wiped completely"})
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        return jsonify({"error": str(e)}), 500

@api.route("/documents/upload", methods=["POST"])
@auth_required
def upload_documents(user):
    supabase = current_app.supabase
    user_id = user["id"]

    files = request.files.getlist("file")
    conversation_id = request.form.get("conversationId")
    user_question = request.form.get("prompt", "")

    if not files:
        return jsonify({"error": "No files provided"}), 400

    file_hashes = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"error": "Only PDF files are allowed"}), 400
        
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        
        if size > MAX_FILE_BYTES:
            return jsonify({"error": f"File size exceeds limit of {MAX_FILE_BYTES//1024//1024}MB"}), 400
        
        try:
            file_hash = compute_sha256_from_stream(file.stream)
            file_hashes.append((file, file_hash))
        except ValueError as ve:
            return jsonify({"error": f"Unseekable file stream: {str(ve)}"}), 400

    if not conversation_id or conversation_id == "null":
        conversation_id = create_conversation(supabase, user_id, user_question or "Document Upload")
    else:
        update_conversation_timestamp(supabase, conversation_id)

    responses = []

    for file, file_hash in file_hashes:
        existing = supabase.table("documents").select("id").eq("conversation_id", conversation_id).eq("file_hash", file_hash).execute()

        if existing.data and len(existing.data) > 0:
            responses.append({"filename": file.filename, "status": "skipped_duplicate"})
            continue

        documents = load_documents([file])
        chunks = split_documents(documents)
        if not chunks:
            return jsonify({"error": f"{file.filename} contained no extractable text"}), 400
        if len(chunks) > MAX_CHUNKS:
            return jsonify({"error": f"Too many chunks ({len(chunks)}) - please upload a smaller file"}), 400

        for chunk in chunks:
            chunk.metadata["user_id"] = user_id
            chunk.metadata["conversation_id"] = conversation_id

        chunks_with_ids = calculate_chunk_ids(chunks)
        sorted_chunks = prioritize_chunks(chunks_with_ids, user_question)

        now_iso = datetime.now().isoformat()
        doc_res = supabase.table("documents").insert({
            "user_id": user_id,
            "conversation_id": conversation_id,
            "file_hash": file_hash,
            "file_name": file.filename,
            "last_used_at": now_iso,
            "status": "pending",
            "chunk_count": len(sorted_chunks)
        }).execute()

        doc_record = doc_res.data[0]

        chunk_records = build_chunk_records(
            sorted_chunks, user_id, conversation_id, doc_record["id"]
        )

        if chunk_records:
            supabase.table("chunks").insert(chunk_records).execute()

        create_ingestion_job(user_id, doc_record["id"], conversation_id, file_hash)
        responses.append({"filename": file.filename, "status": "queued"})

    enforce_retention_for_user(user_id)

    return jsonify({
        "message": "Documents accepted and queued for ingestion",
        "conversationId": conversation_id,
        "files": responses,
    }), 202

@api.route("/documents/status", methods=["GET"])
@auth_required
def documents_ingestion_status(user):
    supabase = current_app.supabase

    conversation_id = request.args.get("conversationId")
    if not conversation_id:
        return jsonify({"error": "conversationId is required"}), 400

    try:
        docs_res = supabase.table("documents").select("status").eq("conversation_id", conversation_id).limit(100).execute()

        docs = docs_res.data or []
        if not docs:
            return jsonify({"ready": False, "pending": 0, "failed": 0, "total": 0}), 200

        statuses = [doc.get("status") for doc in docs]
        pending = sum(1 for s in statuses if s in ("pending", "processing"))
        failed = sum(1 for s in statuses if s == "failed")
        ready = pending == 0 and failed == 0 and all(s == "completed" for s in statuses)

        return jsonify({
            "ready": ready,
            "pending": pending,
            "failed": failed,
            "total": len(docs),
        }), 200
    except Exception as e:
        logger.error(f"Error checking document status: {e}")
        return jsonify({"error": str(e)}), 500


@api.route("/prompt/text-file", methods=["POST"])
@limiter.limit("30 per day")
@auth_required
def process_documents_without_voice(user):
    supabase = current_app.supabase

    user_id = user["id"]
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

    prompts_remaining, max_prompts = get_user_prompt_limit(supabase, user_id, increment=False)

    if prompts_remaining <= 0:
        return jsonify({"error": f"Daily prompt limit of {max_prompts} reached. Please try again tomorrow."}), 429

    prompts_remaining, max_prompts = get_user_prompt_limit(supabase, user_id, increment=True)

    if not conversation_id or conversation_id == "null":
        conversation_id = create_conversation(supabase, user_id, user_prompt)
    else:
        update_conversation_timestamp(supabase, conversation_id)

    save_message_to_db(supabase, conversation_id, "user", user_prompt, user_id)

    docs_ready = supabase.table("documents").select("id").eq("user_id", user_id).eq("conversation_id", conversation_id).eq("status", "completed").limit(1).execute()

    context_documents = []
    if docs_ready.data and len(docs_ready.data) > 0:
        try:
            search_filter = {"user_id": user_id, "conversation_id": conversation_id}
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

            save_message_to_db(supabase, conversation_id, "bot", final_answer_for_db, user_id)

        except Exception as e:
            logger.error(f"Error during AI stream generation: {e}")
            yield json.dumps({"type": "error", "content": f"An error occurred: {str(e)}"}) + "\n"

        metadata = {"type": "metadata", "conversationId": conversation_id, "promptsRemaining": prompts_remaining}
        yield json.dumps(metadata) + "\n"

    response = Response(generate_stream(), mimetype="application/x-ndjson")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@api.route("/admin/prune", methods=["POST"])
def admin_prune():
    if not require_admin():
        return jsonify({"error": "Unauthorized"}), 403
    supabase = current_app.supabase

    data = request.get_json() or {}
    user_id = data.get("userId")
    conversation_id = data.get("conversationId")
    file_hash = data.get("fileHash")

    query = supabase.table("documents").select("*")
    if user_id:
        query = query.eq("user_id", user_id)
    if conversation_id:
        query = query.eq("conversation_id", conversation_id)
    if file_hash:
        query = query.eq("file_hash", file_hash)

    docs_res = query.limit(500).execute()
    count = 0
    for doc in docs_res.data or []:
        prune_document(doc, reason="admin")
        count += 1
    return jsonify({"pruned": count})


@api.route("/admin/rebuild-index", methods=["POST"])
def admin_rebuild():
    if not require_admin():
        return jsonify({"error": "Unauthorized"}), 403
    supabase = current_app.supabase

    data = request.get_json() or {}
    drop_vectors = data.get("dropVectors", False)

    if drop_vectors:
        reset_vector_store()

    docs_res = supabase.table("documents").select("*").eq("status", "completed").limit(500).execute()

    jobs_created = 0
    for doc in docs_res.data or []:
        create_ingestion_job(
            doc.get("user_id"),
            doc["id"],
            doc.get("conversation_id"),
            doc["file_hash"],
        )
        supabase.table("documents").update({"status": "pending"}).eq("id", doc["id"]).execute()
        jobs_created += 1

    return jsonify({"jobsCreated": jobs_created, "droppedVectors": bool(drop_vectors)})