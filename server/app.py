from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
from .api.routes import limiter

load_dotenv()
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)

def create_app():
    app = Flask(__name__)
    logging.info("Process start: Flask app factory invoked")

    CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": os.getenv("FRONTEND_URL")}})

    limiter.init_app(app)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify(error="Network rate limit exceeded. Please try again tomorrow."), 429

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    app.supabase: Client = create_client(supabase_url, supabase_key)

    from api.routes import api
    app.register_blueprint(api, url_prefix='/api')

    try:
        from api.vector_store import get_vector_store
        get_vector_store()
    except Exception as init_err:
        logging.error(f"Failed to eager-load vector store: {init_err}")

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