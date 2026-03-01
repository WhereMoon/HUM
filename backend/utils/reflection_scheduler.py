"""
Background scheduler for automatic personality reflection
"""
import asyncio
from db.personality import PersonalityDB
from agents.reflection import perform_reflection

personality_db = PersonalityDB()


async def check_and_reflect(user_id: str):
    """Check if user needs reflection and perform it"""
    conversations = personality_db.get_recent_conversations(user_id, limit=100)
    conv_count = len(conversations)
    
    # Trigger reflection every 10 conversations
    if conv_count >= 10 and conv_count % 10 == 0:
        print(f"Triggering automatic reflection for user {user_id} (conversation #{conv_count})")
        result = await perform_reflection(user_id, conversation_count=10)
        
        if result:
            print(f"Reflection completed for {user_id}: {result.get('changes', {})}")
        else:
            print(f"Reflection skipped for {user_id} (insufficient data)")
    
    return conv_count


async def periodic_reflection_check(active_users: set):
    """Periodically check all active users for reflection needs"""
    while True:
        try:
            for user_id in list(active_users):
                await check_and_reflect(user_id)
            
            # Check every 5 minutes
            await asyncio.sleep(300)
        except Exception as e:
            print(f"Error in reflection scheduler: {e}")
            await asyncio.sleep(60)  # Retry after 1 minute on error


# Global scheduler task
_reflection_task = None


def start_reflection_scheduler(active_users: set):
    """Start the background reflection scheduler"""
    global _reflection_task
    if _reflection_task is None or _reflection_task.done():
        _reflection_task = asyncio.create_task(periodic_reflection_check(active_users))
        print("Reflection scheduler started")


def stop_reflection_scheduler():
    """Stop the background reflection scheduler"""
    global _reflection_task
    if _reflection_task and not _reflection_task.done():
        _reflection_task.cancel()
        print("Reflection scheduler stopped")
