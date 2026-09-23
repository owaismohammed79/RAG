from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

MAX_PROMPTS_PER_DAY = 10

def get_user_prompt_limit(supabase, user_id, increment=False):
    """Get (and optionally increment) user's prompt limit"""
    try:
        res = supabase.table("user_limits").select("*").eq("user_id", user_id).execute()
        user_limits = res.data or []
        user_limit_doc = user_limits[0] if user_limits else None
        
        today_str = date.today().isoformat()
        
        if user_limit_doc:
            last_reset_date = user_limit_doc.get("last_reset_date")
            prompt_count = user_limit_doc.get("prompt_count", 0)
            
            if last_reset_date != today_str:
                if increment:
                    supabase.table("user_limits").update({
                        "prompt_count": 1,
                        "last_reset_date": today_str
                    }).eq("id", user_limit_doc["id"]).execute()
                    prompts_remaining = MAX_PROMPTS_PER_DAY - 1
                else:
                    prompts_remaining = MAX_PROMPTS_PER_DAY
            else:
                if prompt_count >= MAX_PROMPTS_PER_DAY:
                    return 0, MAX_PROMPTS_PER_DAY
                
                if increment:
                    supabase.table("user_limits").update({
                        "prompt_count": prompt_count + 1
                    }).eq("id", user_limit_doc["id"]).execute()
                    prompts_remaining = MAX_PROMPTS_PER_DAY - (prompt_count + 1)
                else:
                    prompts_remaining = MAX_PROMPTS_PER_DAY - prompt_count
        else:
            if increment:
                supabase.table("user_limits").insert({
                    "user_id": user_id,
                    "prompt_count": 1,
                    "last_reset_date": today_str
                }).execute()
                prompts_remaining = MAX_PROMPTS_PER_DAY - 1
            else:
                prompts_remaining = MAX_PROMPTS_PER_DAY
                
        return prompts_remaining, MAX_PROMPTS_PER_DAY
    except Exception as e:
        logger.error(f"Error managing user prompt limit: {e}")
        return MAX_PROMPTS_PER_DAY, MAX_PROMPTS_PER_DAY

def create_conversation(supabase, user_id, title):
    """Create a new conversation"""
    current_timestamp = datetime.now().isoformat()
    
    res = supabase.table("conversations").insert({
        "title": title[:50],
        "user_id": user_id,
        "last_message_at": current_timestamp
    }).execute()
    
    return res.data[0]["id"]

def update_conversation_timestamp(supabase, conversation_id):
    """Update conversation timestamp"""
    current_timestamp = datetime.now().isoformat()
    
    supabase.table("conversations").update({
        "last_message_at": current_timestamp
    }).eq("id", conversation_id).execute()