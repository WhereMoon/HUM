"""
API endpoints for personality reflection and evolution
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agents.reflection import perform_reflection
from db.personality import PersonalityDB

router = APIRouter()
personality_db = PersonalityDB()


class ReflectionRequest(BaseModel):
    user_id: str
    conversation_count: int = 10


class ReflectionResponse(BaseModel):
    success: bool
    reflection: str = None
    changes: dict = None
    message: str


@router.post("/reflection/trigger", response_model=ReflectionResponse)
async def trigger_reflection(request: ReflectionRequest):
    """Manually trigger personality reflection for a user"""
    try:
        result = await perform_reflection(
            request.user_id,
            request.conversation_count
        )
        
        if result:
            return ReflectionResponse(
                success=True,
                reflection=result.get("reflection", ""),
                changes=result.get("changes", {}),
                message="反思完成，性格参数已更新"
            )
        else:
            return ReflectionResponse(
                success=False,
                message="对话数量不足，无法进行反思（至少需要5轮对话）"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reflection/status/{user_id}")
async def get_reflection_status(user_id: str):
    """Get reflection history for a user"""
    try:
        # Get recent conversations count
        conversations = personality_db.get_recent_conversations(user_id, limit=100)
        conv_count = len(conversations)
        
        # Get current personality
        personality = personality_db.get_personality(user_id)
        
        # Check if ready for reflection (every 10 conversations)
        ready_for_reflection = conv_count >= 10 and conv_count % 10 == 0
        
        return {
            "user_id": user_id,
            "conversation_count": conv_count,
            "ready_for_reflection": ready_for_reflection,
            "current_personality": personality,
            "next_reflection_at": ((conv_count // 10) + 1) * 10 if not ready_for_reflection else conv_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
