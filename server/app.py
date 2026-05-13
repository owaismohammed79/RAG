from gevent import monkey
monkey.patch_all()
from flask import Flask
from flask_cors import CORS
import os
import logging
from appwrite.client import Client
from appwrite.services.databases import Databases
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

# Configure basic logging early so startup events are visible on Render
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)


def create_app():
    app = Flask(__name__)
    logging.info("Process start: Flask app factory invoked")

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
    app.docs_collection_id = os.getenv("VITE_APPWRITE_DOCUMENTS_COLL_ID")
    app.chunks_collection_id = os.getenv("VITE_APPWRITE_CHUNKS_COLL_ID")
    app.jobs_collection_id = os.getenv("VITE_APPWRITE_INGESTION_JOBS_COLL_ID")

    from api.routes import api
    app.register_blueprint(api, url_prefix='/api')

    # Make appwrite services available globally
    global databases, db_id, conv_collection_id, msg_collection_id, user_limits_collection_id
    global docs_collection_id, chunks_collection_id, jobs_collection_id
    databases = app.databases
    db_id = app.db_id
    conv_collection_id = app.conv_collection_id
    msg_collection_id = app.msg_collection_id
    user_limits_collection_id = app.user_limits_collection_id
    docs_collection_id = app.docs_collection_id
    chunks_collection_id = app.chunks_collection_id
    jobs_collection_id = app.jobs_collection_id

    #Start ingestion worker loop after variables are set
    try:
        from api.ingestion_worker import start_worker_once
        start_worker_once(app)
        logging.info("Background ingestion worker initialized")
    except Exception as worker_err:
        logging.error(f"Ingestion worker failed to start: {worker_err}")

    logging.info("Health endpoint ready at /api/health")
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)