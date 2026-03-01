"""
Local Qwen API client for Raspberry Pi deployment
"""
import os
import httpx
from typing import List, Dict, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage


class LocalQwenClient:
    """Client for local Qwen API (deployed on Raspberry Pi)"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv(
            "LOCAL_QWEN_URL",
            "http://localhost:8088/v1"
        )
        self.model_name = os.getenv("LOCAL_QWEN_MODEL", "qwen2.5")
    
    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict]:
        """Convert LangChain messages to API format"""
        api_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                api_messages.append({
                    "role": "system",
                    "content": msg.content
                })
            elif isinstance(msg, HumanMessage):
                api_messages.append({
                    "role": "user",
                    "content": msg.content
                })
            elif isinstance(msg, AIMessage):
                api_messages.append({
                    "role": "assistant",
                    "content": msg.content
                })
        return api_messages
    
    async def invoke(self, messages: List[BaseMessage], temperature: float = 0.7) -> str:
        """Invoke local Qwen API"""
        api_messages = self._convert_messages(messages)
        
        payload = {
            "model": self.model_name,
            "messages": api_messages,
            "temperature": temperature
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    raise ValueError(f"Unexpected API response: {result}")
                    
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to connect to local Qwen API: {e}")
        except Exception as e:
            raise RuntimeError(f"Error calling local Qwen API: {e}")


class LocalQwenLLM:
    """LangChain-compatible wrapper for LocalQwenClient"""
    
    def __init__(self, base_url: Optional[str] = None, temperature: float = 0.7):
        self.client = LocalQwenClient(base_url)
        self.temperature = temperature
    
    def invoke(self, messages: List[BaseMessage]) -> AIMessage:
        """Invoke model and return AIMessage"""
        import asyncio
        
        # Run async method
        if asyncio.iscoroutinefunction(self.client.invoke):
            content = asyncio.run(self.client.invoke(messages, self.temperature))
        else:
            # Fallback for sync
            import nest_asyncio
            nest_asyncio.apply()
            content = asyncio.run(self.client.invoke(messages, self.temperature))
        
        return AIMessage(content=content)


# Global instance
_local_qwen_client = None


def get_local_qwen_client(base_url: Optional[str] = None) -> LocalQwenClient:
    """Get or create local Qwen client"""
    global _local_qwen_client
    if _local_qwen_client is None:
        _local_qwen_client = LocalQwenClient(base_url)
    return _local_qwen_client


def get_local_qwen_llm(base_url: Optional[str] = None, temperature: float = 0.7) -> LocalQwenLLM:
    """Get LangChain-compatible local Qwen LLM"""
    return LocalQwenLLM(base_url, temperature)
