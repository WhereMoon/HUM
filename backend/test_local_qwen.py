"""
Test script for local Qwen API connection
"""
import asyncio
import os
from dotenv import load_dotenv
from utils.local_qwen_client import get_local_qwen_client
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()


async def test_qwen_connection():
    """Test connection to local Qwen API"""
    print("Testing local Qwen API connection...")
    print(f"API URL: {os.getenv('LOCAL_QWEN_URL', 'http://localhost:8088/v1')}")
    print(f"Model: {os.getenv('LOCAL_QWEN_MODEL', 'qwen2.5')}")
    print("-" * 50)
    
    try:
        client = get_local_qwen_client()
        
        # Simple test
        messages = [
            SystemMessage(content="你是一个友好的助手。"),
            HumanMessage(content="你好，简单介绍下你自己")
        ]
        
        print("Sending test message...")
        response = await client.invoke(messages, temperature=0.7)
        print(f"\nResponse: {response}")
        print("\n✅ Connection successful!")
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\n请检查：")
        print("1. 树莓派上的 Qwen API 服务是否正在运行")
        print("2. IP 地址和端口是否正确")
        print("3. 网络连接是否正常")


if __name__ == "__main__":
    asyncio.run(test_qwen_connection())
