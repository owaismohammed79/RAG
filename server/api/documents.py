from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import tempfile
import subprocess
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema.document import Document
import re
import logging

logger = logging.getLogger(__name__)

def _run_ocrmypdf(input_path, output_path, language="eng"):
    """Run OCR on a PDF file"""
    command = [
        "ocrmypdf",
        "-l", language,
        "--output-type", "pdf",
        "--force-ocr",
        input_path, output_path
    ]
    
    logger.info(f"Attempting OCR with ocrmypdf for '{os.path.basename(input_path)}'...")
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        logger.info(f"OCR successful for '{os.path.basename(input_path)}'")
        return True, None
    except subprocess.CalledProcessError as e:
        error_msg = f"ocrmypdf failed for '{os.path.basename(input_path)}' with exit code {e.returncode}.\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}"
        logger.error(error_msg)
        return False, error_msg
    except FileNotFoundError:
        error_msg = "Error: 'ocrmypdf' command not found"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred while running ocrmypdf: {e}"
        logger.error(error_msg)
        return False, error_msg

def load_documents(file_array):
    """Load documents from uploaded files"""
    all_documents = []
    
    with tempfile.TemporaryDirectory() as tempdir:
        saved_file_paths = []
        
        #save uploaded files
        for i, file in enumerate(file_array):
            if not hasattr(file, 'filename'):
                raise ValueError("Invalid file object received")
                
            file_path = os.path.join(tempdir, f"uploaded_file_{i}_{file.filename}")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            try:
                file.save(file_path)
                saved_file_paths.append(file_path)
            except AttributeError:
                logger.error("Invalid object file type recieved")
        
        for file_path in saved_file_paths:
            documents_for_this_pdf = []
            is_scanned = False
            total_chars_pypdf = 0
            
            #load with pypdf 
            try:
                pypdf_loader = PyPDFLoader(file_path)
                pypdf_docs = pypdf_loader.load()
                documents_for_this_pdf.extend(pypdf_docs)
                
                if not pypdf_docs:
                    logger.info(f"PyPDFLoader found no text for {file_path}, assuming scanned PDF")
                    is_scanned = True
                elif len(pypdf_docs) > 0 and (sum(len(doc.page_content) for doc in pypdf_docs) / len(pypdf_docs) < 500):
                    logger.info(f"Low character density for {file_path}, assuming potential scanned PDF")
                    is_scanned = True
                else:
                    logger.info(f"Loaded {file_path} as a native PDF")
            except Exception as e:
                logger.error(f"Error with PyPDFLoader for {file_path}: {e}")
                is_scanned = True
            
            #fallback to OCR if pypdf fails
            if is_scanned:
                ocr_output_path = os.path.join(tempdir, f"ocr_output_{os.path.basename(file_path)}")
                ocr_successful, ocr_error_message = _run_ocrmypdf(file_path, ocr_output_path, language="eng")
                
                if ocr_successful:
                    try:
                        ocr_loader = PyPDFLoader(ocr_output_path)
                        ocr_docs = ocr_loader.load()
                        total_chars_ocr = sum(len(doc.page_content) for doc in ocr_docs)
                        total_chars_pypdf = sum(len(doc.page_content) for doc in pypdf_docs) if pypdf_docs else 0
                        
                        if total_chars_ocr > total_chars_pypdf * 1.1:
                            logger.info(f"Using OCR'd content for {file_path}")
                            all_documents.extend(ocr_docs)
                        elif not pypdf_docs and ocr_docs:
                            logger.info(f"OCR extracted content where pypdf found none for {file_path}")
                            all_documents.extend(ocr_docs)
                        elif pypdf_docs and ocr_docs and total_chars_ocr <= total_chars_pypdf * 1.1:
                            logger.info(f"OCR did not significantly improve content for {file_path}, sticking with original pypdf content")
                            all_documents.extend(pypdf_docs)
                        else:
                            if documents_for_this_pdf:
                                all_documents.extend(documents_for_this_pdf)
                            else:
                                logger.info(f"No content extracted by any method for {file_path}")
                    except Exception as ocr_load_e:
                        logger.error(f"Error loading OCR'd PDF '{ocr_output_path}': {ocr_load_e}")
                        if documents_for_this_pdf:
                            all_documents.extend(documents_for_this_pdf)
                else:
                    logger.error(f"OCR with ocrmypdf failed for {file_path}: {ocr_error_message}")
                    if documents_for_this_pdf:
                        all_documents.extend(documents_for_this_pdf)
            else:
                all_documents.extend(documents_for_this_pdf)
                logger.info(f"Using native PDF content for {file_path}")
    
    return all_documents

def split_documents(documents: list[Document]):
    """Split documents into chunks"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)

def calculate_chunk_ids(chunks):
    """Calculate unique IDs for document chunks"""
    last_page_id = None
    current_chunk_index = 0
    
    for chunk in chunks:
        source = chunk.metadata.get("source")
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

def prioritize_chunks(chunks, user_prompt):
    """Reorder chunks based on relevance to user prompt"""
    if not user_prompt:
        return chunks
    
    def get_tokens(text):
        return set(re.findall(r'\w+', text.lower()))
    
    prompt_tokens = get_tokens(user_prompt)
    
    if len(prompt_tokens) == 0:
        return chunks
    
    scored_chunks = []
    for chunk in chunks:
        chunk_tokens = get_tokens(chunk.page_content)
        score = len(prompt_tokens.intersection(chunk_tokens))
        scored_chunks.append((score, chunk))
    
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_chunks]