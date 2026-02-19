from flask import Blueprint, request, jsonify, Response
import json
import logging
from datetime import datetime
from .auth import auth_required
from .documents import load_documents, split_documents, calculate_chunk_ids, prioritize_chunks
from .vector_store import get_vector_store, add_documents_with_retry
from .ai_service import generate_rag_response, generate_fallback_response, save_message_to_db
from .user_service import get_user_prompt_limit, create_conversation, update_conversation_timestamp
import threading
import time

logger = logging.getLogger(__name__)
api = Blueprint('api', __name__)

def background_ingest_task(chunks, db_instance):
    """Adds documents in background to avoid blocking the request"""
    batch_size = 5
    total_chunks = len(chunks)
    logger.info(f"Starting background ingestion for {total_chunks} chunks...")
    
    for i in range(0, total_chunks, batch_size):
        batch = chunks[i:i + batch_size]
        batch_ids = [chunk.metadata["id"] for chunk in batch]
        try:
            add_documents_with_retry(db_instance, batch, batch_ids)
            time.sleep(0.2)
        except Exception as e:
            logger.error(f"Background ingestion error on batch {i}: {e}")
    
    logger.info("Background ingestion complete.")

@api.route('/ping', methods=['GET'])
def ping():
    """A simple endpoint to wake up the server"""
    return jsonify({'status': 'awake'}), 200

@api.route('/user/prompt-limit', methods=['GET'])
@auth_required
def get_user_prompt_limit_route(user):
    """Get user's prompt limit"""
    from app import databases, db_id, user_limits_collection_id
    
    try:
        prompts_remaining, max_prompts = get_user_prompt_limit(
            databases, db_id, user_limits_collection_id, user['$id']
        )
        return jsonify({
            'promptsRemaining': prompts_remaining,
            'maxPrompts': max_prompts
        })
    except Exception as e:
        logger.error(f"Error fetching user prompt limit: {e}")
        return jsonify({'error': 'Failed to fetch prompt limit', 'details': str(e)}), 500

@api.route('/conversations', methods=['GET'])
@auth_required
def get_conversations(user):
    """Get user's conversations"""
    from app import databases, db_id, conv_collection_id
    from appwrite.query import Query
    
    try:
        result = databases.list_documents(
            db_id,
            conv_collection_id,
            queries=[Query.equal('userId', user['$id']), Query.order_desc('$createdAt')]
        )
        return jsonify(result['documents'])
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/conversations/<conversation_id>', methods=['GET'])
@auth_required
def get_messages(user, conversation_id):
    """Get messages for a conversation"""
    from app import databases, db_id, msg_collection_id, conv_collection_id
    from appwrite.query import Query
    
    try:
        convo = databases.get_document(db_id, conv_collection_id, conversation_id)
        if convo['userId'] != user['$id']:
            return jsonify({'error': 'Unauthorized'}), 403
            
        result = databases.list_documents(
            db_id,
            msg_collection_id,
            queries=[Query.equal('conversationId', conversation_id), Query.order_asc('$createdAt')]
        )
        return jsonify(result['documents'])
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/conversations/<conversation_id>', methods=['DELETE'])
@auth_required
def delete_conversation(user, conversation_id):
    """Delete a conversation and its messages"""
    from app import databases, db_id, msg_collection_id, conv_collection_id
    from appwrite.query import Query
    
    try:
        convo = databases.get_document(db_id, conv_collection_id, conversation_id)
        if convo['userId'] != user['$id']:
            return jsonify({'error': 'Unauthorized'}), 403

        messages_to_delete = databases.list_documents(
            db_id,
            msg_collection_id,
            queries=[Query.equal('conversationId', conversation_id)]
        )
        
        for msg in messages_to_delete['documents']:
            databases.delete_document(db_id, msg_collection_id, msg['$id'])

        databases.delete_document(db_id, conv_collection_id, conversation_id)
        return jsonify({'message': 'Conversation and associated messages deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/documents/upload', methods=['POST'])
@auth_required
def upload_documents(user):
    """Upload and process documents"""
    from app import databases, db_id, msg_collection_id, conv_collection_id
    
    files = request.files.getlist('file')
    conversation_id = request.form.get('conversationId')
    user_question = request.form.get('prompt', '')
    
    if not files:
        return jsonify({'error': 'No files provided'}), 400
    
    for file in files:
        if not file.filename.endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        if len(file.read()) > 5 * 1024 * 1024:  #5MB limit
            return jsonify({'error': 'File size exceeds 5MB limit'}), 400
        file.seek(0)  #reset file pointer after reading
    
    try:
        current_timestamp = datetime.now().isoformat()
        
        if not conversation_id or conversation_id == 'null':
            conversation_id = create_conversation(
                databases, db_id, conv_collection_id, user['$id'], 
                user_question or 'Document Upload'
            )
        else:
            update_conversation_timestamp(databases, db_id, conv_collection_id, conversation_id)
        
        documents = load_documents(files)
        chunks = split_documents(documents)
        
        for chunk in chunks:
            chunk.metadata['user_id'] = user['$id']
            chunk.metadata['conversation_id'] = conversation_id
            
        chunks_with_ids = calculate_chunk_ids(chunks)
        sorted_chunks = prioritize_chunks(chunks_with_ids, user_question)
        
        db = get_vector_store()
        sync_batch = sorted_chunks[:10]
        async_batch = sorted_chunks[10:]
        
        if sync_batch:
            logger.info(f"Sync ingesting {len(sync_batch)} chunks...")
            batch_ids = [c.metadata["id"] for c in sync_batch]
            add_documents_with_retry(db, sync_batch, batch_ids)
        
        if async_batch:
            logger.info(f"Background ingesting {len(async_batch)} chunks...")
            t = threading.Thread(target=background_ingest_task, args=(async_batch, db))
            t.daemon = True
            t.start()
        
        return jsonify({
            'message': 'Documents processed successfully',
            'conversationId': conversation_id
        }), 200
    except Exception as e:
        logger.error(f"Error processing documents: {e}")
        return jsonify({'error': f'Failed to process documents: {str(e)}'}), 500

@api.route('/prompt/text-file', methods=['POST'])
@auth_required
def process_documents_without_voice(user):
    """Process documents and generate response"""
    from app import databases, db_id, msg_collection_id, conv_collection_id, user_limits_collection_id
    
    user_id = user['$id']
    user_prompt = request.form.get('prompt')
    files = request.files.getlist('file')
    conversation_id = request.form.get('conversationId')
    history_str = request.form.get('history', '[]')
    
    try:
        history = json.loads(history_str)
    except json.JSONDecodeError:
        history = []
    
    if not user_prompt:
        return jsonify({'error': 'Missing question argument'}), 400
    
    prompts_remaining, max_prompts = get_user_prompt_limit(
        databases, db_id, user_limits_collection_id, user_id
    )
    
    if prompts_remaining <= 0:
        return jsonify({
            'error': f'Daily prompt limit of {max_prompts} reached. Please try again tomorrow.'
        }), 429
    
    current_timestamp = datetime.now().isoformat()
    
    if not conversation_id or conversation_id == 'null':
        conversation_id = create_conversation(
            databases, db_id, conv_collection_id, user_id, user_prompt
        )
    else:
        update_conversation_timestamp(databases, db_id, conv_collection_id, conversation_id)
    
    save_message_to_db(
        databases, db_id, msg_collection_id, conversation_id, 
        'user', user_prompt
    )
    
    try:
        if files:
            documents = load_documents(files)
            logger.info("File loaded")
            chunks = split_documents(documents)
            logger.info("File split into chunks")
            
            for chunk in chunks:
                chunk.metadata['user_id'] = user_id
                chunk.metadata['conversation_id'] = conversation_id
                
            chunks_with_ids = calculate_chunk_ids(chunks)
            logger.info("meta-data appended")
            sorted_chunks = prioritize_chunks(chunks_with_ids, user_prompt)
            
            sync_batch = sorted_chunks[:10]
            async_batch = sorted_chunks[10:]
            
            db = get_vector_store()
            
            if sync_batch:
                logger.info(f"Sync ingesting {len(sync_batch)} chunks...")
                batch_ids = [c.metadata["id"] for c in sync_batch]
                add_documents_with_retry(db, sync_batch, batch_ids)
            
            if async_batch:
                logger.info(f"Background ingesting {len(async_batch)} chunks...")
                t = threading.Thread(target=background_ingest_task, args=(async_batch, db))
                t.daemon = True
                t.start()
        
        search_filter = {
            "$and": [
                {'user_id': user_id},
                {'conversation_id': conversation_id}
            ]
        }
        
        logger.info("Started retrieving relevant docs")
        db = get_vector_store()
        retriever = db.as_retriever(search_kwargs={'k': 15, 'filter': search_filter})
        docs = retriever.invoke(user_prompt)
        logger.info("Relevant docs found")
        
        context_documents = docs if docs else []
        
        def generate_stream():
            final_answer_for_db = ""
            rag_response_buffer = ""
            
            try:
                logger.info("Starting RAG stream...")
                rag_stream = generate_rag_response(user_prompt, context_documents, history)
                
                for chunk in rag_stream:
                    chunk_content = chunk.content
                    if chunk_content:
                        rag_response_buffer += chunk_content
                        yield json.dumps({"type": "rag_chunk", "content": chunk_content}) + "\n"
                
                logger.info("RAG chunks sent")
                
                if "Answer is not available in the context" in rag_response_buffer:
                    logger.info("RAG context not found. Switching to fallback stream")
                    prefix = "Couldn't find answer in context provided.\nResponse from Gemini:\n"
                    yield json.dumps({"type": "fallback_start", "content": prefix}) + "\n"
                    
                    fallback_stream = generate_fallback_response(user_prompt, history)
                    fallback_buffer = ""
                    
                    for chunk in fallback_stream:
                        chunk_content = chunk.content
                        if chunk_content:
                            fallback_buffer += chunk_content
                            yield json.dumps({"type": "fallback_chunk", "content": chunk_content}) + "\n"
                    
                    logger.info("Fallback stream done")
                    final_answer_for_db = "Couldn't find answer in context provided.\nResponse from Gemini:\n" + fallback_buffer
                else:
                    logger.info("RAG stream successful")
                    final_answer_for_db = rag_response_buffer
                
                save_message_to_db(
                    databases, db_id, msg_collection_id, conversation_id,
                    'bot', final_answer_for_db
                )
                logger.info("Answer saved to db")
                print("Final answer saved to DB")
                
            except Exception as e:
                logger.error(f"Error during AI stream generation: {e}")
                yield json.dumps({"type": "error", "content": f"An error occurred: {str(e)}"}) + "\n"
            
            metadata = {
                "type": "metadata",
                "conversationId": conversation_id,
                "promptsRemaining": prompts_remaining - 1
            }
            yield json.dumps(metadata) + "\n"
        
        logger.info("Streaming started")
        response = Response(generate_stream(), mimetype='application/x-ndjson')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        return response
        
    except Exception as e:
        logger.error(f"Error calling generate_stream: {e}")
        return jsonify({'error': f'An internal server error occurred while starting the stream: {str(e)}'}), 500