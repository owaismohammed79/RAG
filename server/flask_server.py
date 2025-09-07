from flask import Flask, request, jsonify
from main import load_documents, split_documents, user_input, get_vector_store, get_embedding_function, CHROMA_PATH
from langchain_chroma import Chroma
from flask_cors import CORS
from google import genai
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
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": os.getenv("FRONTEND_URL")}})
gemini_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

#Appwrite Client Initialization
client = Client()
client.set_endpoint(os.getenv("VITE_APPWRITE_ENDPOINT"))
client.set_project(os.getenv("VITE_APPWRITE_PROJECT_ID"))
client.set_key(os.getenv("VITE_APPWRITE_API_KEY"))

#This account instance is for admin tasks if needed, not user auth
account = Account(client)
databases = Databases(client)
db_id = os.getenv("VITE_APPWRITE_DATABASE_ID")
conv_collection_id = os.getenv("VITE_APPWRITE_CONVERSATIONS_COLL_ID")
msg_collection_id = os.getenv("VITE_APPWRITE_MESSAGES_COLL_ID")

#Authentication Decorator
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        jwt = request.headers.get('Authorization')
        if not jwt:
            return jsonify({'error': 'Missing token'}), 401
        
        try:
            jwt_token = jwt.split(' ')[1]

            #Creating a temporary, request specific client to verify the users JWT
            user_client = Client()
            user_client.set_endpoint(os.getenv("VITE_APPWRITE_ENDPOINT"))
            user_client.set_project(os.getenv("VITE_APPWRITE_PROJECT_ID"))
            user_client.set_jwt(jwt_token)

            user_account = Account(user_client)
            user = user_account.get() # This verifies the JWT and gets the user
            kwargs['user'] = user
        except Exception as e:
            return jsonify({'error': 'Invalid or expired token', 'details': str(e)}), 401
        
        return f(*args, **kwargs)
    return decorated_function


@app.route('/api/prompt/text-file', methods=['POST'])
@auth_required
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

    #new conversation
    if not conversation_id or conversation_id == 'null':
        try:
            doc = databases.create_document(
                db_id,
                conv_collection_id,
                ID.unique(),
                {
                    'title': user_prompt[:50], 
                    'userId': user_id,
                    'lastMessageAt': current_timestamp
                },
                permissions=[ #Set permissions directly
                    Permission.read(Role.user(user_id)),
                    Permission.update(Role.user(user_id)),
                    Permission.delete(Role.user(user_id)),
                ]
            )
            conversation_id = doc['$id']
        except Exception as e:
            return jsonify({'error': f'Failed to create conversation: {e}'}), 500
    else:
        #update lastMessageAt for existing conversation
        try:
            databases.update_document(
                db_id,
                conv_collection_id,
                conversation_id,
                {'lastMessageAt': current_timestamp}
            )
        except Exception as e:
            print(f"Error updating lastMessageAt for conversation {conversation_id}: {e}")


    try:
        databases.create_document(
            db_id,
            msg_collection_id,
            ID.unique(),
            {
                'conversationId': conversation_id, 
                'senderType': 'user', 
                'content': user_prompt,
                'timestamp': current_timestamp
            },
            permissions=[ #set permissions directly
                Permission.read(Role.user(user_id)),
                Permission.update(Role.user(user_id)),
                Permission.delete(Role.user(user_id)),
            ]
        )
    except Exception as e:
        #print this error but continue, as getting an answer is more important
        print(f"Error saving user message: {e}")

    if files:
        documents = load_documents(files)
        chunks = split_documents(documents)
        #add user_id to metadata for filtering
        for chunk in chunks:
            chunk.metadata['user_id'] = user_id
        get_vector_store(chunks)
    
    embeddings = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    
    #similarity search with user_id filter
    retriever = db.as_retriever(search_kwargs={'k': 15, 'filter': {'user_id': user_id}})
    docs = retriever.get_relevant_documents(user_prompt)
    
    context_documents = docs if docs else []

    response_text = user_input(user_prompt, context_documents, history)
    
    if "Answer is not available in the context" in response_text:
        fallback_response = gemini_client.models.generate_content(model="gemini-1.5-flash", contents=user_prompt)
        response_text = "Couldn't find answer in context provided.\nResponse from Gemini:\n" + fallback_response.text

    try:
        databases.create_document(
            db_id,
            msg_collection_id,
            ID.unique(),
            {
                'conversationId': conversation_id, 
                'senderType': 'bot', 
                'content': response_text,
                'timestamp': datetime.now().isoformat()
            },
            permissions=[ #set permissions directly
                Permission.read(Role.user(user_id)),
                Permission.update(Role.user(user_id)),
                Permission.delete(Role.user(user_id)),
            ]
        )
    except Exception as e:
        print(f"Error saving bot message: {e}")

    return jsonify({'answer': response_text, 'conversationId': conversation_id})

@app.route('/api/conversations', methods=['GET'])
@auth_required
def get_conversations(user):
    try:
        result = databases.list_documents(
            db_id,
            conv_collection_id,
            queries=[Query.equal('userId', user['$id']), Query.order_desc('$updatedAt')]
        )
        return jsonify(result['documents'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
@auth_required
def get_messages(user, conversation_id):
    try:
        #verify if user owns this conversation
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
        #verify if user owns this conversation
        convo = databases.get_document(db_id, conv_collection_id, conversation_id)
        if convo['userId'] != user['$id']:
            return jsonify({'error': 'Unauthorized'}), 403

        #delete all messages associated with the conversation
        messages_to_delete = databases.list_documents(
            db_id,
            msg_collection_id,
            queries=[Query.equal('conversationId', conversation_id)]
        )
        for msg in messages_to_delete['documents']:
            databases.delete_document(db_id, msg_collection_id, msg['$id'])

        #delete conversation
        databases.delete_document(db_id, conv_collection_id, conversation_id)
        
        return jsonify({'message': 'Conversation and associated messages deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)