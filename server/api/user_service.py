from appwrite.services.databases import Databases
from appwrite.query import Query
from appwrite.id import ID
from appwrite.permission import Permission
from appwrite.role import Role
from datetime import date
import logging

logger = logging.getLogger(__name__)

MAX_PROMPTS_PER_DAY = 10

def get_user_prompt_limit(databases, db_id, user_limits_collection_id, user_id):
    """Get user's prompt limit"""
    try:
        user_limit_docs = databases.list_documents(
            db_id,
            user_limits_collection_id,
            queries=[Query.equal('userId', user_id)]
        )
        
        user_limit_doc = user_limit_docs['documents'][0] if user_limit_docs['documents'] else None
        today_str = date.today().isoformat()
        
        if user_limit_doc:
            last_reset_date = user_limit_doc.get('lastResetDate')
            prompt_count = user_limit_doc.get('promptCount', 0)
            
            if last_reset_date != today_str:
                # New day, reset count
                databases.update_document(
                    db_id,
                    user_limits_collection_id,
                    user_limit_doc['$id'],
                    {'promptCount': 1, 'lastResetDate': today_str}
                )
                prompts_remaining = MAX_PROMPTS_PER_DAY - 1
            else:
                # Same day
                if prompt_count >= MAX_PROMPTS_PER_DAY:
                    return 0, MAX_PROMPTS_PER_DAY
                else:
                    databases.update_document(
                        db_id,
                        user_limits_collection_id,
                        user_limit_doc['$id'],
                        {'promptCount': prompt_count + 1}
                    )
                    prompts_remaining = MAX_PROMPTS_PER_DAY - (prompt_count + 1)
        else:
            # Create new user limit document
            databases.create_document(
                db_id,
                user_limits_collection_id,
                ID.unique(),
                {
                    'userId': user_id,
                    'promptCount': 1,
                    'lastResetDate': today_str
                },
                permissions=[
                    Permission.read(Role.user(user_id)),
                    Permission.update(Role.user(user_id)),
                    Permission.delete(Role.user(user_id)),
                ]
            )
            prompts_remaining = MAX_PROMPTS_PER_DAY - 1
            
        return prompts_remaining, MAX_PROMPTS_PER_DAY
    except Exception as e:
        logger.error(f"Error managing user prompt limit: {e}")
        return MAX_PROMPTS_PER_DAY, MAX_PROMPTS_PER_DAY

def create_conversation(databases, db_id, conv_collection_id, user_id, title):
    """Create a new conversation"""
    from datetime import datetime
    
    current_timestamp = datetime.now().isoformat()
    
    doc = databases.create_document(
        db_id,
        conv_collection_id,
        ID.unique(),
        {
            'title': title[:50],
            'userId': user_id,
            'lastMessageAt': current_timestamp
        },
        permissions=[
            Permission.read(Role.user(user_id)),
            Permission.update(Role.user(user_id)),
            Permission.delete(Role.user(user_id)),
        ]
    )
    
    return doc['$id']

def update_conversation_timestamp(databases, db_id, conv_collection_id, conversation_id):
    """Update conversation last message timestamp"""
    from datetime import datetime
    
    current_timestamp = datetime.now().isoformat()
    
    databases.update_document(
        db_id,
        conv_collection_id,
        conversation_id,
        {'lastMessageAt': current_timestamp}
    )