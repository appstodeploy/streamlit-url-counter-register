import streamlit as st
import pandas as pd
import ast
from collections import Counter

st.title("Interactive URL Count by Date Filter")

# **Step 1: Upload CSV File**
uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    # Load CSV file
    df = pd.read_csv(uploaded_file)

    # Ensure 'Created' column is in datetime format
    if "Created" in df.columns:
        df["Created"] = pd.to_datetime(df["Created"], errors="coerce")
    else:
        st.error("The uploaded CSV must contain a 'Created' column.")
        st.stop()

    # Ensure required columns are present
    if "Origin" not in df.columns or "Last Origin" not in df.columns:
        st.error("The uploaded CSV must contain 'Origin' and 'Last Origin' columns.")
        st.stop()

    df["Origin"] = df["Origin"].astype(str)
    df["Last Origin"] = df["Last Origin"].astype(str)

    # **Extract firstVisitedPage base paths**
    def extract_first_visited_pages(origin):
        try:
            origin_data = ast.literal_eval(origin)  # Convert string to Python object

            if isinstance(origin_data, dict):  # If it's a single dict
                return [origin_data["firstVisitedPage"].split("?")[0]] if "firstVisitedPage" in origin_data else []

            elif isinstance(origin_data, list):  # If it's a list of dicts
                return [entry["firstVisitedPage"].split("?")[0] for entry in origin_data if isinstance(entry, dict) and "firstVisitedPage" in entry]

        except (ValueError, SyntaxError):
            return []  # Return empty list on failure
        return []

    # Apply function to extract base paths of firstVisitedPage URLs
    df["first_visited_pages"] = df["Origin"].apply(extract_first_visited_pages)

    # **Step 2: Interactive Date Filter**
    min_date = df["Created"].min()
    max_date = df["Created"].max()

    start_date, end_date = st.date_input(
        "Select Date Range",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

    # Convert selected dates to datetime
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Filter data based on selected date range
    filtered_df = df[(df["Created"] >= start_date) & (df["Created"] <= end_date)]

    # **Step 3: Count firstVisitedPage occurrences**
    url_counts = Counter([url for sublist in filtered_df["first_visited_pages"] for url in sublist])

    # **New: Count only those URLs in Last Origin using full pattern match**
    last_origin_counts = Counter()

    for url in url_counts.keys():  # Only count URLs that exist in Origin
        search_pattern = f"'firstVisitedPage': '{url}'"
        last_origin_counts[url] = filtered_df["Last Origin"].str.contains(search_pattern, regex=False).sum()

    # Count URLs appearing exactly 2, 3, and 4 times per row
    url_x_times_counts = {2: Counter(), 3: Counter(), 4: Counter()}

    for urls in filtered_df["first_visited_pages"]:
        url_frequency_per_row = Counter(urls)
        for url, count in url_frequency_per_row.items():
            if count in url_x_times_counts:
                url_x_times_counts[count][url] += 1

    # Convert to DataFrame
    url_count_df = pd.DataFrame(url_counts.items(), columns=["URL", "Origin"])
    url_count_df["2 Times"] = url_count_df["URL"].map(url_x_times_counts[2]).fillna(0).astype(int)
    url_count_df["3 Times"] = url_count_df["URL"].map(url_x_times_counts[3]).fillna(0).astype(int)
    url_count_df["4 Times"] = url_count_df["URL"].map(url_x_times_counts[4]).fillna(0).astype(int)
    url_count_df["Last Origin Count"] = url_count_df["URL"].map(last_origin_counts).fillna(0).astype(int)

    # Sort by Origin count
    url_count_df = url_count_df.sort_values(by="Origin", ascending=False)

    # Display results
    st.dataframe(url_count_df)

    # **Step 4: Allow user to download the filtered results**
    csv = url_count_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "filtered_url_counts.csv", "text/csv")
