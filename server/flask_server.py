from flask import Flask, request, jsonify
from main import load_documents, split_documents, user_input, clear_database, get_vector_store, get_embedding_function, CHROMA_PATH
from langchain_chroma import Chroma
from flask_cors import CORS
from google import genai
import os

app = Flask(__name__); """Creating a new Flask app instance"""
CORS(app);
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

@app.route('/api/prompt/text-file', methods=['POST'])
def process_documents_without_voice():
    user_prompt = request.form.get('prompt')
    files = request.files.getlist('file')

    if not files:
        fallback_response = client.models.generate_content(model = "gemini-2.0-flash-001", contents =user_prompt)
        new_response = "No context provided \n Response from Gemini:\n" + fallback_response.text
        
        return jsonify({'answer': new_response})
    if not user_prompt:
        return jsonify({'error': 'Missing question argument'}), 400
    
    #clear_database()
    documents = load_documents(files)
    chunks = split_documents(documents)
    get_vector_store(chunks)
    
    embeddings = get_embedding_function()
    new_db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    docs = new_db.similarity_search_with_score(user_prompt, k=15)
    context_documents = [doc[0] for doc in docs]
    
    response = user_input(user_prompt, context_documents)
    if response == "Answer is not available in the context." or response == "Answer is not available in the context":
        fallback_response = client.models.generate_content(model = "gemini-2.0-flash", contents =user_prompt)
        new_response = "Couldn't find answer in context provided \n Response from Gemini:\n" + fallback_response.text
        return jsonify({'answer': new_response})
    return jsonify({'answer': response})


# @app.route('/api/prompt/{id}', method=['GET'])
# def yadayada():


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)