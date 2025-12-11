from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import stat
from tenacity import retry, wait_exponential, stop_after_attempt
from typing import List
from langchain_community.document_loaders import PyPDFLoader
import google.generativeai as genai
from google.generativeai import types
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain.schema.document import Document 
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import shutil
import tempfile
import subprocess #to run the command as though it ran in the terminal using python subprocess  
from dotenv import load_dotenv
import json
import traceback
from datetime import datetime
from appwrite.id import ID
from appwrite.permission import Permission
from appwrite.role import Role
# import logging
# logging.basicConfig(level=logging.DEBUG)

load_dotenv()
CHROMA_PATH="chroma"
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
data_path = r"data"
#data_path=r"no_data"

def _run_ocrmypdf(input_path, output_path, language="eng"):
    #command to execute along with aguments
    command = [
        "ocrmypdf",
        # "--skip-text", forces ocr even if some text is found
        "-l", language,
        "--output-type", "pdf",
        "--force-ocr",
        # "--deskew", can be used for very skewed scans
        input_path,
        output_path
    ]

    print(f"Attempting OCR with ocrmypdf for '{os.path.basename(input_path)}'...")

    try:
        # check=True is if there occurs any error then except will be called
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"OCR successful for '{os.path.basename(input_path)}'")
        return True, None
    except subprocess.CalledProcessError as e:
        error_msg = f"ocrmypdf failed for '{os.path.basename(input_path)}' with exit code {e.returncode}.\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}"
        print(error_msg)
        return False, error_msg
    except FileNotFoundError:
        error_msg = "Error: 'ocrmypdf' command not found"
        print(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred while running ocrmypdf: {e}"
        print(error_msg)
        return False, error_msg
    

def load_documents(file_array):
    all_documents = []
    with tempfile.TemporaryDirectory() as tempdir:
        saved_file_paths = []
        for i, file in enumerate(file_array):
            if not hasattr(file, 'filename'):
                raise ValueError("Invalid file object received")
            
            file_path = os.path.join(tempdir, f"uploaded_file_{i}_{file.filename}")
            os.makedirs(os.path.dirname(file_path), exist_ok=True) 
            
            try:
                file.save(file_path)
            except AttributeError:
                print("Invalid object file type recieved")
                
            saved_file_paths.append(file_path)

        for file_path in saved_file_paths:
            documents_for_this_pdf = []
            is_scanned = False
            total_chars_pypdf = 0

            #load with pypdfoader first
            try:
                pypdf_loader = PyPDFLoader(file_path)
                pypdf_docs = pypdf_loader.load()
                documents_for_this_pdf.extend(pypdf_docs) #acts as 

                total_chars_pypdf = sum(len(doc.page_content) for doc in pypdf_docs)

                #Check if pdf is scanned
                if not pypdf_docs:
                    print(f"PyPDFLoader found no text for {file_path}, assuming scanned PDF")
                    is_scanned = True
                elif len(pypdf_docs) > 0 and (total_chars_pypdf / len(pypdf_docs) < 500):
                    print(f"Low character density ({total_chars_pypdf / len(pypdf_docs):.2f} chars/page) for {file_path}, assuming potential scanned PDF")
                    is_scanned = True
                else:
                    print(f"Loaded {file_path} as a native PDF")

            except Exception as e:
                print(f"Error with PyPDFLoader for {file_path}: {e}")
                is_scanned = True #Fallback to OCR if pypdf fails

            if is_scanned:
                ocr_output_path = os.path.join(tempdir, f"ocr_output_{os.path.basename(file_path)}")
                ocr_successful, ocr_error_message = _run_ocrmypdf(file_path, ocr_output_path, language="eng")

                if ocr_successful:
                    try:
                        #load new content from OCR'd pdf
                        ocr_loader = PyPDFLoader(ocr_output_path)
                        ocr_docs = ocr_loader.load()
                        
                        total_chars_ocr = sum(len(doc.page_content) for doc in ocr_docs)
                        
                        if total_chars_ocr > total_chars_pypdf * 1.1: #use OCR'd content if it adds at least 10% more chars
                            print(f"Using OCR'd content for {file_path} (OCR chars: {total_chars_ocr}, pypdf chars: {total_chars_pypdf})")
                            all_documents.extend(ocr_docs)
                        elif not pypdf_docs and ocr_docs: #OCR got something, pypdf got nothing
                            print(f"OCR extracted content where pypdf found none for {file_path}")
                            all_documents.extend(ocr_docs)
                        elif pypdf_docs and ocr_docs and total_chars_ocr <= total_chars_pypdf * 1.1:
                            print(f"OCR did not significantly improve content for {file_path}, sticking with original pypdf content")
                            all_documents.extend(pypdf_docs)
                        else:
                            print(f"OCR did not produce usable content for {file_path}. If pypdf had content, it will be used")
                            if documents_for_this_pdf: #if pypdf had anything originally
                                all_documents.extend(documents_for_this_pdf)
                            else:
                                print(f"No content extracted by any method for {file_path}. Skipping this file")

                    except Exception as ocr_load_e:
                        print(f"Error loading OCR'd PDF '{ocr_output_path}' with PyPDFLoader: {ocr_load_e}")
                        if documents_for_this_pdf:
                            print("Falling back to original PyPDFLoader content (if any)")
                            all_documents.extend(documents_for_this_pdf)
                        else:
                            print(f"Could not process {file_path} with any loader or OCR. Skipping this file")
                else: #ocrmypdf failed
                    print(f"OCR with ocrmypdf failed for {file_path}: {ocr_error_message}")
                    if documents_for_this_pdf:
                        print("Falling back to original PyPDFLoader content")
                        all_documents.extend(documents_for_this_pdf)
                    else:
                        print(f"Could not process {file_path} with any loader or OCR. Skipping this file")
            else:
                #documents were already added
                all_documents.extend(documents_for_this_pdf)
                print(f"Using native PDF content for {file_path}")

    return all_documents
    

def split_documents(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)

# Retry decorator for API calls
@retry(wait=wait_exponential(multiplier=2, min=5, max=60), stop=stop_after_attempt(5))
def add_documents_with_retry(db, batch, ids):
    db.add_documents(batch, ids=ids)


def get_embedding_function():
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    return embeddings

def calculate_chunk_ids(chunks):

    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source =  chunk.metadata.get("source")
        page = chunk.metadata.get("page")
        current_page_id = f"{source}:{page}"


        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id
        chunk.metadata["id"] = chunk_id

    return chunks

def onexc_handler(func, path, exc_info):
    """
    Error handler for shutil.rmtree, Changes permissions on read only files and retries the operation.
    """
    exception_object = exc_info[1]
    if isinstance(exception_object, OSError) and 'winerror' in dir(exception_object) and exception_object.winerror == 5:
        file_path = exception_object.filename
        os.chmod(file_path, stat.S_IWRITE)        
        func(file_path)
    else:
        raise
        

def clear_database():
    if os.path.exists(CHROMA_PATH):
        try:
            db = Chroma(persist_directory=CHROMA_PATH, embedding_function=get_embedding_function())
            db.reset()
        except Exception as e:
            print(f"Error closing Chroma client: {e}")
        
        try:
            shutil.rmtree(CHROMA_PATH, onexc=onexc_handler)
        except PermissionError as e:
            print(f"Failed to delete Chroma database: {e}")



def generate_stream(user_id, conversation_id, user_question, context_documents, history, databases, db_id: str, msg_collection_id: str):
    """Generates a streamed response and saves the final answer to the DB"""
    final_answer_for_db = ""
    rag_response_buffer = ""
    
    context = "\n\n".join([doc.page_content for doc in context_documents])
    logger.info("Relevant context extracted")
    history_str_prompt = ""
    for message in history:
        role = "User" if message.get('type') == 'user' else "bot"
        history_str_prompt += f"{role}: {message.get('content')}\n"
    logger.info("Appended relevant context")
    try:
        rag_prompt = f"""
        You are an expert RAG assistant that answers questions based on the provided documents and previous conversation. Provide a detailed answer to the question based on the following context.
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
        logger.info("LLM call starting")
        model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", temperature=0.3)
        logger.info("LLM call done")

        print("Starting RAG stream...")
        rag_stream = model.stream(rag_prompt)
        
        for chunk in rag_stream:
            chunk_content = chunk.content
            if chunk_content:
                rag_response_buffer += chunk_content
                # Sending a JSON event for each RAG chunk
                yield json.dumps({"type": "rag_chunk", "content": chunk_content}) + "\n"
        logger.info("Normal chunks sent")

        if "Answer is not available in the context" in rag_response_buffer:
            print("RAG context not found. Switching to fallback stream")
            prefix = "Couldn't find answer in context provided.\nResponse from Gemini:\n"
            # Send a special event to tell the frontend to clear its text as context was unavailable
            yield json.dumps({"type": "fallback_start", "content": prefix}) + "\n"

            fallback_prompt = f"""
            Previous conversation:
            {history_str_prompt}
            
            Question:
            {user_question}

            Answer:
            """
            logger.info("Fallback starting")
            fallback_model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", temperature=0.7)
            fallback_stream = fallback_model.stream(fallback_prompt)
            logger.info("LLM starts fallback streaming")

            fallback_buffer = ""
            for chunk in fallback_stream:
                chunk_content = chunk.content
                if chunk_content:
                    fallback_buffer += chunk_content
                    yield json.dumps({"type": "fallback_chunk", "content": chunk_content}) + "\n"
            logger.info("Fallback stream done")
            
            # Final answer to save in db
            final_answer_for_db = "Couldn't find answer in context provided.\nResponse from Gemini:\n" + fallback_buffer
        
        else:
            print("RAG stream successful")
            final_answer_for_db = rag_response_buffer
        
        # Save final answer to DB
        try:
            databases.create_document(
                db_id,
                msg_collection_id,
                ID.unique(),
                {
                    'conversationId': conversation_id, 
                    'senderType': 'bot', 
                    'content': final_answer_for_db,
                    'timestamp': datetime.now().isoformat()
                },
                permissions=[
                    Permission.read(Role.user(user_id)),
                    Permission.update(Role.user(user_id)),
                    Permission.delete(Role.user(user_id)),
                ]
            )
            logger.info("Answer saved to db")
            print("Final answer saved to DB")
        except Exception as e:
            print(f"Error saving bot message after stream: {e}")
    
    except Exception as e:
        print(f"Error during AI stream generation: {e}")
        traceback.print_exc()
        yield json.dumps({"type": "error", "content": f"An error occurred: {str(e)}"}) + "\n"
    

def main():
    # clear_database()

    print("Chat With Multiple PDF")
    print("Chat with PDF using Gemini: ")

    documents = load_documents()

    # If no documents are found, handle it by directly querying Gemini
    if not documents:
        print("No PDFs found, using Gemini Pro for direct answers.")

        user_question = input("Ask a question (without PDF context): ")

        if user_question:
            model = genai.GenerativeModel("gemini-2.0-flash-lite")
            response = model.invoke(user_question)
    else:
        # Documents exist, proceed with processing
        chunks = split_documents(documents)
        get_vector_store(chunks)
        print("PDFs loaded and processed.")

        user_question = input("Ask a question from the PDF Files: ")

        if user_question:
            embeddings = get_embedding_function()
            new_db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
            docs = new_db.similarity_search_with_score(user_question, k=15)
            
            context_documents = [doc[0] for doc in docs]
            res = user_input(user_question, context_documents, [])
            print(res)