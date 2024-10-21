import sqlite3
from loguru import logger
import json
from configs.constants import DATABASE_PATH


def get_connection():
    """Create a new SQLite connection."""
    return sqlite3.connect(DATABASE_PATH)


def count_rows() -> int:
    conn = get_connection()
    c = conn.cursor()

    # Query to count rows
    c.execute("SELECT COUNT(*) FROM conversations")
    counts = c.fetchone()[0]
    conn.close()
    return counts


def create_table():
    """Create a table to store conversations as JSON."""
    # Create a new connection for this query
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT PRIMARY KEY,
            conversation_data TEXT
        )
    """
    )
    conn.commit()
    conn.close()


def save_conversation(session_id, conversation, timestamp):
    """
    Save the entire conversation as a JSON object in the database
    along with a static session timestamp.
    """
    # Convert conversation to JSON format
    conversation_data = json.dumps(conversation)

    # Create a new connection for this query
    conn = get_connection()
    c = conn.cursor()

    # Save the conversation and session timestamp
    c.execute(
        """
        INSERT OR REPLACE INTO conversations (session_id, conversation_data, timestamp)
        VALUES (?, ?, ?)
        """,
        (session_id, conversation_data, timestamp),
    )
    conn.commit()
    conn.close()  # Close the connection after committing


def get_conversation(session_id):
    """Retrieve the entire conversation for a given session from the database."""
    # Create a new connection for this query
    conn = get_connection()
    c = conn.cursor()

    # Fetch the conversation data and timestamp from the database
    c.execute(
        "SELECT conversation_data, timestamp FROM conversations WHERE session_id = ?",
        (session_id,),
    )
    result = c.fetchone()
    conn.close()  # Close the connection after fetching the result

    if result:
        conversation_data, timestamp = result
        # Parse the JSON string from conversation_data
        conversation = json.loads(conversation_data)
        return (
            conversation,
            timestamp,
        )  # Return parsed conversation and session timestamp
    return None  # Return None if no conversation found


def get_session_start(session_id):
    """Retrieve the session start time, if it exists."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT timestamp FROM conversations WHERE session_id = ? LIMIT 1",
        (session_id,),
    )
    result = c.fetchone()
    conn.close()

    res = result[0] if result else None
    return res
