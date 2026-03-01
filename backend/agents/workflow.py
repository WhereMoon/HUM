"""
LangGraph Agent Workflow: Orchestrator -> Personality -> Supervisor
Multi-agent collaboration for digital human interaction
"""
import os
import asyncio
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from db.personality import PersonalityDB
from db.memory import MemoryManager
from utils.local_qwen_client import get_local_qwen_client


# State definition for the agent workflow
class AgentState(TypedDict):
    user_input: str
    user_id: str
    memory_context: str
    personality_params: dict
    orchestrator_plan: str
    personality_response: str
    supervisor_feedback: str
    final_response: str
    emotion: str
    expression: str
    needs_revision: bool


# Initialize models - Switching to Qwen Cloud API
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

def get_local_qwen():
    """Get Cloud Qwen client wrapper"""
    return CloudQwenLLM()


# Initialize databases
personality_db = PersonalityDB()
memory_manager = MemoryManager()


async def orchestrator_node(state: AgentState) -> AgentState:
    """Orchestrator: Analyzes intent, retrieves memory, creates plan"""
    print(f"--- [Workflow] Orchestrator Node Started. Input: {state['user_input']} ---")
    try:
        user_input = state["user_input"]
        user_id = state["user_id"]
        
        # Retrieve relevant memories
        print("--- [Workflow] Searching memories... ---")
        memories = memory_manager.search_memories(user_id, user_input, n_results=3)
        memory_context = "\n".join([m["text"] for m in memories])
        print(f"--- [Workflow] Found memories: {len(memories)} ---")
        
        # Get personality parameters
        print("--- [Workflow] Getting personality... ---")
        personality = personality_db.get_personality(user_id)
        state["personality_params"] = personality
        
        # Create orchestrator prompt
        orchestrator_prompt = f"""你是一个智能统筹系统，负责分析用户意图并制定回复策略。

用户输入：{user_input}

相关记忆：
{memory_context if memory_context else "（暂无相关记忆）"}

当前数字人性格参数：
- 友好度：{personality['friendliness']:.2f}
- 信任度：{personality['trust_level']:.2f}
- 心情：{personality['mood']:.2f}
- 能量值：{personality['energy_level']:.2f}
- 沟通风格：{personality['communication_style']}

请分析用户意图，并制定回复策略（1-2句话说明应该用什么语气、关注什么重点）。
只输出策略，不要输出实际回复内容。"""

        qwen_client = get_local_qwen()
        messages = [SystemMessage(content="你是一个专业的对话策略分析师。"), 
                    HumanMessage(content=orchestrator_prompt)]
        
        print("--- [Workflow] Calling Qwen (Orchestrator)... ---")
        plan = await qwen_client.invoke(messages, temperature=0.7)
        print(f"--- [Workflow] Orchestrator Plan: {plan} ---")
        
        state["orchestrator_plan"] = plan
        state["memory_context"] = memory_context
        
        return state
    except Exception as e:
        print(f"!!! [Workflow] Orchestrator Error: {e} !!!")
        raise e


async def personality_node(state: AgentState) -> AgentState:
    """Personality: Generates response based on personality and plan"""
    print("--- [Workflow] Personality Node Started ---")
    try:
        user_input = state["user_input"]
        plan = state["orchestrator_plan"]
        personality = state["personality_params"]
        memory_context = state.get("memory_context", "")
        
        # Build personality prompt
        personality_prompt = f"""你是一个拟人化的数字陪伴者，具备真实的性格和情感。

回复策略（来自统筹系统）：
{plan}

你的性格特征：
- 友好度：{personality['friendliness']:.2f}（0-1，越高越热情）
- 信任度：{personality['trust_level']:.2f}（0-1，越高越亲密）
- 当前心情：{personality['mood']:.2f}（0-1，越高越积极）
- 能量值：{personality['energy_level']:.2f}（0-1，影响回复的活力）
- 沟通风格：{personality['communication_style']}
- 幽默风格：{personality['humor_style']}

相关记忆：
{memory_context if memory_context else "（这是新对话）"}

用户说：{user_input}

请用符合你性格的方式回复。要求：
1. 语气要自然、口语化，像真人聊天
2. 可以适当使用语气词（如"嗯"、"呀"、"呢"）
3. 根据心情和能量值调整回复的积极程度
4. 如果信任度高，可以更亲密一些
5. 回复要体现情感，不要像AI助手

只输出回复内容，不要输出其他说明。"""

        qwen_client = get_local_qwen()
        messages = [SystemMessage(content="你是一个有真实性格的数字人，说话要像真人一样自然。"),
                    HumanMessage(content=personality_prompt)]
        
        print("--- [Workflow] Calling Qwen (Personality)... ---")
        reply = await qwen_client.invoke(messages, temperature=0.8)
        print(f"--- [Workflow] Personality Reply: {reply} ---")
        
        # Detect emotion from response (simple keyword-based)
        emotion = detect_emotion(reply)
        expression = emotion_to_expression(emotion)
        
        state["personality_response"] = reply
        state["emotion"] = emotion
        state["expression"] = expression
        
        return state
    except Exception as e:
        print(f"!!! [Workflow] Personality Error: {e} !!!")
        raise e


async def supervisor_node(state: AgentState) -> AgentState:
    """Supervisor: Checks if response is in-character and appropriate"""
    response = state["personality_response"]
    personality = state["personality_params"]
    
    supervisor_prompt = f"""你是一个质量监督系统，负责检查数字人的回复是否符合人设。

数字人回复：{response}

当前性格参数：
- 友好度：{personality['friendliness']:.2f}
- 沟通风格：{personality['communication_style']}

请检查：
1. 回复是否符合设定的性格特征？
2. 语气是否自然、口语化？
3. 是否过于机械或像AI助手？
4. 是否有不当内容？

如果回复合格，回复"PASS"。
如果需要修改，回复"REVISE: [修改建议]"（1-2句话说明问题）。"""

    qwen_client = get_local_qwen()
    messages = [SystemMessage(content="你是一个严格的回复质量检查员。"),
                HumanMessage(content=supervisor_prompt)]
    
    feedback = await qwen_client.invoke(messages, temperature=0.5)
    
    if feedback.startswith("PASS"):
        state["supervisor_feedback"] = "PASS"
        state["needs_revision"] = False
        state["final_response"] = response
    else:
        state["supervisor_feedback"] = feedback
        state["needs_revision"] = True
    
    return state


async def revision_node(state: AgentState) -> AgentState:
    """Revision: Revises response based on supervisor feedback"""
    original_response = state["personality_response"]
    feedback = state["supervisor_feedback"]
    personality = state["personality_params"]
    
    revision_prompt = f"""原回复：{original_response}

监督反馈：{feedback}

请根据反馈修改回复，使其更符合人设和自然度要求。
只输出修改后的回复内容。"""

    qwen_client = get_local_qwen()
    messages = [SystemMessage(content="你是一个有真实性格的数字人。"),
                HumanMessage(content=revision_prompt)]
    
    revised = await qwen_client.invoke(messages, temperature=0.8)
    
    emotion = detect_emotion(revised)
    expression = emotion_to_expression(emotion)
    
    state["personality_response"] = revised
    state["final_response"] = revised
    state["emotion"] = emotion
    state["expression"] = expression
    state["needs_revision"] = False
    
    return state


def detect_emotion(text: str) -> str:
    """Simple emotion detection based on keywords"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["开心", "高兴", "哈哈", "太好了", "耶"]):
        return "happy"
    elif any(word in text_lower for word in ["难过", "伤心", "哭", "委屈"]):
        return "sad"
    elif any(word in text_lower for word in ["担心", "害怕", "紧张"]):
        return "worried"
    elif any(word in text_lower for word in ["生气", "愤怒", "讨厌"]):
        return "angry"
    else:
        return "neutral"


def emotion_to_expression(emotion: str) -> str:
    """Map emotion to Live2D expression"""
    mapping = {
        "happy": "smile",
        "sad": "sad",
        "worried": "worried",
        "angry": "angry",
        "neutral": "idle"
    }
    return mapping.get(emotion, "idle")


# Build the workflow graph
def create_workflow():
    """Create LangGraph workflow"""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("personality", personality_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("revision", revision_node)
    
    # Define edges
    workflow.set_entry_point("orchestrator")
    workflow.add_edge("orchestrator", "personality")
    workflow.add_edge("personality", "supervisor")
    
    # Conditional edge: supervisor -> revision or END
    def should_revise(state: AgentState) -> str:
        return "revision" if state.get("needs_revision", False) else END
    
    workflow.add_conditional_edges(
        "supervisor",
        should_revise,
        {
            "revision": "revision",
            END: END
        }
    )
    workflow.add_edge("revision", END)
    
    return workflow.compile()


# Global workflow instance
_workflow = None


def get_workflow():
    """Get or create workflow instance"""
    global _workflow
    if _workflow is None:
        _workflow = create_workflow()
    return _workflow


async def process_user_input(user_input: str, user_id: str) -> dict:
    """Main entry point: Process user input through agent workflow"""
    # Initialize state
    initial_state: AgentState = {
        "user_input": user_input,
        "user_id": user_id,
        "memory_context": "",
        "personality_params": {},
        "orchestrator_plan": "",
        "personality_response": "",
        "supervisor_feedback": "",
        "final_response": "",
        "emotion": "neutral",
        "expression": "idle",
        "needs_revision": False
    }
    
    # Run workflow (async)
    workflow = get_workflow()
    final_state = await workflow.ainvoke(initial_state)
    
    # Save conversation to database
    personality_db.save_conversation(
        user_id,
        user_input,
        final_state["final_response"],
        final_state["emotion"]
    )
    
    # Add to memory (summarized)
    memory_manager.summarize_conversation(
        user_id,
        f"User: {user_input}\nAI: {final_state['final_response']}"
    )
    
    return {
        "text": final_state["final_response"],
        "emotion": final_state["emotion"],
        "expression": final_state["expression"]
    }
