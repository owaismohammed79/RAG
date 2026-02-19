from flask import Flask
from flask_cors import CORS
import os
from appwrite.client import Client
from appwrite.services.databases import Databases
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": os.getenv("FRONTEND_URL")}})
    
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["60 per minute"]
    )
    
    client = Client()
    client.set_endpoint(os.getenv("VITE_APPWRITE_ENDPOINT"))
    client.set_project(os.getenv("VITE_APPWRITE_PROJECT_ID"))
    client.set_key(os.getenv("VITE_APPWRITE_API_KEY"))
    
    app.client = client
    app.databases = Databases(client)
    app.db_id = os.getenv("VITE_APPWRITE_DATABASE_ID")
    app.conv_collection_id = os.getenv("VITE_APPWRITE_CONVERSATIONS_COLL_ID")
    app.msg_collection_id = os.getenv("VITE_APPWRITE_MESSAGES_COLL_ID")
    app.user_limits_collection_id = os.getenv("VITE_APPWRITE_USER_LIMITS_COLL_ID")
    
    from api.routes import api
    app.register_blueprint(api, url_prefix='/api')
    
    #Make appwrite services available globally
    global databases, db_id, conv_collection_id, msg_collection_id, user_limits_collection_id
    databases = app.databases
    db_id = app.db_id
    conv_collection_id = app.conv_collection_id
    msg_collection_id = app.msg_collection_id
    user_limits_collection_id = app.user_limits_collection_id
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)