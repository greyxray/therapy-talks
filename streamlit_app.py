

import streamlit as st


def main():
    st.title("Welcome to the Chatbot App!")
    st.write(
        """
        This app has three main pages:
        - **Chat**: Chat with our AI coach.
        - **Analytics**: Analyze the conversation and gather insights.
        - **ReadMe**: Learn more about how this app works.
    """
    )


if __name__ == "__main__":
    main()