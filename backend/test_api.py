import os
import asyncio
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import HumanMessage, SystemMessage

# 使用环境变量 DASHSCOPE_API_KEY，请在本机 .env 或 shell 中配置
if not os.getenv("DASHSCOPE_API_KEY"):
    print("请设置环境变量 DASHSCOPE_API_KEY 后再运行测试")
    exit(1)


async def test_qwen():
    print("Testing Qwen Cloud API Connection...")
    
    # 使用与项目中相同的配置
    # 注意：LangChain 内部会自动处理 base_url，如果你在 api_clients.py 里改了 base_url，
    # 这里我们直接测试 LangChain 是否能通，或者手动指定 base_url
    
    try:
        # 方法 1: 直接使用 LangChain (这是目前 workflow.py 中使用的方式)
        llm = ChatTongyi(
            model="qwen-turbo", 
            temperature=0.7,
            # 如果需要指定 base_url，可以在这里加，但通常 LangChain 会自动处理
            # base_url="https://dashscope.aliyuncs.com/compatible-mode/v1" 
        )
        
        messages = [
            SystemMessage(content="你是一个测试助手。"),
            HumanMessage(content="你好，请回复'测试成功'四个字。")
        ]
        
        print("Sending request to Qwen...")
        response = await llm.ainvoke(messages)
        print(f"Response received: {response.content}")
        
    except Exception as e:
        print(f"Error testing LangChain Qwen: {e}")

    print("-" * 50)
    
    print("Testing HTTP Client (Manual Request)...")
    try:
        import httpx
        
        # 测试我们在 api_clients.py 中设置的 URL
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "qwen-turbo",
            "messages": [{"role": "user", "content": "你好"}],
            "temperature": 0.7
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                print(f"Response: {resp.json()['choices'][0]['message']['content']}")
            else:
                print(f"Error Response: {resp.text}")
                
    except Exception as e:
        print(f"Error testing HTTP Client: {e}")

if __name__ == "__main__":
    asyncio.run(test_qwen())
