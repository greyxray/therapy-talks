import streamlit as st
from utils.database_helpers import get_conversation

from utils.database_helpers import count_rows

def main():
    st.title("Conversation Analytics")

    session_id = st.text_input("Enter Session ID to analyze:")

    if session_id:
        conversation = get_conversation(session_id)
        if conversation:
            st.write("Conversation History:")
            for msg in conversation:
                st.write(f"{msg['role']}: {msg['content']}")
        else:
            st.error("No conversation found for this Session ID.")

    # Display row count in Streamlit app
    st.write(f"Total number of rows in 'conversations': {count_rows()}")

if __name__ == "__main__":
    main()
