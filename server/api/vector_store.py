import os
import logging
import threading
from tenacity import retry, wait_exponential, stop_after_attempt
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Chroma is treated as a rebuildable index (cache)
# We keep a singleton per process to avoid repeated heavy init.
CHROMA_PATH = os.getenv("CHROMA_PATH", "chroma")
_vector_store = None
_embeddings = None
_lock = threading.Lock()


def _ensure_chroma_dir():
    try:
        os.makedirs(CHROMA_PATH, exist_ok=True)
    except Exception as exc:
        logging.error(f"Failed to create chroma directory {CHROMA_PATH}: {exc}")
        raise


def get_embedding_function():
    """Lazy singleton for embeddings; avoid per-request instantiation."""
    global _embeddings
    if _embeddings is None:
        if not os.getenv("GOOGLE_API_KEY"):
            raise RuntimeError("Missing GOOGLE_API_KEY for embeddings")
        _embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            output_dimensionality=768
        )
        logging.info("Embeddings initialized")
    return _embeddings


def get_vector_store():
    global _vector_store
    if _vector_store is None:
        with _lock:
            if _vector_store is None:
                _ensure_chroma_dir()
                embeddings = get_embedding_function()
                _vector_store = Chroma(
                    collection_name=os.getenv("CHROMA_COLLECTION", "rag"),
                    persist_directory=CHROMA_PATH,
                    embedding_function=embeddings
                )
                logging.info(f"Vector store initialized at {CHROMA_PATH}")
    return _vector_store


@retry(wait=wait_exponential(multiplier=2, min=5, max=60), stop=stop_after_attempt(5))
def add_documents_with_retry(db, batch, ids):
    """Add documents to vector store with retry logic"""
    db.add_documents(batch, ids=ids)


def reset_vector_store():
    """admin only reset hook; does not delete files."""
    global _vector_store
    _vector_store = None
