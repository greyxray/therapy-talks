import json
import os

import openai
import streamlit as st
from loguru import logger

from configs.constants import tags_instructions

openai.api_key = st.secrets["OPENAI_API_KEY"]


def assign_tags(conversation, predefined_tags):
    """Use OpenAI to suggest which tags are relevant for the conversation."""
    # logger.debug(f"Tag instructions: {tags_instructions.format(conversation=conversation, predefined_tags=predefined_tags)}")
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": tags_instructions.format(
                    conversation=json.loads(conversation)[
                        1:
                    ],  # Skip the initial system message
                    predefined_tags=predefined_tags,
                ),
            }
        ],
        max_tokens=100,
        n=1,
        temperature=0.5,
    )
    # Assuming OpenAI returns the tags in comma-separated format

    # Extract the response text and load it as JSON
    response_text = response["choices"][0]["message"]["content"].strip()

    try:
        # Parse the JSON result
        tags_data = json.loads(response_text)

        # Ensure the tags are lowercase
        active_tags = [tag.lower() for tag in tags_data.get("active_tags", [])]
        suggested_tags = [
            tag.lower() for tag in tags_data.get(
                "suggested_tags", [])]

        return active_tags, suggested_tags

    except json.JSONDecodeError:
        # Handle case where the response is not valid JSON
        logger.error("Error: Failed to parse JSON from OpenAI response.")
        return [], []  # Return empty lists in case of error
