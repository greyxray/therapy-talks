"""
Main file for the Listener App.
"""

import streamlit as st


def main():
    """
    Main function for the Listener App.
    """
    st.title("Welcome to the Listener App!")
    st.write(
        """
        This app has three main pages:
        - **Chat**: Chat with our AI listener.
        - **Analytics**: Analyze the conversation and gather insights.
        - **ReadMe**: Learn more about how this app works.
    """
    )


if __name__ == "__main__":
    main()
