import json

import pandas as pd
import streamlit as st
from loguru import logger
from psycopg2 import pool

from utils.openai_helpers import assign_tags

# Create a global connection pool
pg_pool = pool.SimpleConnectionPool(
    1,
    20,  # Min and max connections in the pool
    dbname=st.secrets["PG_DATABASE"],
    user=st.secrets["PG_USER"],
    password=st.secrets["PG_PASSWORD"],
    host=st.secrets["PG_HOST"],
    port=st.secrets["PG_PORT"],
)


def get_pg_connection_from_pool():
    """Get a connection from the pool."""
    if pg_pool:
        return pg_pool.getconn()
    else:
        raise Exception("Connection pool not initialized.")


def count_rows() -> int:
    """Count the number of rows in the conversations table using a connection pool."""
    conn = None
    try:
        # Get a connection from the pool
        conn = get_pg_connection_from_pool()
        c = conn.cursor()

        # Execute the query
        c.execute("SELECT COUNT(*) FROM conversations")
        return c.fetchone()[0]
    finally:
        # Always release the connection back to the pool
        if conn:
            pg_pool.putconn(conn)


def create_table():
    """Create tables to store conversations and tags as needed."""
    conn = None
    try:
        conn = get_pg_connection_from_pool()
        c = conn.cursor()

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                session_id TEXT PRIMARY KEY,
                conversation_data JSONB,
                timestamp TIMESTAMPTZ
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_tags (
                session_id TEXT PRIMARY KEY,
                anxious INTEGER DEFAULT 0,
                sad INTEGER DEFAULT 0,
                sleepless INTEGER DEFAULT 0,
                worried INTEGER DEFAULT 0,
                hyperfixated INTEGER DEFAULT 0,
                distracted INTEGER DEFAULT 0
            )
            """
        )

        conn.commit()
    finally:
        if conn:
            pg_pool.putconn(conn)


def save_conversation(session_id, conversation, timestamp):
    """Save the entire conversation as a JSON object in the PostgreSQL database along with a static session timestamp."""
    conversation_data = json.dumps(conversation)
    conn = None
    try:
        conn = get_pg_connection_from_pool()
        c = conn.cursor()

        c.execute(
            """
            INSERT INTO conversations (session_id, conversation_data, timestamp)
            VALUES (%s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE
            SET conversation_data = EXCLUDED.conversation_data, timestamp = EXCLUDED.timestamp;
            """,
            (session_id, conversation_data, timestamp),
        )
        conn.commit()
    finally:
        if conn:
            pg_pool.putconn(conn)


def get_conversation(session_id):
    """Retrieve the entire conversation for a given session from the PostgreSQL database."""
    conn = None
    try:
        conn = get_pg_connection_from_pool()
        c = conn.cursor()

        c.execute(
            "SELECT conversation_data FROM conversations WHERE session_id = %s",
            (session_id,),
        )
        result = c.fetchone()
        return json.loads(result[0]) if result else None
    finally:
        if conn:
            pg_pool.putconn(conn)


def update_tags(session_id, active_tags):
    """Update the tags for a given conversation in the `conversation_tags` table."""
    conn = None
    try:
        conn = get_pg_connection_from_pool()
        c = conn.cursor()

        predefined_tags = [
            "anxious",
            "sad",
            "sleepless",
            "worried",
            "hyperfixated",
            "distracted",
        ]
        tag_values = {
            tag: 1 if tag in active_tags else 0 for tag in predefined_tags}

        columns = ", ".join(predefined_tags)
        placeholders = ", ".join(["%s"] * len(predefined_tags))
        query = f"""
        INSERT INTO conversation_tags (session_id, {columns})
        VALUES (%s, {placeholders})
        ON CONFLICT (session_id) DO UPDATE
        SET {", ".join([f"{tag} = EXCLUDED.{tag}" for tag in predefined_tags])};
        """
        values = (session_id, *tag_values.values())

        c.execute(query, values)
        conn.commit()
    finally:
        if conn:
            pg_pool.putconn(conn)


def add_new_tag_column(tag):
    """Add a new column to the conversation_tags table for a new tag."""
    conn = None
    try:
        conn = get_pg_connection_from_pool()
        c = conn.cursor()

        # Use IF NOT EXISTS to avoid errors if the column already exists
        c.execute(
            f"ALTER TABLE conversation_tags ADD COLUMN IF NOT EXISTS {tag} INTEGER DEFAULT 0"
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error adding new tag column: {e}")
    finally:
        if conn:
            pg_pool.putconn(conn)


def get_predefined_tags_from_db():
    """Extract predefined tags by fetching all column names from the `conversation_tags` table except `session_id`."""
    conn = None
    try:
        conn = get_pg_connection_from_pool()
        c = conn.cursor()

        c.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'conversation_tags' AND column_name != 'session_id';
        """
        )
        return [row[0] for row in c.fetchall()]
    finally:
        if conn:
            pg_pool.putconn(conn)


def load_tagged_data(timeframe, predefined_tags) -> pd.DataFrame:
    """
    Load tagged conversations from the `conversation_tags` table based on the selected timeframe.
    """
    conn = None
    try:
        conn = get_pg_connection_from_pool()

        # Create the SQL query by including the dynamically retrieved tags
        tags_columns = ", ".join(predefined_tags)
        query = f"""
        SELECT t.session_id, c.timestamp, {tags_columns}
        FROM conversation_tags t
        JOIN conversations c ON t.session_id = c.session_id
        """

        # Apply timeframe filtering using PostgreSQL date functions
        if timeframe == "1 month":
            query += " WHERE c.timestamp >= NOW() - INTERVAL '1 month'"
        elif timeframe == "1 week":
            query += " WHERE c.timestamp >= NOW() - INTERVAL '7 days'"

        return pd.read_sql_query(query, conn)
    finally:
        if conn:
            pg_pool.putconn(conn)


def process_all_unprocessed_conversations(predefined_tags):
    """
    Process all untagged conversations by running them through assign_tags
    and storing the tags in the `conversation_tags` table.
    """
    conn = None
    try:
        conn = get_pg_connection_from_pool()
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
        if unprocessed_conversations := c.fetchall():
            for session_id, conversation_data in unprocessed_conversations:
                # Ensure conversation_data is passed as a string
                if isinstance(conversation_data, (list, dict)):
                    # breakpoint()
                    conversation_data = json.dumps(conversation_data)
                # Run assign_tags to get active and suggested tags
                active_tags, suggested_tags = assign_tags(
                    conversation_data, predefined_tags
                )

                # Save the active tags into the database
                update_conversation_tags(
                    session_id, active_tags, predefined_tags)

                logger.info(
                    f"Processed conversation {session_id} and tagged it.")
                logger.info(f"Active Tags: {active_tags}")
                logger.info(f"Suggested Tags: {suggested_tags}")
        else:
            logger.info("No unprocessed conversations found.")

    finally:
        if conn:
            pg_pool.putconn(conn)


def update_conversation_tags(session_id, active_tags, predefined_tags):
    """Update the tags for a given conversation in the `conversation_tags` table."""
    conn = None
    try:
        conn = get_pg_connection_from_pool()
        c = conn.cursor()

        # Construct the tag values based on predefined_tags
        tag_values = {
            tag: 1 if tag in active_tags else 0 for tag in predefined_tags}

        # Create dynamic columns and placeholders for insertion
        columns = ", ".join(predefined_tags)
        placeholders = ", ".join(["%s"] * len(predefined_tags))
        query = f"""
        INSERT INTO conversation_tags (session_id, {columns})
        VALUES (%s, {placeholders})
        ON CONFLICT (session_id) DO UPDATE
        SET {", ".join([f"{tag} = EXCLUDED.{tag}" for tag in predefined_tags])};
        """

        # Prepare the values for execution
        values = (session_id, *tag_values.values())

        # Execute the query to insert or update the tags
        c.execute(query, values)
        conn.commit()
    finally:
        if conn:
            pg_pool.putconn(conn)
