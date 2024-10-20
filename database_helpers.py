import sqlite3
from loguru import logger
import json

conn = sqlite3.connect("chatbot.db")
c = conn.cursor()

def create_table():
    """Create a table to store conversations as JSON."""
    # conn = sqlite3.connect("chatbot.db")
    # c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT PRIMARY KEY,
            conversation_data TEXT
        )
    """
    )
    conn.commit()
    # conn.close()


def save_conversation(session_id, conversation):
    """Save the entire conversation as a JSON object in the database."""
    conversation_data = json.dumps(conversation)
    c.execute(
        """
        INSERT OR REPLACE INTO conversations (session_id, conversation_data)
        VALUES (?, ?)
    """,
        (session_id, conversation_data),
    )
    conn.commit()
    logger.info("Conversation saved successfully.")


def get_conversation(session_id):
    """Retrieve the conversation for a given session from the database."""
    c.execute(
        "SELECT conversation_data FROM conversations WHERE session_id = ?",
        (session_id,),
    )
    return json.loads(result[0]) if (result := c.fetchone()) else []
