from appwrite.client import Client
from appwrite.services.database import Databases
import os
from dotenv import load_dotenv
from appwrite.query import Query

load_dotenv()

class dbService:
    def __init__(self, session, jwt):
        self.client = Client()
        self.client.set_endpoint('https://Frankfurt.cloud.appwrite.io/v1')
        self.client.set_session(session)
        self.client.set_project(os.getenv("APPWRITE_PROJECT_ID"))
        self.client.set_key(os.getenv("APPWRITE_API_KEY"))
        self.client.set_jwt(jwt)
        self.databases = Databases(self.client)

    def add_messages(self, convoId, sendertype, content, timestamp):
        result = self.databases.create_document(
            database_id = os.getenv("APPWRITE_DB_ID"),
            collection_id = os.getenv("APPWRITE_MESSAGES_COLL_ID"),
            conversationId = convoId,
            sendertype = sendertype,
            content = content,
            timestamp = timestamp
        )

    def create_convo(self, userId, title, lastMessageAt):
        result  = self.databases.create_document(
            database_id = os.getenv("APPWRITE_DB_ID"),
            collection_id = os.getenv("APPWRITE_CONVERSATIONS_COLL_ID"),
            userId = userId,
            title = title,
            lastMessageAt = lastMessageAt
        )

    def get_convo(self, userId):
        result = self.databases.list_documents(
            database_id = os.getenv("APPWRITE_DB_ID"),
            collection_id = os.getenv("APPWRITE_CONVERSATIONS_COLL_ID"),
            queries = [ Query.equal('userId', userId)]
        )
        return result

    def get_messages(self, userId):
        return self.databases.list_documents(
            database_id = os.getenv("APPWRITE_DB_ID"),
            collection_id = os.getenv("APPWRITE_MESSAGES_COLL_ID"),
            queries = [Query.equal('userId', userId)]
        )
    
    