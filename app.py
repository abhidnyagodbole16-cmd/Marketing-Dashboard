# app.py - Marketing Performance Dashboard (version 1: filters + KPI cards)
# run from the project folder:  streamlit run app.py

import sqlite3
import pandas as pd
import streamlit as st
from src.kpis import overall_kpis

# ---- page settings (must be the first streamlit command) ----
st.set_page_config(page_title="Marketing Performance Dashboard", layout="wide")


# ---- load the data from the database ----
# @st.cache_data means the data is loaded once, not every time a filter changes
@st.cache_data
def load_data():
    conn = sqlite3.connect("marketing.db")
    df = pd.read_sql("SELECT * FROM campaigns", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    return df

df = load_data()

# ---- title ----
st.title("Marketing Performance Dashboard")
st.caption("Dataset: self-created (synthetic) marketing data for 2025")

# ---- sidebar filters ----
st.sidebar.header("Filters")

# 1. date range
min_date = df["date"].min().date()
max_date = df["date"].max().date()
date_range = st.sidebar.date_input("Date range", value=(min_date, max_date),
                                   min_value=min_date, max_value=max_date)

# 2. channel
all_channels = sorted(df["channel"].unique())
selected_channels = st.sidebar.multiselect("Channel", all_channels, default=all_channels)

# 3. campaign (only shows campaigns from the selected channels)
campaign_options = sorted(df[df["channel"].isin(selected_channels)]["campaign_name"].unique())
selected_campaigns = st.sidebar.multiselect("Campaign", campaign_options, default=campaign_options)

# ---- apply the filters ----
# date_input gives 1 date while the user is still picking the 2nd one, so wait for both
if len(date_range) != 2:
    st.info("Please pick an end date.")
    st.stop()

start_date, end_date = date_range
filtered = df[
    (df["date"] >= pd.to_datetime(start_date))
    & (df["date"] <= pd.to_datetime(end_date))
    & (df["channel"].isin(selected_channels))
    & (df["campaign_name"].isin(selected_campaigns))
]

# if the filters remove everything, stop here instead of showing errors
if filtered.empty:
    st.warning("No data for these filters. Try selecting more channels or campaigns.")
    st.stop()

# ---- KPI cards ----
kpi = overall_kpis(filtered)

st.subheader("Key Performance Indicators")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Spend", f"₹{kpi['spend']:,.0f}")
col2.metric("Total Revenue", f"₹{kpi['revenue']:,.0f}")
col3.metric("ROI", f"{kpi['roi']:.1f}%")
col4.metric("CTR", f"{kpi['ctr']:.2f}%")
col5.metric("Conversion Rate", f"{kpi['conversion_rate']:.2f}%")

col6, col7, col8, col9, col10 = st.columns(5)
col6.metric("Impressions", f"{kpi['impressions']:,.0f}")
col7.metric("Clicks", f"{kpi['clicks']:,.0f}")
col8.metric("Conversions", f"{kpi['conversions']:,.0f}")
col9.metric("Cost per Acquisition", f"₹{kpi['cpa']:,.0f}")
col10.metric("Engagement Rate", f"{kpi['engagement_rate']:.2f}%")

# ---- data table ----
st.subheader("Filtered data")
st.write(f"Showing {len(filtered):,} rows")
st.dataframe(filtered, use_container_width=True)
