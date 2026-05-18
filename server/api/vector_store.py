import os
import logging
import threading
from tenacity import retry, wait_exponential, stop_after_attempt
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_google_genai import GoogleGenerativeAIEmbeddings

_vector_store = None
_embeddings = None
_lock = threading.Lock()


def get_embedding_function():
    global _embeddings
    if _embeddings is None:
        if not os.getenv("GOOGLE_API_KEY"):
            raise RuntimeError("Missing GOOGLE_API_KEY for embeddings")
        _embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001"
        ) #Sends in 3072 dimension output no matter what you give in for output_dimensionality attribute
        logging.info("Embeddings initialized")
    return _embeddings


def get_vector_store():
    global _vector_store
    if _vector_store is None:
        with _lock:
            if _vector_store is None:
                api_key = os.getenv("PINECONE_API_KEY")
                index_name = os.getenv("PINECONE_INDEX_NAME")
                
                if not api_key or not index_name:
                    raise ValueError("PINECONE API KEY and PINECONE INDEX NAME must be set in env")
                
                embeddings = get_embedding_function()
                pc = Pinecone(api_key=api_key)
                _vector_store = PineconeVectorStore(
                    index_name=index_name, 
                    embedding=embeddings
                )
                logging.info(f"Pinecone initialized for index: {index_name}")
    return _vector_store

def log_error(state):
    if state.outcome.failed:
        exception = state.outcome.exception()
        logging.warning(f"Push to vector store failed. Retrying... Error: {exception}")


@retry(wait=wait_exponential(multiplier=2, min=5, max=60), stop=stop_after_attempt(5), after=log_error)
def add_documents_with_retry(db, batch, ids):
    """Add documents to vector store with retry logic"""
    db.add_documents(batch, ids=ids)


def reset_vector_store():
    """admin only hook to delete vector index"""
    global _vector_store
    if _vector_store:
        api_key = os.getenv("PINECONE_API_KEY")
        index_name = os.getenv("PINECONE_INDEX_NAME")
        pc = Pinecone(api_key=api_key)

        try:
            index = pc.Index(index_name)
            index.delete(delete_all=True)
            logging.info(f"Wiped all vectors with the index {index_name}")
        except Exception as e:
            logging.error(f"Error in clearing vectors in the index {e}")


