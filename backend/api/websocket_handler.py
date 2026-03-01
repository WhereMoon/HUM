"""
WebSocket handler for real-time audio and text communication
"""
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
import json
import asyncio
from typing import Dict

from agents.workflow import process_user_input
from utils.audio_processor import AudioProcessor
from utils.api_clients import get_whisper_client, get_tts_client
from utils.reflection_scheduler import check_and_reflect

router = APIRouter()

# Store active connections
active_connections: Dict[str, WebSocket] = {}


class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"Client {client_id} connected")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        print(f"Client {client_id} disconnected")
    
    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
    
    async def send_audio_chunk(self, audio_data: bytes, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_bytes(audio_data)


manager = ConnectionManager()
audio_processor = AudioProcessor()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """Main WebSocket endpoint for real-time interaction"""
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message (can be audio bytes or JSON text)
            data = await websocket.receive()
            
            if "text" in data:
                # Text message
                message = json.loads(data["text"])
                await handle_text_message(message, client_id)
            
            elif "bytes" in data:
                # Audio data
                await handle_audio_message(data["bytes"], client_id)
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket error for {client_id}: {e}")
        manager.disconnect(client_id)


async def handle_text_message(message: dict, client_id: str):
    """Handle text-based messages from client"""
    print(f"--- [WS] Received text message from {client_id}: {message} ---")
    msg_type = message.get("type")
    
    if msg_type == "text_input":
        # Direct text input
        user_text = message.get("text", "")
        print(f"--- [WS] Processing text input: {user_text} ---")
        await process_and_respond(user_text, client_id)
    
    elif msg_type == "audio_transcript":
        # Audio has been transcribed on client side
        transcript = message.get("transcript", "")
        print(f"--- [WS] Processing transcript: {transcript} ---")
        await process_and_respond(transcript, client_id)
    else:
        print(f"--- [WS] Unknown message type: {msg_type} ---")


async def handle_audio_message(audio_bytes: bytes, client_id: str):
    """Handle audio stream from client"""
    print(f"--- [WS] Received audio bytes from {client_id} (len: {len(audio_bytes)}) ---")
    try:
        # Use Whisper API to transcribe
        whisper = get_whisper_client()
        transcript = await whisper.transcribe_audio_bytes(audio_bytes)
        print(f"--- [WS] Audio transcribed: {transcript} ---")
        
        # Process the transcript
        await process_and_respond(transcript, client_id)
    except Exception as e:
        print(f"Error processing audio: {e}")
        await manager.send_personal_message({
            "type": "error",
            "message": f"Audio processing failed: {str(e)}"
        }, client_id)


async def process_and_respond(user_input: str, client_id: str):
    """Process user input through agent workflow and send response"""
    print(f"--- [WS] process_and_respond called with input: {user_input} ---")
    try:
        # Send thinking status
        await manager.send_personal_message({
            "type": "status",
            "status": "thinking"
        }, client_id)
        
        # Process through agent workflow
        print("--- [WS] Invoking process_user_input... ---")
        response = await process_user_input(user_input, client_id)
        print(f"--- [WS] process_user_input returned: {response} ---")
        
        # Send text response
        await manager.send_personal_message({
            "type": "text_response",
            "text": response["text"],
            "emotion": response.get("emotion", "neutral"),
            "expression": response.get("expression", "idle")
        }, client_id)
        
        # Generate and stream audio via TTS API
        tts_client = get_tts_client()
        
        # Send audio start signal
        await manager.send_personal_message({
            "type": "audio_start",
            "text": response["text"]
        }, client_id)
        
        # Stream audio chunks
        print("--- [WS] Starting TTS stream... ---")
        async for audio_chunk in tts_client.synthesize_stream(
            response["text"],
            voice="zhiyan"  # 阿里云百炼语音：zhiyan(知燕), zhiqi(知琪), zhitian(知甜) 等
        ):
            await manager.send_audio_chunk(audio_chunk, client_id)
        print("--- [WS] TTS stream finished ---")
        
        # Send audio end signal
        await manager.send_personal_message({
            "type": "audio_end"
        }, client_id)
        
        # Check if reflection is needed (async, non-blocking)
        asyncio.create_task(check_and_reflect(client_id))
        
    except Exception as e:
        print(f"!!! [WS] Error processing input: {e} !!!")
        import traceback
        traceback.print_exc()
        await manager.send_personal_message({
            "type": "error",
            "message": str(e)
        }, client_id)
