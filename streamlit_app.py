import streamlit as st
import openai
from dotenv import load_dotenv
from loguru import logger
import os
from database_helpers import save_conversation, get_conversation
from constants import coach_instructions  # Importing the preset instruction
import uuid  # For generating session IDs

from pprint import pformat

# Load environment variables
load_dotenv()

# Set up GPT-4.0 Turbo Mini API
openai.api_key = os.getenv("OPENAI_API_KEY")


def get_response(messages):
    # Always use gpt-4.0-mini model
    logger.debug(f"Getting response for messages:\n{pformat(messages)}")
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini", messages=messages  # Pass the conversation history
    )
    return response["choices"][0]["message"]["content"]


def main():
    st.title("Coach support Chatbot")

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
        st.session_state.messages = [
            {
                "role": "system",
                "content": coach_instructions,
            }  # Start with coach instructions
        ]

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        if message["role"] != "system":  # Exclude system message from being displayed
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("How can I assist you today?"):
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
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Save the entire conversation (as JSON) in the database
        save_conversation(session_id, st.session_state.messages)


if __name__ == "__main__":
    main()
