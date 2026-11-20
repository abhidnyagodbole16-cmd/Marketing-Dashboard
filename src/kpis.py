# kpis.py - functions that calculate the marketing KPIs
# the dashboard (app.py) will import these functions later

import pandas as pd


def add_kpi_columns(df):
    """Takes a table that has the SUMMED columns and adds the KPI columns."""
    df = df.copy()

    # replacing 0 with NaN stops "division by zero" errors
    clicks = df["clicks"].replace(0, float("nan"))
    conversions = df["conversions"].replace(0, float("nan"))
    spend = df["spend"].replace(0, float("nan"))

    df["ctr"] = df["clicks"] / df["impressions"] * 100            # click-through rate (%)
    df["conversion_rate"] = df["conversions"] / clicks * 100      # conversion rate (%)
    df["cpc"] = df["spend"] / clicks                              # cost per click
    df["cpa"] = df["spend"] / conversions                         # cost per acquisition
    df["roi"] = (df["revenue"] - df["spend"]) / spend * 100       # return on investment (%)
    df["engagement_rate"] = (df["likes"] + df["shares"] + df["comments"]) / df["reach"] * 100
    return df


def kpis_by(df, column):
    """KPIs grouped by a column, e.g. kpis_by(df, "channel") or kpis_by(df, "campaign_name")."""
    # IMPORTANT: add up the raw numbers first, THEN divide.
    # Averaging each row's CTR would give a wrong answer.
    totals = df.groupby(column)[["spend", "impressions", "clicks", "conversions",
                                 "revenue", "likes", "shares", "comments", "reach"]].sum()
    totals = totals.reset_index()
    return add_kpi_columns(totals)


def overall_kpis(df):
    """KPIs for the whole table as a single row (for the cards at the top of the dashboard)."""
    totals = df[["spend", "impressions", "clicks", "conversions",
                 "revenue", "likes", "shares", "comments", "reach"]].sum()
    totals = totals.to_frame().T          # turn the sums into a 1-row table
    return add_kpi_columns(totals).iloc[0]
