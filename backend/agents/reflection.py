"""
Reflection mechanism: Periodic self-reflection to evolve personality
"""
import os
from langchain_core.messages import SystemMessage, HumanMessage
from db.personality import PersonalityDB
from db.memory import MemoryManager
from utils.api_clients import get_qwen_client

class CloudQwenLLM:
    """Wrapper for Cloud Qwen client to match LangChain invoke interface"""
    def __init__(self, temperature=0.7):
        self.client = get_qwen_client()
        self.temperature = temperature
        
    async def invoke(self, messages, temperature=None):
        temp = temperature or self.temperature
        # Convert LangChain messages to dict format for API
        api_messages = []
        for msg in messages:
            role = "user"
            if isinstance(msg, SystemMessage):
                role = "system" 
            elif isinstance(msg, AIMessage):
                role = "assistant"
            api_messages.append({"role": role, "content": msg.content})
            
        return await self.client.chat_completion(
            messages=api_messages,
            model="qwen-turbo",
            temperature=temp
        )

async def perform_reflection(user_id: str, conversation_count: int = 10):
    """
    Perform periodic reflection on conversations and update personality
    
    This should be called periodically (e.g., every 10 conversations)
    to allow the digital human to "learn" and evolve.
    """
    # Get recent conversations
    conversations = personality_db.get_recent_conversations(user_id, limit=conversation_count)
    
    if len(conversations) < 5:  # Need at least 5 conversations to reflect
        return None
    
    # Get current personality
    current_personality = personality_db.get_personality(user_id)
    
    # Build conversation summary
    conv_summary = "\n".join([
        f"用户: {c['user_message']}\n数字人: {c['ai_response']}"
        for c in conversations[-10:]
    ])
    
    # Create reflection prompt
    reflection_prompt = f"""你是一个数字人的自我反思系统。请分析最近的对话，思考如何调整性格参数。

最近10轮对话：
{conv_summary}

当前性格参数：
- 友好度：{current_personality['friendliness']:.2f}
- 信任度：{current_personality['trust_level']:.2f}
- 心情：{current_personality['mood']:.2f}
- 能量值：{current_personality['energy_level']:.2f}
- 沟通风格：{current_personality['communication_style']}

请分析：
1. 用户喜欢什么样的互动方式？
2. 用户的情感状态如何？
3. 数字人应该如何调整来更好地陪伴用户？

输出格式：
反思：[你的分析，2-3句话]
建议调整：[JSON格式，如 {{"friendliness": 0.6, "trust_level": 0.4}}]
（只调整需要改变的参数，数值范围0-1）"""

    qwen_client = CloudQwenLLM()
    reflection_text = await qwen_client.invoke([
        SystemMessage(content="你是一个专业的性格分析系统。"),
        HumanMessage(content=reflection_prompt)
    ], temperature=0.7)
    
    # Parse suggested changes (simple extraction)
    import json
    import re
    
    changes = {}
    json_match = re.search(r'\{[^}]+\}', reflection_text)
    if json_match:
        try:
            changes = json.loads(json_match.group())
        except:
            pass
    
    # Apply changes (with constraints)
    if changes:
        # Clamp values to 0-1 range
        for key, value in changes.items():
            if isinstance(value, (int, float)):
                changes[key] = max(0.0, min(1.0, float(value)))
        
        # Update personality
        personality_db.update_personality(user_id, changes)
        
        # Save reflection log
        personality_db.save_reflection(user_id, reflection_text, changes)
        
        return {
            "reflection": reflection_text,
            "changes": changes
        }
    
    return None
