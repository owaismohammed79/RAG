import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime

logger = logging.getLogger(__name__)

def generate_rag_response(user_question, context_documents, history):
    """Generate RAG response using context documents"""
    context = "\n\n".join([doc.page_content for doc in context_documents])
    
    history_str_prompt = ""
    for message in history:
        role = "User" if message.get('type') == 'user' else "bot"
        history_str_prompt += f"{role}: {message.get('content')}\n"
    
    rag_prompt = f"""
You are an expert RAG assistant that answers questions based on the provided documents and previous conversation.
Provide a detailed answer to the question based on the following context.
If the answer is not in the provided context, just say, "Answer is not available in the context".
Don't provide the wrong answer.

Previous conversation:
{history_str_prompt}

Context from documents:
{context}

Question:
{user_question}

Answer:
"""
    
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.3)
    return model.stream(rag_prompt)

def generate_fallback_response(user_question, history):
    """Generate fallback response using general knowledge"""
    history_str_prompt = ""
    for message in history:
        role = "User" if message.get('type') == 'user' else "bot"
        history_str_prompt += f"{role}: {message.get('content')}\n"
    
    fallback_prompt = f"""
Previous conversation:
{history_str_prompt}

Question:
{user_question}

Answer:
"""
    
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.7)
    return model.stream(fallback_prompt)

def save_message_to_db(supabase, conversation_id, sender_type, content, user_id):
    """Save message to Supabase database"""
    supabase.table("messages").insert({
        "conversation_id": conversation_id,
        "user_id": user_id,
        "sender_type": sender_type,
        "content": content,
        "created_at": datetime.now().isoformat()
    }).execute()