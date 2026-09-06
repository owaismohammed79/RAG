# RAG (Rapid Answer Generator)

## 🚀 Project Overview

RAG (Rapid Answer Generator) is an intelligent web application designed to transform PDF documents into a queryable knowledge base. Users can upload PDFs, perform optical character recognition (OCR) on scanned files, and ask context-aware questions with instant AI-driven answers. The architecture features background ingestion, retention management, vector embeddings, and full container support.

---

## ✨ Features

* **Advanced PDF Processing**: Upload PDF documents (up to 2 files, max 5MB each) with automatic text extraction.
* **OCR Integration**: Performs automated OCR on scanned PDFs using `ocrmypdf` to guarantee text extractability.
* **Retrieval-Augmented Generation (RAG)**: Text is chunked, converted into vector embeddings via Google's models, and stored in ChromaDB or Pinecone for fast context retrieval.
* **Background Workers**: Dedicated background worker scripts (`ingestion_worker.py`) and retention policies (`retention.py`) manage asynchronous document processing and cleanup.
* **Context-Aware Chat & Fallback**: Retains conversation history to answer queries in context, with automatic fallback to Google Gemini for general knowledge questions.
* **Voice-to-Text Input**: Speech recognition API integration allows hands-free voice search.
* **Authentication & Usage Limits**: Appwrite BaaS integration supports Email/Password and Google OAuth login while enforcing daily prompt usage limits per user.
* **Modular Architecture**: Restructured modular Python backend (`server/api/`) organizing authentication, AI services, user management, and vector storage.
* **Modern Responsive Interface**: React, Vite, Tailwind CSS, and shadcn/ui frontend managed with Redux Toolkit.
* **Containerization**: Standardized deployment setup provided via a root `Dockerfile`.

---

## 🛠️ Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React, Vite, Tailwind CSS, shadcn/ui, Redux Toolkit, React Router DOM, Lucide React |
| **Backend** | Flask (Python), LangChain, Appwrite Python SDK, Pinecone, PyPDFLoader, `ocrmypdf` |
| **AI & Embeddings** | Google Gemini API & Google Vector Embeddings |
| **Services & Workers** | Appwrite BaaS, Ingestion Worker, Retention Service |
| **DevOps** | Docker |

---

## 🏗️ Architecture

Below is a high-level overview of the RAG application's architecture:

![RAG Architecture Diagram](./client/public/RAG%20architecture.png)

## 📺 Demo Video

Watch a quick demonstration of RAG in action, from setting up to querying your documents:

[![RAG Demo Video](./client/public/DemoIcon.png)](https://screenrec.com/share/U7RV108Ovx)


## 📁 Project Structure

```text
├── Dockerfile
├── README.md
├── client/
│   ├── public/
│   ├── src/
│   │   ├── appwrite(service)/
│   │   ├── components/
│   │   ├── config/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── pages/
│   │   ├── redux/
│   │   └── utils/
│   └── package.json
└── server/
    ├── api/
    │   ├── ai_service.py
    │   ├── appwrite_utils.py
    │   ├── auth.py
    │   ├── documents.py
    │   ├── ingestion_worker.py
    │   ├── retention.py
    │   ├── routes.py
    │   ├── user_service.py
    │   └── vector_store.py
    ├── app.py
    └── requirements.txt
```


## 🚀 Getting Started

### Prerequisites

* Node.js (v18 or higher)
* Python (v3.9 or higher)
* npm or Yarn
* `ocrmypdf` (installed via `pip install ocrmypdf` or system package manager)
* Docker (optional, for containerized execution)

---

### 1. Clone the Repository

```bash
git clone https://github.com/owaismohammed79/RAG
cd RAG
```

---

### 2. Backend Setup (Flask Server)

Navigate to the `server` directory:

```bash
cd server
```

Create a Python virtual environment and activate it:

```bash
# On Windows
python -m venv venv
.\venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the `server` directory by copying `.env.sample` and fill in your credentials:

```
# server/.env
FRONTEND_URL="http://localhost:5173"
VITE_APPWRITE_ENDPOINT="https://cloud.appwrite.io/v1"
VITE_APPWRITE_PROJECT_ID="YOUR_APPWRITE_PROJECT_ID"
VITE_APPWRITE_API_KEY="YOUR_APPWRITE_API_KEY"
VITE_APPWRITE_DATABASE_ID="YOUR_APPWRITE_DATABASE_ID"
VITE_APPWRITE_CONVERSATIONS_COLL_ID="YOUR_CONVERSATIONS_COLLECTION_ID"
VITE_APPWRITE_MESSAGES_COLL_ID="YOUR_MESSAGES_COLLECTION_ID"
VITE_APPWRITE_USER_LIMITS_COLL_ID="YOUR_USER_LIMITS_COLLECTION_ID"
GOOGLE_API_KEY="YOUR_GOOGLE_GEMINI_API_KEY"
PINECONE_API_KEY="YOUR_PINECONE_API_KEY"
PINECONE_INDEX_NAME="YOUR_PINECONE_INDEX_NAME"
```

Run the Flask server:

```bash
flask run
```

### 3. Frontend Setup (React Vite)

Open a new terminal and navigate to the `client` directory:

```bash
cd client
```

Install the Node.js dependencies:

```bash
npm install
```

Create a `.env` file in the `client` directory by copying `.env.sample` and fill in your credentials:

```
# client/.env
VITE_APPWRITE_PROJECT_ID="YOUR_APPWRITE_PROJECT_ID"
VITE_APPWRITE_ENDPOINT="https://cloud.appwrite.io/v1"
VITE_APPWRITE_DATABASE_ID="YOUR_APPWRITE_DATABASE_ID"
VITE_APPWRITE_USERS_COLL_ID="YOUR_USERS_COLLECTION_ID"
VITE_APPWRITE_USER_LIMITS_COLL_ID="YOUR_USER_LIMITS_COLLECTION_ID"
VITE_GOOGLE_OAUTH_CLIENT_ID="YOUR_GOOGLE_OAUTH_CLIENT_ID"
VITE_EMAIL_ADDRESS="your-contact-email@example.com"
VITE_BACKEND_URL="http://127.0.0.1:5000"
VITE_BASE_URL="http://localhost:5173"
```

Start the React development server:

```bash
npm run dev
```

---

### 4. Docker Deployment

To run the application inside a container:

```bash
docker build -t rag-application .
docker run -p 5000:5000 rag-application
```

---

## 🤝 Contributing

1. Fork the repository.
2. Create a new feature branch (`git checkout -b feature/your-feature-name`).
3. Commit your changes (`git commit -m 'Add new feature'`).
4. Push to the branch (`git push origin feature/your-feature-name`).
5. Open a Pull Request.