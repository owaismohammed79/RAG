from flask import Flask, request, jsonify, Response
from main import load_documents, split_documents, get_embedding_function, CHROMA_PATH, add_documents_with_retry, calculate_chunk_ids, generate_stream
from langchain.schema.document import Document
import time
from langchain_chroma import Chroma
from flask_cors import CORS
import google.generativeai as genai
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from functools import wraps
from appwrite.client import Client
from appwrite.services.account import Account
from appwrite.services.databases import Databases
from appwrite.id import ID
from appwrite.query import Query
from appwrite.permission import Permission
from appwrite.role import Role
from dotenv import load_dotenv
import json
from datetime import datetime, date
import traceback

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": os.getenv("FRONTEND_URL")}})

#Appwrite Client Initialization
client = Client()
client.set_endpoint(os.getenv("VITE_APPWRITE_ENDPOINT"))
client.set_project(os.getenv("VITE_APPWRITE_PROJECT_ID"))
client.set_key(os.getenv("VITE_APPWRITE_API_KEY"))

#This account instance is for admin tasks
account = Account(client)
databases = Databases(client)
db_id = os.getenv("VITE_APPWRITE_DATABASE_ID")
conv_collection_id = os.getenv("VITE_APPWRITE_CONVERSATIONS_COLL_ID")
msg_collection_id = os.getenv("VITE_APPWRITE_MESSAGES_COLL_ID")
user_limits_collection_id = os.getenv("VITE_APPWRITE_USER_LIMITS_COLL_ID")

# Initialize ChromaDB globally
embeddings = get_embedding_function()
db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)

@app.route('/api/ping', methods=['GET'])
def ping():
    """A simple endpoint to wake up the server"""
    return jsonify({'status': 'awake'}), 200

#Authentication Decorator
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        jwt = request.headers.get('Authorization')
        if not jwt:
            return jsonify({'error': 'Missing token'}), 401
        
        try:
            jwt_token = jwt.split(' ')[1]

            #create a temporary, request-specific client to verify the user's JWT
            user_client = Client()
            user_client.set_endpoint(os.getenv("VITE_APPWRITE_ENDPOINT"))
            user_client.set_project(os.getenv("VITE_APPWRITE_PROJECT_ID"))
            user_client.set_jwt(jwt_token)

            user_account = Account(user_client)
            user = user_account.get() #verifies the JWT and gets the user
            kwargs['user'] = user
        except Exception as e:
            return jsonify({'error': 'Invalid or expired token', 'details': str(e)}), 401
        
        return f(*args, **kwargs)
    return decorated_function

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"]
)

@app.route('/api/prompt/text-file', methods=['POST'])
@auth_required
@limiter.limit("60 per minute")
def process_documents_without_voice(user):
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

    current_timestamp = datetime.now().isoformat()
    today_str = date.today().isoformat()

    MAX_PROMPTS_PER_DAY = 10
    prompts_remaining = MAX_PROMPTS_PER_DAY

    try:
        user_limit_docs = databases.list_documents(
            db_id,
            user_limits_collection_id,
            queries=[Query.equal('userId', user_id)]
        )
        user_limit_doc = user_limit_docs['documents'][0] if user_limit_docs['documents'] else None

        if user_limit_doc:
            last_reset_date = user_limit_doc.get('lastResetDate')
            prompt_count = user_limit_doc.get('promptCount', 0)

            if last_reset_date != today_str:
                databases.update_document(
                    db_id, user_limits_collection_id, user_limit_doc['$id'],
                    {'promptCount': 1, 'lastResetDate': today_str}
                )
                prompts_remaining = MAX_PROMPTS_PER_DAY - 1
            else:
                if prompt_count >= MAX_PROMPTS_PER_DAY:
                    return jsonify({'error': f'Daily prompt limit of {MAX_PROMPTS_PER_DAY} reached. Please try again tomorrow.'}), 429
                
                databases.update_document(
                    db_id, user_limits_collection_id, user_limit_doc['$id'],
                    {'promptCount': prompt_count + 1}
                )
                prompts_remaining = MAX_PROMPTS_PER_DAY - (prompt_count + 1)
        else:
            databases.create_document(
                db_id, user_limits_collection_id, ID.unique(),
                {
                    'userId': user_id, 'promptCount': 1, 'lastResetDate': today_str
                },
                permissions=[
                    Permission.read(Role.user(user_id)),
                    Permission.update(Role.user(user_id)),
                    Permission.delete(Role.user(user_id)),
                ]
            )
            prompts_remaining = MAX_PROMPTS_PER_DAY - 1
    except Exception as e:
        print(f"Error managing user prompt limit: {e}")

    if not conversation_id or conversation_id == 'null':
        try:
            doc = databases.create_document(
                db_id, conv_collection_id, ID.unique(),
                {
                    'title': user_prompt[:50], 
                    'userId': user_id,
                    'lastMessageAt': current_timestamp
                },
                permissions=[
                    Permission.read(Role.user(user_id)),
                    Permission.update(Role.user(user_id)),
                    Permission.delete(Role.user(user_id)),
                ]
            )
            conversation_id = doc['$id']
        except Exception as e:
            return jsonify({'error': f'Failed to create conversation: {e}'}), 500
    else:
        try:
            databases.update_document(
                db_id, conv_collection_id, conversation_id,
                {'lastMessageAt': current_timestamp}
            )
        except Exception as e:
            print(f"Error updating lastMessageAt for conversation {conversation_id}: {e}")

    try:
        databases.create_document(
            db_id, msg_collection_id, ID.unique(),
            {
                'conversationId': conversation_id, 
                'senderType': 'user', 
                'content': user_prompt,
                'timestamp': current_timestamp
            },
            permissions=[
                Permission.read(Role.user(user_id)),
                Permission.update(Role.user(user_id)),
                Permission.delete(Role.user(user_id)),
            ]
        )
    except Exception as e:
        print(f"Error saving user message: {e}")

    try:
        if files:
            documents = load_documents(files)
            chunks = split_documents(documents)
            for chunk in chunks:
                chunk.metadata['user_id'] = user_id
                chunk.metadata['conversation_id'] = conversation_id
            
            chunks_with_ids = calculate_chunk_ids(chunks)
            
            batch_size = 5
            for i in range(0, len(chunks_with_ids), batch_size):
                batch = chunks_with_ids[i:i + batch_size]
                batch_ids = [chunk.metadata["id"] for chunk in batch]
                try:
                    print(f"Processing batch {(i // batch_size) + 1}/{(len(chunks_with_ids) + batch_size - 1) // batch_size}...")
                    add_documents_with_retry(db, batch, batch_ids)
                    time.sleep(0.3) 
                except Exception as e:
                    print(f"Failed to process batch after retries: {e}")
                    continue
            print(f"Added {len(chunks_with_ids)} new chunks to the database.")
        
        search_filter = {
            "$and": [
                {'user_id': user_id},
                {'conversation_id': conversation_id}
            ]
        }
        retriever = db.as_retriever(search_kwargs={'k': 15, 'filter': search_filter})
        docs = retriever.invoke(user_prompt)
        context_documents = docs if docs else []

    except Exception as e:
        print(f"Error during document processing: {e}")
        traceback.print_exc()
        return jsonify({'error': f'An internal server error occurred during document processing: {str(e)}'}), 500

    try:
        stream_generator = generate_stream(
            user_id=user_id,
            conversation_id=conversation_id,
            user_question=user_prompt,
            context_documents=context_documents,
            history=history,
            databases=databases,
            db_id=db_id,
            msg_collection_id=msg_collection_id
        )
        
        # We must send convoID n prompts at the end, so create a new generator to chain them
        def final_stream_with_metadata():
            # First, yield everything from the AI generator
            yield from stream_generator
            
            # After the AI stream is done, yield the final metadata
            metadata = {
                "type": "metadata",
                "conversationId": conversation_id,
                "promptsRemaining": prompts_remaining
            }
            yield json.dumps(metadata) + "\n"
            print("Sent final metadata")


        return Response(final_stream_with_metadata(), mimetype='application/x-ndjson')

    except Exception as e:
        print(f"Error calling generate_stream: {e}")
        traceback.print_exc()
        return jsonify({'error': f'An internal server error occurred while starting the stream: {str(e)}'}), 500


@app.route('/api/conversations', methods=['GET'])
@auth_required
def get_conversations(user):
    try:
        result = databases.list_documents(
            db_id,
            conv_collection_id,
            queries=[Query.equal('userId', user['$id']), Query.order_desc('$createdAt')]
        )
        return jsonify(result['documents'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/user/prompt-limit', methods=['GET'])
@auth_required
def get_user_prompt_limit(user):
    user_id = user['$id']
    MAX_PROMPTS_PER_DAY = 10
    prompts_remaining = MAX_PROMPTS_PER_DAY

    try:
        user_limit_docs = databases.list_documents(
            db_id,
            user_limits_collection_id,
            queries=[Query.equal('userId', user_id)]
        )
        user_limit_doc = user_limit_docs['documents'][0] if user_limit_docs['documents'] else None
        today_str = date.today().isoformat()

        if user_limit_doc:
            last_reset_date = user_limit_doc.get('lastResetDate')
            prompt_count = user_limit_doc.get('promptCount', 0)

            if last_reset_date != today_str:
                #new day, reset count
                prompts_remaining = MAX_PROMPTS_PER_DAY
            else:
                #Same day
                prompts_remaining = MAX_PROMPTS_PER_DAY - prompt_count
                if prompts_remaining < 0:
                    prompts_remaining = 0
        
        return jsonify({'promptsRemaining': prompts_remaining, 'maxPrompts': MAX_PROMPTS_PER_DAY})
    except Exception as e:
        print(f"Error fetching user prompt limit: {e}")
        return jsonify({'error': 'Failed to fetch prompt limit', 'details': str(e)}), 500


@app.route('/api/conversations/<conversation_id>', methods=['GET'])
@auth_required
def get_messages(user, conversation_id):
    try:
        #verify the user is the owner of this conversation
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
@auth_required
def delete_conversation(user, conversation_id):
    try:
        #Verify the user is the owner of this conversation
        convo = databases.get_document(db_id, conv_collection_id, conversation_id)
        if convo['userId'] != user['$id']:
            return jsonify({'error': 'Unauthorized'}), 403

        #Delete all messages associated with the conversation
        messages_to_delete = databases.list_documents(
            db_id,
            msg_collection_id,
            queries=[Query.equal('conversationId', conversation_id)]
        )
        for msg in messages_to_delete['documents']:
            databases.delete_document(db_id, msg_collection_id, msg['$id'])

        #Delete the conversation itself
        databases.delete_document(db_id, conv_collection_id, conversation_id)
        
        return jsonify({'message': 'Conversation and associated messages deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)