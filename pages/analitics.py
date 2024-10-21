import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from loguru import logger

from utils.database_helpers import count_rows, load_data


def plot_histogram(df, binning):
    """Plot the histogram based on the binning option using Plotly."""
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    if binning == "Day":
        df["date"] = df["timestamp"].dt.date
    elif binning == "Week":
        df["date"] = df["timestamp"].dt.to_period("W").apply(lambda r: r.start_time)
    elif binning == "Month":
        df["date"] = df["timestamp"].dt.to_period("M").apply(lambda r: r.start_time)

    # Group data by the selected binning period
    df_grouped = df["date"].value_counts().sort_index().reset_index()
    df_grouped.columns = ["date", "count"]

    # Plot histogram using Plotly
    fig = px.bar(
        df_grouped,
        x="date",
        y="count",
        title=f"Conversations Binned by {binning}",
        labels={"date": f"Binned by {binning}", "count": "Number of Conversations"},
    )
    fig.update_layout(
        xaxis_title=f"Binned by {binning}",
        yaxis_title="Number of Conversations",
        xaxis_tickformat="%Y-%m-%d",
    )

    st.plotly_chart(fig)


def main():
    st.title("Chatbot Analytics")

    # Display row count in Streamlit app
    st.write(f"Total number of conversations: {count_rows()}")

    # Timeframe dropdown
    timeframe = st.selectbox(
        "Select Timeframe", ["All time", "1 month", "1 week"], index=0
    )

    # Binning option dropdown
    binning = st.selectbox("Bin conversations by", ["Day", "Week", "Month"], index=0)

    # Load conversation data based on timeframe
    df = load_data(timeframe)

    if df.empty:
        st.write("No conversations found for the selected timeframe.")
    else:
        # Plot the histogram using Plotly
        plot_histogram(df, binning)


if __name__ == "__main__":
    main()
