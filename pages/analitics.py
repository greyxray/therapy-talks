import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from loguru import logger
from utils.database_helpers import (
    get_connection,
    count_rows,
    load_data,
    get_predefined_tags_from_db,
    load_tagged_data,
    process_all_unprocessed_conversations,
    update_conversation_tags,
)
from utils.openai_helpers import assign_tags  # Assuming this exists


def plot_tag_histogram(df, binning, predefined_tags):
    """Plot the histogram of tags based on the binning option using Plotly."""
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Melt the DataFrame to have one row per tag
    df_melted = df.melt(
        id_vars=["timestamp"],
        value_vars=predefined_tags,
        var_name="tag",
        value_name="count",
    )

    # Only keep rows where 'count' is 1 (i.e., where the tag was applied)
    df_melted = df_melted[df_melted["count"] == 1]

    # Group by time bin and tag
    if binning == "Day":
        df_melted["date"] = df_melted["timestamp"].dt.date
    elif binning == "Week":
        df_melted["date"] = (
            df_melted["timestamp"].dt.to_period("W").apply(lambda r: r.start_time)
        )
    elif binning == "Month":
        df_melted["date"] = (
            df_melted["timestamp"].dt.to_period("M").apply(lambda r: r.start_time)
        )

    # Count the number of conversations per tag per time bin
    df_grouped = df_melted.groupby(["date", "tag"]).size().reset_index(name="count")

    # Plot histogram using Plotly
    fig = px.bar(
        df_grouped,
        x="date",
        y="count",
        color="tag",
        title=f"Conversations Tagged by {binning}",
        labels={
            "date": f"Binned by {binning}",
            "count": "Number of Conversations",
            "tag": "Tag",
        },
    )

    fig.update_layout(
        xaxis_title=f"Binned by {binning}",
        yaxis_title="Number of Conversations",
        xaxis_tickformat="%Y-%m-%d",
    )

    st.plotly_chart(fig)


def main():
    st.title("Chatbot Analytics with Tagging")

    # Dynamically load predefined tags
    predefined_tags = get_predefined_tags_from_db()

    # Process all untagged conversations before continuing with the analysis
    process_all_unprocessed_conversations(predefined_tags)

    # Display total number of conversations
    st.write(f"Total number of conversations: {count_rows()}")

    # Timeframe dropdown
    timeframe = st.selectbox(
        "Select Timeframe", ["All time", "1 month", "1 week"], index=0
    )

    # Binning option dropdown
    binning = st.selectbox("Bin conversations by", ["Day", "Week", "Month"], index=0)

    # Load conversation data with tags based on timeframe
    df = load_tagged_data(timeframe, predefined_tags)

    if df.empty:
        st.write("No conversations found for the selected timeframe.")
    else:
        # Plot the histogram using Plotly
        plot_tag_histogram(df, binning, predefined_tags)


if __name__ == "__main__":
    main()
