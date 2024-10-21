import sqlite3
from loguru import logger
import pandas as pd
import json
from configs.constants import DATABASE_PATH
from datetime import datetime, timedelta
from utils.openai_helpers import (
    assign_tags,
)  # Assuming this is the assign_tags function we defined earlier


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


def load_data(timeframe):
    """Load conversation data based on the selected timeframe."""
    conn = get_connection()
    query = "SELECT timestamp FROM conversations"

    # Filter by timeframe
    if timeframe == "1 month":
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        query += f" WHERE timestamp >= '{start_date}'"
    elif timeframe == "1 week":
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        query += f" WHERE timestamp >= '{start_date}'"

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def load_tagged_data(timeframe, predefined_tags) -> pd.DataFrame:
    """
    Load tagged conversations from the `conversation_tags` table based on the selected timeframe.
    """
    conn = get_connection()

    # Create the SQL query by including the dynamically retrieved tags
    tags_columns = ", ".join(predefined_tags)
    query = f"""
    SELECT t.session_id, c.timestamp, {tags_columns}
    FROM conversation_tags t
    JOIN conversations c ON t.session_id = c.session_id
    """

    # Apply timeframe filtering
    if timeframe == "1 month":
        query += " WHERE c.timestamp >= date('now', '-1 month')"
    elif timeframe == "1 week":
        query += " WHERE c.timestamp >= date('now', '-7 days')"

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def process_all_unprocessed_conversations(predefined_tags):
    """
    Process all untagged conversations by running them through assign_tags
    and storing the tags in the `conversation_tags` table.
    """
    conn = get_connection()
    c = conn.cursor()

    # Fetch all unprocessed conversations
    query = """
    SELECT c.session_id, c.conversation_data
    FROM conversations c
    LEFT JOIN conversation_tags t
    ON c.session_id = t.session_id
    WHERE t.session_id IS NULL;
    """
    c.execute(query)
    unprocessed_conversations = c.fetchall()

    if unprocessed_conversations:
        for session_id, conversation_data in unprocessed_conversations:
            # Run assign_tags to get active and suggested tags
            active_tags, suggested_tags = assign_tags(
                conversation_data, predefined_tags
            )

            # Save the active tags into the database
            update_conversation_tags(session_id, active_tags, predefined_tags)

            logger.info(f"Processed conversation {session_id} and tagged it.")
            logger.info(f"Active Tags: {active_tags}")
            logger.info(f"Suggested Tags: {suggested_tags}")
    else:
        logger.info("No unprocessed conversations found.")

    conn.close()


def update_conversation_tags(session_id, active_tags, predefined_tags):
    """
    Save the active tags for a given conversation in the `conversation_tags` table in `chatbot.db`.
    """
    conn = get_connection()
    c = conn.cursor()

    # Set values for each tag (1 if present in tags, otherwise 0)
    tag_values = {tag: 1 if tag in active_tags else 0 for tag in predefined_tags}

    # Create a dynamic SQL query for inserting or replacing the tag values
    columns = ", ".join(predefined_tags)
    placeholders = ", ".join(["?"] * len(predefined_tags))
    query = f"""
    INSERT OR REPLACE INTO conversation_tags (session_id, {columns})
    VALUES (?, {placeholders})
    """

    # Define the values to be inserted into the query, corresponding to each tag column
    values = (session_id, *tag_values.values())

    # Execute the query to update the conversation_tags table
    c.execute(query, values)

    # Commit the transaction and close the connection
    conn.commit()
    conn.close()


def add_new_tag_column(tag):
    """Add a new column to the conversation_tags table for a new tag."""
    conn = get_connection()
    c = conn.cursor()

    # Add the new tag column with default value 0
    c.execute(f"ALTER TABLE conversation_tags ADD COLUMN {tag} INTEGER DEFAULT 0")

    conn.commit()
    conn.close()

def get_predefined_tags_from_db():
    """
    Extract predefined tags by fetching all column names from the `conversation_tags` table
    except `session_id`.
    """
    # Connect to the database
    conn = get_connection()
    c = conn.cursor()

    # Query to get all column names from the conversation_tags table
    query = "PRAGMA table_info(conversation_tags);"
    c.execute(query)

    # Fetch all columns from the result of the query
    columns_info = c.fetchall()

    # Close the database connection
    conn.close()

    # Extract column names excluding 'session_id'
    predefined_tags = [
        column[1] for column in columns_info if column[1] != "session_id"
    ]

    return predefined_tags
