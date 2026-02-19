from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
from tenacity import retry, wait_exponential, stop_after_attempt

CHROMA_PATH = "chroma"

@retry(wait=wait_exponential(multiplier=2, min=5, max=60), stop=stop_after_attempt(5))
def add_documents_with_retry(db, batch, ids):
    """Add documents to vector store with retry logic"""
    db.add_documents(batch, ids=ids)

def get_embedding_function():
    """Get embedding function for vector store"""
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", output_dimensionality=768)
    return embeddings

def get_vector_store():
    """Get or create vector store instance"""
    embeddings = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    return db