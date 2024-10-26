import uuid  # For generating session IDs
from datetime import datetime
from pprint import pformat

import openai
import streamlit as st

# from dotenv import load_dotenv
from loguru import logger

# Importing the preset instruction
from configs.constants import coach_instructions

# import os
from utils.pg_database_helpers import get_conversation, save_conversation

# Load environment variables
# load_dotenv()

# Set up GPT-4.0 Turbo Mini API
openai.api_key = st.secrets["OPENAI_API_KEY"]


def get_response(messages):
    # Always use gpt-4.0-mini model
    logger.debug(f"Getting response for messages:\n{pformat(messages)}")
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini", messages=messages  # Pass the conversation history
    )
    return response["choices"][0]["message"]["content"]


def main():
    st.title("Listener is here")

    # Check if there's already a session ID, if not create one
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        logger.warning(
            f"Creating new session ID manually: {st.session_state.session_id}",
        )

    session_id = st.session_state.session_id
    logger.warning(
        f"Session ID: {session_id}",
    )

    # logger.warning(f"st.session_state:\n{pformat(st.session_state)}")

    # Initialize session state for conversation history
    if "messages" not in st.session_state:
        # Retrieve previous conversations from the database (conversation and
        # session_start)
        previous_data = get_conversation(session_id)

        if previous_data:
            # Load previous conversation and session start time
            st.session_state.messages, st.session_state.session_start = previous_data
        else:
            # Initialize new conversation and session start time
            st.session_state.messages = [
                {"role": "system", "content": coach_instructions}
            ]
            st.session_state.session_start = None

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        if message["role"] != "system":  # Exclude system message from being displayed
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("How can I assist you today?"):
        # Generate the session start timestamp if it's the first message
        if not st.session_state.session_start:
            st.session_state.session_start = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Get response from the model
        response = get_response(st.session_state.messages)

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            st.markdown(response)
        # Add assistant response to chat history
        st.session_state.messages.append(
            {"role": "assistant", "content": response})

        # Save the entire conversation (as JSON) in the database
        save_conversation(
            session_id,
            st.session_state.messages,
            st.session_state.session_start)


if __name__ == "__main__":
    main()
