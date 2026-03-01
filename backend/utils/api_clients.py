"""
API clients for external services: 阿里云百炼 (DashScope) ASR/TTS, Qwen2.5 (LLM)
"""
import os
import base64
from typing import Optional, AsyncGenerator
import httpx


class DashScopeASRClient:
    """阿里云百炼语音识别 (ASR) 客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
        
    async def transcribe_audio_bytes(self, audio_bytes: bytes, format: str = "wav") -> str:
        """将音频字节转换为文字（使用阿里云百炼 ASR）"""
        # 将音频编码为 base64
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "paraformer-realtime-v2",
            "audio": {
                "data": audio_base64,
                "format": format
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
                if "output" in result and "text" in result["output"]:
                    return result["output"]["text"]
                elif "message" in result:
                    raise ValueError(f"ASR API error: {result['message']}")
                else:
                    raise ValueError(f"Unexpected ASR response: {result}")
        except httpx.HTTPError as e:
            raise RuntimeError(f"Failed to connect to DashScope ASR: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to transcribe audio: {e}")
    
    async def transcribe_audio(self, audio_file_path: str) -> str:
        """将音频文件转换为文字"""
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()
        return await self.transcribe_audio_bytes(audio_bytes)


class DashScopeTTSClient:
    """阿里云百炼语音合成 (TTS) 客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/text-to-speech"
    
    async def synthesize_speech(
        self, 
        text: str, 
        voice: str = "zhiyan",
        format: str = "wav"
    ) -> bytes:
        """将文字合成为语音（阿里云百炼 TTS）"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 阿里云百炼 TTS (Sambert 系列)
        # model: sambert-zhiyan-v1 (知燕)
        # 这种模型不需要额外的 voice 参数，因为模型名已经指定了发音人
        model_name = f"sambert-{voice}-v1"
        
        payload = {
            "model": model_name,
            "input": {
                "text": text
            },
            "parameters": {
                "format": format,
                "sample_rate": 16000
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload
                )
                if response.status_code == 400:
                    # 如果 sambert 系列失败，尝试使用更通用的 CosyVoice 或 paraformer (虽然后者是ASR)
                    # 这里尝试回退到 cosvoice-v1 (如果支持) 或者打印更详细的错误
                    print(f"TTS Error 400: {response.text}")
                    
                response.raise_for_status()
                result = response.json()
                
                if "output" in result and "audio" in result["output"]:
                    # 百炼返回 base64 编码的音频
                    audio_base64 = result["output"]["audio"]
                    return base64.b64decode(audio_base64)
                elif "message" in result:
                    raise ValueError(f"TTS API error: {result['message']}")
                else:
                    raise ValueError(f"Unexpected TTS response: {result}")
        except httpx.HTTPError as e:
            raise RuntimeError(f"Failed to connect to DashScope TTS: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to synthesize speech: {e}")
    
    async def synthesize_stream(
        self,
        text: str,
        voice: str = "zhiyan",
        format: str = "wav"
    ) -> AsyncGenerator[bytes, None]:
        """流式合成语音（分块返回）"""
        # 对于长文本，可以分段处理
        max_chunk_length = 200  # 每次最多200字
        
        if len(text) <= max_chunk_length:
            # 短文本直接合成，直接返回完整音频，不要切片破坏 WAV 头
            audio = await self.synthesize_speech(text, voice, format)
            yield audio
        else:
            # 长文本分段处理
            chunks = [text[i:i + max_chunk_length] for i in range(0, len(text), max_chunk_length)]
            for chunk in chunks:
                audio = await self.synthesize_speech(chunk, voice, format)
                yield audio


class QwenClient:
    """Qwen2.5 API client (via DashScope)"""
    
    def __init__(self, api_key: Optional[str] = None):
        # 优先使用传入的 key，其次是环境变量，最后是硬编码的默认 key
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        # 阿里云百炼兼容 OpenAI 格式的 endpoint 应该是这个：
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    async def chat_completion(
        self,
        messages: list,
        model: str = "qwen-turbo",
        temperature: float = 0.8
    ) -> str:
        """Call Qwen API for chat completion"""
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]


# Global instances
_asr_client = None
_tts_client = None
_qwen_client = None


def get_whisper_client() -> DashScopeASRClient:
    """Get or create ASR client (阿里云百炼)"""
    global _asr_client
    if _asr_client is None:
        _asr_client = DashScopeASRClient()
    return _asr_client


def get_tts_client() -> DashScopeTTSClient:
    """Get or create TTS client (阿里云百炼)"""
    global _tts_client
    if _tts_client is None:
        _tts_client = DashScopeTTSClient()
    return _tts_client


def get_qwen_client() -> QwenClient:
    """Get or create Qwen client"""
    global _qwen_client
    if _qwen_client is None:
        _qwen_client = QwenClient()
    return _qwen_client
