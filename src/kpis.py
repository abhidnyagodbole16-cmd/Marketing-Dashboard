# kpis.py - functions that calculate the marketing KPIs
# the dashboard (app.py) will import these functions later

import pandas as pd


# takes a table that has the SUMMED columns and adds the KPI columns
def add_kpi_columns(df):
    df = df.copy()

    # replacing 0 with NaN stops "division by zero" errors
    clicks = df["clicks"].replace(0, float("nan"))
    conversions = df["conversions"].replace(0, float("nan"))
    spend = df["spend"].replace(0, float("nan"))

    df["ctr"] = df["clicks"] / df["impressions"] * 100  # click-through rate (%)
    df["conversion_rate"] = df["conversions"] / clicks * 100  # conversion rate (%)
    df["cpc"] = df["spend"] / clicks  # cost per click
    df["cpa"] = df["spend"] / conversions  # cost per acquisition
    df["roi"] = (df["revenue"] - df["spend"]) / spend * 100  # return on investment (%)
    df["engagement_rate"] = (df["likes"] + df["shares"] + df["comments"]) / df["reach"] * 100
    return df


# KPIs grouped by a column, e.g. kpis_by(df, "channel") or kpis_by(df, "campaign_name")
def kpis_by(df, column):
    # add up the raw numbers first, then divide.
    # Averaging each row's CTR would give a wrong answer.
    totals = df.groupby(column)[["spend", "impressions", "clicks", "conversions",
                                 "revenue", "likes", "shares", "comments", "reach"]].sum()
    totals = totals.reset_index()
    return add_kpi_columns(totals)


# KPIs for the whole table as a single row (for the cards at the top of the dashboard)
def overall_kpis(df):
    totals = df[["spend", "impressions", "clicks", "conversions",
                 "revenue", "likes", "shares", "comments", "reach"]].sum()
    totals = totals.to_frame().T  # turn the sums into a 1-row table
    return add_kpi_columns(totals).iloc[0]


# social media KPIs (uses the social_media table)

# takes a social media table with SUMMED columns and adds the KPI columns
def add_social_kpi_columns(df):
    df = df.copy()
    reach = df["reach"].replace(0, float("nan"))
    total_engagement = df["likes"] + df["comments"] + df["shares"] + df["saves"]

    df["total_engagement"] = total_engagement
    df["engagement_rate"] = total_engagement / reach * 100  # (likes+comments+shares+saves) / reach
    df["share_rate"] = df["shares"] / reach * 100
    df["save_rate"] = df["saves"] / reach * 100
    df["link_ctr"] = df["link_clicks"] / reach * 100  # how many reached people clicked the link
    df["follower_growth_rate"] = df["new_followers"] / reach * 100  # new followers per 100 people reached
    return df


# social KPIs grouped by a column, e.g. 'platform' or 'post_type'
def social_kpis_by(df, column):
    totals = df.groupby(column).agg(
        posts=("post_id", "count"),
        impressions=("impressions", "sum"),
        reach=("reach", "sum"),
        likes=("likes", "sum"),
        comments=("comments", "sum"),
        shares=("shares", "sum"),
        saves=("saves", "sum"),
        link_clicks=("link_clicks", "sum"),
        new_followers=("new_followers", "sum"),
    ).reset_index()
    totals = add_social_kpi_columns(totals)
    totals["avg_reach_per_post"] = totals["reach"] / totals["posts"]
    totals["avg_engagement_per_post"] = totals["total_engagement"] / totals["posts"]
    return totals


# social KPIs for the whole table as one row
def overall_social_kpis(df):
    totals = df[["impressions", "reach", "likes", "comments", "shares",
                 "saves", "link_clicks", "new_followers"]].sum()
    totals = add_social_kpi_columns(totals.to_frame().T).iloc[0]
    totals["posts"] = len(df)
    return totals


# website traffic KPIs (uses the web_traffic table)

# website KPIs grouped by a column, e.g. 'source'
def web_kpis_by(df, column):
    df = df.copy()
    # bounce rate, session time and pages are AVERAGES, so weight them by sessions
    # (a day with 5000 sessions should count more than a day with 50)
    df["bounced_sessions"] = df["sessions"] * df["bounce_rate"] / 100
    df["total_duration"] = df["sessions"] * df["avg_session_duration"]
    df["total_pages"] = df["sessions"] * df["pages_per_session"]

    totals = df.groupby(column)[["sessions", "users", "new_users", "bounced_sessions",
                                 "total_duration", "total_pages"]].sum().reset_index()
    totals["bounce_rate"] = totals["bounced_sessions"] / totals["sessions"] * 100
    totals["avg_session_duration"] = totals["total_duration"] / totals["sessions"]
    totals["pages_per_session"] = totals["total_pages"] / totals["sessions"]
    totals["new_user_share"] = totals["new_users"] / totals["users"] * 100
    return totals[[column, "sessions", "users", "new_users", "new_user_share",
                   "bounce_rate", "avg_session_duration", "pages_per_session"]]


# website KPIs for the whole table as one row
def overall_web_kpis(df):
    df = df.copy()
    df["all"] = "all"
    return web_kpis_by(df, "all").iloc[0]


# cross-dataset KPIs (campaigns + web_traffic, joined on channel)

# ties ad performance to website behaviour for the 5 paid channels
def channel_funnel(campaigns, traffic):
    ads = kpis_by(campaigns, "channel")
    web = web_kpis_by(traffic, "source").rename(columns={"source": "channel"})
    both = ads.merge(web[["channel", "sessions", "bounce_rate", "avg_session_duration"]],
                     on="channel", suffixes=("", "_web"))

    both["click_to_session_rate"] = both["sessions"] / both["clicks"] * 100  # clicks that reached the site
    both["cost_per_session"] = both["spend"] / both["sessions"]
    both["revenue_per_session"] = both["revenue"] / both["sessions"]
    both["session_conversion_rate"] = both["conversions"] / both["sessions"] * 100
    return both
