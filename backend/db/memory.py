"""
Long-term memory management using ChromaDB
"""
import os
import chromadb
from chromadb.config import Settings
import uuid
from datetime import datetime
from typing import List, Dict, Optional

class MemoryManager:
    """Manages long-term memory using vector database"""
    
    def __init__(self, persist_directory: str = "./data/chroma_db"):
        self.persist_directory = persist_directory
        
        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client with telemetry disabled
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 显式禁用 telemetry，防止 chromadb 内部即使配置了 Settings 仍尝试发送
        try:
            from chromadb.telemetry.product import ProductTelemetryClient
            # Monkey patch capture method to do nothing
            ProductTelemetryClient.capture = lambda self, *args, **kwargs: None
        except ImportError:
            pass
        
        # Create or get collections
        self.memory_collection = self.client.get_or_create_collection(
            name="user_memories",
            metadata={"hnsw:space": "cosine"}
        )
        
        print(f"ChromaDB initialized at {persist_directory}")

    def add_memory(self, user_id: str, text: str, metadata: Optional[Dict] = None):
        """Add a new memory entry"""
        if metadata is None:
            metadata = {}
            
        metadata.update({
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "type": "raw_interaction"
        })
        
        self.memory_collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[str(uuid.uuid4())]
        )

    def summarize_conversation(self, user_id: str, conversation_text: str):
        """Add a conversation summary to memory"""
        self.add_memory(
            user_id, 
            conversation_text, 
            metadata={"type": "conversation_summary"}
        )

    def search_memories(self, user_id: str, query: str, n_results: int = 5) -> List[Dict]:
        """Search for relevant memories"""
        results = self.memory_collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"user_id": user_id}
        )
        
        memories = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                memories.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results["distances"] else None
                })
                
        return memories

    def clear_memories(self, user_id: str):
        """Delete all memories for a user"""
        self.memory_collection.delete(
            where={"user_id": user_id}
        )
