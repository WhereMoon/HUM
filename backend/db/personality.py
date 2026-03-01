"""
Personality database schema and operations
Stores dynamic personality parameters for evolving personality system
"""
import sqlite3
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


DB_PATH = Path("./data/personality.db")


def init_personality_db():
    """Initialize personality database with schema"""
    DB_PATH.parent.mkdir(exist_ok=True, parents=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Personality parameters table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS personality_params (
            user_id TEXT PRIMARY KEY,
            friendliness REAL DEFAULT 0.5,
            trust_level REAL DEFAULT 0.3,
            mood REAL DEFAULT 0.5,
            energy_level REAL DEFAULT 0.5,
            humor_style TEXT DEFAULT 'gentle',
            communication_style TEXT DEFAULT 'warm',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Conversation history table (for reflection mechanism)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            user_message TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            emotion_detected TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES personality_params(user_id)
        )
    """)
    
    # Reflection logs table (stores AI's self-reflection results)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reflection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            reflection_text TEXT NOT NULL,
            personality_changes TEXT,  -- JSON string of changes
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES personality_params(user_id)
        )
    """)
    
    # Create indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversation_user_timestamp 
        ON conversation_history(user_id, timestamp DESC)
    """)
    
    conn.commit()
    conn.close()
    print(f"Personality database initialized at {DB_PATH}")


class PersonalityDB:
    """Database operations for personality management"""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
    
    def get_personality(self, user_id: str) -> Dict:
        """Get current personality parameters for a user"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM personality_params WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        
        # Create default personality if doesn't exist
        return self.create_default_personality(user_id)
    
    def create_default_personality(self, user_id: str) -> Dict:
        """Create default personality for new user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO personality_params 
            (user_id, friendliness, trust_level, mood, energy_level, 
             humor_style, communication_style)
            VALUES (?, 0.5, 0.3, 0.5, 0.5, 'gentle', 'warm')
        """, (user_id,))
        
        conn.commit()
        conn.close()
        
        return self.get_personality(user_id)
    
    def update_personality(self, user_id: str, updates: Dict):
        """Update personality parameters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build update query dynamically
        allowed_fields = [
            'friendliness', 'trust_level', 'mood', 'energy_level',
            'humor_style', 'communication_style'
        ]
        
        set_clauses = []
        values = []
        
        for field, value in updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = ?")
                values.append(value)
        
        if set_clauses:
            set_clauses.append("last_updated = CURRENT_TIMESTAMP")
            values.append(user_id)
            
            query = f"""
                UPDATE personality_params 
                SET {', '.join(set_clauses)}
                WHERE user_id = ?
            """
            cursor.execute(query, values)
            conn.commit()
        
        conn.close()
    
    def save_conversation(self, user_id: str, user_message: str, 
                         ai_response: str, emotion: Optional[str] = None):
        """Save conversation to history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversation_history 
            (user_id, user_message, ai_response, emotion_detected)
            VALUES (?, ?, ?, ?)
        """, (user_id, user_message, ai_response, emotion))
        
        conn.commit()
        conn.close()
    
    def get_recent_conversations(self, user_id: str, limit: int = 10) -> list:
        """Get recent conversation history"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM conversation_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def save_reflection(self, user_id: str, reflection_text: str, 
                       personality_changes: Dict):
        """Save AI's self-reflection result"""
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO reflection_logs 
            (user_id, reflection_text, personality_changes)
            VALUES (?, ?, ?)
        """, (user_id, reflection_text, json.dumps(personality_changes)))
        
        conn.commit()
        conn.close()
