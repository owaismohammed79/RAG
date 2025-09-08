# RAG (Rapid Answer Generator)

## 🚀 Project Overview

RAG (Rapid Answer Generator) is an intelligent web application designed to transform your PDF documents into a personal, queryable knowledge base. Upload your PDFs, ask questions, and receive precise, context-aware answers instantly. Whether for research, study, or decision-making, RAG empowers you to extract maximum value from your documents efficiently.

## ✨ Features

*   **Intelligent Document Analysis**: Upload multiple PDF documents, and RAG will process them to create a comprehensive knowledge base.
*   **Contextual Q&A**: Ask questions related to your uploaded documents and get accurate, summarized answers.
*   **Voice Search**: Interact with RAG using your voice for a hands-free, intuitive querying experience.
*   **Gemini Integration**: Leverages Google Gemini API for powerful language model capabilities, providing intelligent responses even without document context.
*   **Conversation History**: Keeps track of your past conversations, allowing you to revisit and continue discussions.
*   **Secure Authentication**: User authentication powered by Appwrite, including Google OAuth for easy sign-in.
*   **Responsive UI**: Built with React and Tailwind CSS for a seamless experience across devices.

## 🛠️ Tech Stack

The application is built with a modern, full-stack architecture, leveraging powerful tools for both the frontend and backend.

### Frontend

*   **Framework**: [React.js](https://reactjs.org/) for building a dynamic and responsive user interface.
*   **Build Tool**: [Vite](https://vitejs.dev/) for a fast development experience and optimized builds.
*   **Styling**: [Tailwind CSS](https://tailwindcss.com/) for utility-first styling.
*   **UI Components**: [shadcn/ui](https://ui.shadcn.com/) for pre-built, accessible, and customizable components.
*   **State Management**: [Redux Toolkit](https://redux-toolkit.js.org/) for managing global application state.
*   **Routing**: [React Router DOM](https://reactrouter.com/) for client-side navigation.
*   **Icons**: [Lucide React](https://lucide.dev/) for a comprehensive icon library.

### Backend

*   **Server**: [Flask](https://flask.palletsprojects.com/) (Python) for handling API requests, document processing, and AI interactions.
*   **BaaS (Backend as a Service)**: [Appwrite](https://appwrite.io/) for user authentication and database management.
*   **AI/RAG Framework**: [LangChain](https://www.langchain.com/) (Python) for orchestrating Retrieval-Augmented Generation workflows.
*   **AI Model**: [Google Gemini API](https://ai.google.dev/) for powerful language model capabilities.
*   **Vector Database**: [ChromaDB](https://www.trychroma.com/) for efficient storage and retrieval of document embeddings.
*   **PDF Processing**: [PyPDFLoader](https://python.langchain.com/docs/integrations/document_loaders/pypdf) and `ocrmypdf` for extracting text from PDF documents, including scanned ones.

## 🏗️ Architecture

Below is a high-level overview of the RAG application's architecture:

![RAG Architecture Diagram](https://example.com/path/to/your/architecture-diagram.png)

## 📺 Demo Video

Watch a quick demonstration of RAG in action, from setting up to querying your documents:

[![RAG Demo Video](https://img.youtube.com/vi/YOUR_VIDEO_ID/0.jpg)](https://www.youtube.com/watch?v=YOUR_VIDEO_ID)

## 🚀 Getting Started

Follow these instructions to set up and run the RAG application on your local machine.

### Prerequisites

*   Node.js (v18 or higher)
*   Python (v3.9 or higher)
*   npm or Yarn
*   `ocrmypdf` (install via `pip install ocrmypdf` or your system's package manager)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/rag-project.git
cd rag-project
```

### 2. Backend Setup (Python Flask)

Navigate to the `server` directory:

```bash
cd server
```

Create a Python virtual environment and activate it:

```bash
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the `server` directory based on `server/.env.sample` and fill in your credentials:

```
# server/.env
APPWRITE_PROJECT_ID=YOUR_APPWRITE_PROJECT_ID
APPWRITE_API_KEY=YOUR_APPWRITE_API_KEY
APPWRITE_DB_ID=YOUR_APPWRITE_DATABASE_ID
APPWRITE_CONVERSATIONS_COLL_ID=YOUR_APPWRITE_CONVERSATIONS_COLLECTION_ID
APPWRITE_MESSAGES_COLL_ID=YOUR_APPWRITE_MESSAGES_COLLECTION_ID
GOOGLE_API_KEY=YOUR_GOOGLE_GEMINI_API_KEY
```

Run the Flask server:

```bash
flask run

python -m flask run
```
The backend server will typically run on `http://127.0.0.1:5000`.

### 3. Frontend Setup (React Vite)

Open a new terminal, navigate to the `client` directory:

```bash
cd ../client
```

Install the Node.js dependencies:

```bash
npm install

yarn install
```

Create a `.env` file in the `client` directory based on `client/.env.sample` and fill in your credentials:

```
# client/.env
VITE_APPWRITE_PROJECT_ID=YOUR_APPWRITE_PROJECT_ID
VITE_APPWRITE_ENDPOINT=https://cloud.appwrite.io/v1 # Or your custom Appwrite endpoint
VITE_APPWRITE_DATABASE_ID=YOUR_APPWRITE_DATABASE_ID
VITE_APPWRITE_COLLECTION_ID=YOUR_APPWRITE_COLLECTION_ID # This might be for a specific collection, verify its usage
VITE_GOOGLE_OAUTH_CLIENT_ID=YOUR_GOOGLE_OAUTH_CLIENT_ID
VITE_EMAIL_ADDRESS=YOUR_CONTACT_EMAIL
BASE_URL=http://localhost:5173
```

Start the React development server:

```bash
npm run dev

yarn dev
```
The frontend application will typically open in your browser.

## 🤝 Contributing

We welcome contributions to the RAG project! If you have suggestions, bug reports, or want to contribute code, please feel free to:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add new feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Open a Pull Request.


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.