"""
Initialize databases (SQLite and ChromaDB)
"""
import os
from pathlib import Path
import chromadb
from db.personality import init_personality_db


def init_databases():
    """Initialize all databases"""
    # Create data directory
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)
    
    # Initialize SQLite personality database
    init_personality_db()
    
    # Initialize ChromaDB for vector memory
    chroma_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
    # Match settings with memory.py to avoid "instance already exists with different settings" error
    chroma_client = chromadb.PersistentClient(
        path=chroma_path,
        settings=chromadb.config.Settings(anonymized_telemetry=False)
    )
    
    # Create or get collection for conversation memory
    memory_collection = chroma_client.get_or_create_collection(
        name="conversation_memory",
        metadata={"hnsw:space": "cosine"}
    )
    
    print(f"ChromaDB initialized at {chroma_path}")
    print("All databases initialized successfully")
