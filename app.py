# app.py - Marketing Performance Dashboard (full version)
# run from the project folder:  streamlit run app.py

import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

from src.kpis import (kpis_by, overall_kpis, social_kpis_by, overall_social_kpis,
                      web_kpis_by, overall_web_kpis, channel_funnel)
from src.insights import generate_insights, monthly_table, inr, MONTH_NAMES
from src.reports import (campaign_report, marketing_summary, monthly_report,
                         to_excel_bytes, insights_text)

st.set_page_config(page_title="Marketing Performance Dashboard", layout="wide")

# one colour per channel so every chart uses the same colours
COLORS = {"Instagram": "#E1306C", "Facebook": "#1877F2", "Google Ads": "#F4B400",
          "Email": "#34A853", "YouTube": "#FF0000"}
PAID = list(COLORS.keys())


# loading data
@st.cache_data
def load_data():
    conn = sqlite3.connect("marketing.db")
    campaigns = pd.read_sql("SELECT * FROM campaigns", conn, parse_dates=["date"])
    social = pd.read_sql("SELECT * FROM social_media", conn, parse_dates=["date"])
    traffic = pd.read_sql("SELECT * FROM web_traffic", conn, parse_dates=["date"])
    conn.close()
    return campaigns, social, traffic


# compares each raw file with its cleaned version (for the Data Quality tab)
@st.cache_data
def load_quality_table():
    files = {
        "Campaigns": ("data/raw/campaigns_raw.csv", "data/cleaned/campaigns_clean.csv"),
        "Social media": ("data/raw/social_media_raw.csv", "data/cleaned/social_media_clean.csv"),
        "Website traffic": ("data/raw/web_traffic_raw.csv", "data/cleaned/web_traffic_clean.csv"),
    }
    rows = []
    for name, (raw_file, clean_file) in files.items():
        raw = pd.read_csv(raw_file)
        clean = pd.read_csv(clean_file)
        rows.append({
            "Dataset": name,
            "Raw rows": len(raw),
            "Missing values (raw)": int(raw.isna().sum().sum()),
            "Duplicate rows (raw)": int(raw.duplicated().sum()),
            "Clean rows": len(clean),
            "Rows removed": len(raw) - len(clean),
            "Missing values (clean)": int(clean.isna().sum().sum()),
        })
    return pd.DataFrame(rows)


# draw a plotly chart at full width
def show(fig):
    st.plotly_chart(fig, use_container_width=True)


# items = list of (label, value, optional help text)
def kpi_row(items):
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        if len(item) == 3:
            col.metric(item[0], item[1], help=item[2])
        else:
            col.metric(item[0], item[1])


campaigns_all, social_all, traffic_all = load_data()

# title
st.title("Marketing Performance Dashboard")
st.caption("Dataset: self-created (synthetic) marketing data for 2025. "
           "Insights describe this dataset only, not real businesses.")

# sidebar filters
st.sidebar.header("Filters")

min_date = campaigns_all["date"].min().date()
max_date = campaigns_all["date"].max().date()
date_range = st.sidebar.date_input("Date range", value=(min_date, max_date),
                                   min_value=min_date, max_value=max_date)

all_channels = sorted(campaigns_all["channel"].unique())
selected_channels = st.sidebar.multiselect("Channel", all_channels, default=all_channels)

campaign_options = sorted(campaigns_all[campaigns_all["channel"].isin(selected_channels)]["campaign_name"].unique())
selected_campaigns = st.sidebar.multiselect("Campaign", campaign_options, default=campaign_options)

st.sidebar.caption("The date and channel filters apply to all three datasets "
                   "(social media is filtered by platform, website traffic by source; "
                   "Organic, Direct and Referral traffic always stay). "
                   "The campaign filter applies to campaign data only.")

if len(date_range) != 2:
    st.info("Please pick an end date.")
    st.stop()
start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])

# "base" = filtered by channel/campaign only (the monthly report needs data from all dates)
camp_base = campaigns_all[campaigns_all["channel"].isin(selected_channels)
                          & campaigns_all["campaign_name"].isin(selected_campaigns)]
soc_base = social_all[social_all["platform"].isin(selected_channels)]
web_base = traffic_all[traffic_all["source"].isin(selected_channels) | ~traffic_all["source"].isin(PAID)]


def in_dates(df):
    return df[(df["date"] >= start_date) & (df["date"] <= end_date)]


campaigns = in_dates(camp_base)
social = in_dates(soc_base)
traffic = in_dates(web_base)

if campaigns.empty:
    st.warning("No campaign data for these filters. Try selecting more channels, campaigns or dates.")
    st.stop()

# tabs
tab_overview, tab_channels, tab_trends, tab_social, tab_web, tab_insights, tab_reports, tab_quality = st.tabs([
    "Overview", "Channels & Campaigns", "Trends & Patterns", "Social Media",
    "Website Traffic", "Insights", "Reports", "Data Quality"])

# tab 1: overview
with tab_overview:
    k = overall_kpis(campaigns)
    st.subheader("Campaign KPIs")
    kpi_row([("Total Spend", f"₹{k['spend']:,.0f}"),
             ("Total Revenue", f"₹{k['revenue']:,.0f}"),
             ("ROI", f"{k['roi']:.1f}%"),
             ("CTR", f"{k['ctr']:.2f}%"),
             ("Conversion Rate", f"{k['conversion_rate']:.2f}%")])
    kpi_row([("Impressions", f"{k['impressions']:,.0f}"),
             ("Clicks", f"{k['clicks']:,.0f}"),
             ("Conversions", f"{k['conversions']:,.0f}"),
             ("Cost per Acquisition", f"₹{k['cpa']:,.0f}"),
             ("Engagement Rate", f"{k['engagement_rate']:.2f}%")])
    kpi_row([("Total Reach", f"{k['reach']:,.0f}",
              "Sum of daily reach. The same person can be reached on several days, "
              "so this is not a count of unique people."),
             ("Cost per Click", f"₹{k['cpc']:,.2f}"),
             ("Likes + Shares + Comments", f"{k['likes'] + k['shares'] + k['comments']:,.0f}")])

    if len(social) > 0 and len(traffic) > 0:
        st.subheader("Social media and website at a glance")
        s = overall_social_kpis(social)
        w = overall_web_kpis(traffic)
        kpi_row([("Social Posts", f"{s['posts']:,.0f}"),
                 ("Social Engagement Rate", f"{s['engagement_rate']:.2f}%"),
                 ("New Followers", f"{s['new_followers']:,.0f}"),
                 ("Website Sessions", f"{w['sessions']:,.0f}"),
                 ("Bounce Rate", f"{w['bounce_rate']:.1f}%")])

    st.divider()
    ch = kpis_by(campaigns, "channel").sort_values("roi", ascending=False)
    left, right = st.columns(2)
    with left:
        st.markdown("**ROI by channel (%)**")
        fig = px.bar(ch, x="channel", y="roi", color="channel", color_discrete_map=COLORS,
                     text=ch["roi"].round(0))
        fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="ROI (%)")
        show(fig)
    with right:
        st.markdown("**Revenue share by channel**")
        fig = px.pie(ch, names="channel", values="revenue", hole=0.45,
                     color="channel", color_discrete_map=COLORS)
        show(fig)

    left, right = st.columns(2)
    with left:
        st.markdown("**Conversion funnel**")
        funnel_df = pd.DataFrame({"stage": ["Impressions", "Clicks", "Conversions"],
                                  "count": [k["impressions"], k["clicks"], k["conversions"]]})
        fig = px.funnel(funnel_df, x="count", y="stage")
        show(fig)
        st.caption(f"Only {k['ctr']:.2f}% of impressions become clicks, and "
                   f"{k['conversion_rate']:.2f}% of clicks become conversions.")
    with right:
        st.markdown("**Monthly spend vs revenue (₹)**")
        m = monthly_table(campaigns)
        m_long = m.melt(id_vars=["month_num", "month"], value_vars=["spend", "revenue"],
                        var_name="measure", value_name="amount")
        fig = px.line(m_long, x="month", y="amount", color="measure", markers=True)
        fig.update_layout(xaxis_title=None, yaxis_title="₹", legend_title=None)
        show(fig)

# tab 2: channels & campaigns
with tab_channels:
    st.subheader("Channel comparison")
    ch = kpis_by(campaigns, "channel").sort_values("roi", ascending=False)

    metric_options = {"ROI (%)": "roi", "CTR (%)": "ctr", "Conversion rate (%)": "conversion_rate",
                      "Cost per acquisition (₹)": "cpa", "Cost per click (₹)": "cpc",
                      "Engagement rate (%)": "engagement_rate"}
    chosen = st.selectbox("Compare channels by", list(metric_options.keys()))
    col_name = metric_options[chosen]
    fig = px.bar(ch.sort_values(col_name, ascending=False), x="channel", y=col_name, color="channel",
                 color_discrete_map=COLORS, text=ch.sort_values(col_name, ascending=False)[col_name].round(2))
    fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title=chosen)
    show(fig)

    table = ch[["channel", "spend", "revenue", "roi", "ctr", "conversion_rate", "cpc", "cpa", "engagement_rate"]].round(2)
    st.dataframe(table, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Campaign performance")
    camp = campaign_report(campaigns)

    left, right = st.columns(2)
    with left:
        st.markdown("**Campaigns ranked by ROI (%)**")
        ranked = camp.sort_values("roi")
        fig = px.bar(ranked, x="roi", y="campaign_name", color="channel", orientation="h",
                     color_discrete_map=COLORS)
        fig.update_layout(yaxis_title=None, xaxis_title="ROI (%)", legend_title=None)
        show(fig)
    with right:
        st.markdown("**Spend vs revenue (bubble size = conversions)**")
        fig = px.scatter(camp, x="spend", y="revenue", size="conversions", color="channel",
                         hover_name="campaign_name", color_discrete_map=COLORS)
        top = max(camp["spend"].max(), camp["revenue"].max())
        fig.add_shape(type="line", x0=0, y0=0, x1=top, y1=top, line=dict(dash="dash", color="grey"))
        fig.add_annotation(x=top * 0.9, y=top * 0.82, text="break-even", showarrow=False)
        fig.update_layout(xaxis_title="Spend (₹)", yaxis_title="Revenue (₹)", legend_title=None)
        show(fig)

    st.markdown("**Campaign table**")
    cols = ["campaign_name", "channel", "spend", "revenue", "roi", "ctr", "conversion_rate", "cpa", "engagement_rate"]
    st.dataframe(camp[cols], use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("From ad click to website visit")
    if len(traffic) > 0:
        funnel = channel_funnel(campaigns, traffic)
        if len(funnel) > 0:
            both = funnel.melt(id_vars="channel", value_vars=["clicks", "sessions"],
                               var_name="stage", value_name="count")
            fig = px.bar(both, x="channel", y="count", color="stage", barmode="group")
            fig.update_layout(xaxis_title=None, legend_title=None)
            show(fig)
            st.dataframe(funnel[["channel", "clicks", "sessions", "click_to_session_rate",
                                 "cost_per_session", "revenue_per_session",
                                 "session_conversion_rate"]].round(2),
                         use_container_width=True, hide_index=True)
            st.caption("Sessions are the website visits from each paid channel. "
                       "Click-to-session rate shows how many ad clicks actually reached the site.")
        else:
            st.info("Select at least one paid channel to see this.")
    else:
        st.info("No website data for these filters.")

# tab 3: trends & patterns
with tab_trends:
    st.subheader("Monthly trends")
    m = monthly_table(campaigns)
    m["revenue_growth"] = m["revenue"].pct_change() * 100

    left, right = st.columns(2)
    with left:
        st.markdown("**Monthly revenue (₹)**")
        fig = px.bar(m, x="month", y="revenue")
        fig.update_layout(xaxis_title=None, yaxis_title="₹")
        show(fig)
    with right:
        st.markdown("**Month-over-month revenue growth (%)**")
        growth = m.dropna(subset=["revenue_growth"])
        fig = px.bar(growth, x="month", y="revenue_growth", text=growth["revenue_growth"].round(1))
        fig.update_layout(xaxis_title=None, yaxis_title="Growth (%)")
        show(fig)

    st.markdown("**Monthly ROI (%)**")
    fig = px.line(m, x="month", y="roi", markers=True)
    fig.update_layout(xaxis_title=None, yaxis_title="ROI (%)")
    show(fig)

    st.divider()
    st.subheader("Patterns across channels")
    df = campaigns.copy()
    df["month_num"] = df["date"].dt.month
    g = df.groupby(["month_num", "channel"])[["spend", "revenue", "likes", "shares", "comments", "reach"]].sum()
    g["roi"] = (g["revenue"] - g["spend"]) / g["spend"] * 100
    g["engagement_rate"] = (g["likes"] + g["shares"] + g["comments"]) / g["reach"] * 100

    st.markdown("**ROI heatmap: month x channel (green = profitable, red = losing money)**")
    pivot = g["roi"].unstack("channel")
    pivot.index = [MONTH_NAMES[i - 1] for i in pivot.index]
    fig = px.imshow(pivot, text_auto=".0f", aspect="auto", color_continuous_scale="RdYlGn",
                    color_continuous_midpoint=0)
    fig.update_layout(xaxis_title=None, yaxis_title=None)
    show(fig)

    st.markdown("**Engagement rate trend by channel (%)**")
    eng = g["engagement_rate"].reset_index()
    eng["month"] = eng["month_num"].apply(lambda n: MONTH_NAMES[n - 1])
    fig = px.line(eng, x="month", y="engagement_rate", color="channel", markers=True,
                  color_discrete_map=COLORS)
    fig.update_layout(xaxis_title=None, yaxis_title="Engagement rate (%)", legend_title=None)
    show(fig)

    findings, recs = generate_insights(campaigns, social, traffic)
    if findings["Trends & patterns"]:
        st.markdown("**What the patterns say**")
        for line in findings["Trends & patterns"]:
            st.markdown(f"- {line}")

# tab 4: social media
with tab_social:
    if social.empty:
        st.info("No social media data for these filters. Select Instagram, Facebook or YouTube.")
    else:
        s = overall_social_kpis(social)
        st.subheader("Social media performance")
        kpi_row([("Posts", f"{s['posts']:,.0f}"),
                 ("Total Reach", f"{s['reach']:,.0f}"),
                 ("Engagement Rate", f"{s['engagement_rate']:.2f}%"),
                 ("Link CTR", f"{s['link_ctr']:.2f}%"),
                 ("New Followers", f"{s['new_followers']:,.0f}")])

        left, right = st.columns(2)
        with left:
            st.markdown("**Engagement rate by post type (%)**")
            types = social_kpis_by(social, ["platform", "post_type"])
            fig = px.bar(types, x="post_type", y="engagement_rate", color="platform",
                         barmode="group", color_discrete_map=COLORS)
            fig.update_layout(xaxis_title=None, yaxis_title="Engagement rate (%)", legend_title=None)
            show(fig)
        with right:
            st.markdown("**Monthly engagement rate by platform (%)**")
            sd = social.copy()
            sd["month_num"] = sd["date"].dt.month
            sg = sd.groupby(["month_num", "platform"])[["likes", "comments", "shares", "saves", "reach"]].sum().reset_index()
            sg["engagement_rate"] = (sg["likes"] + sg["comments"] + sg["shares"] + sg["saves"]) / sg["reach"] * 100
            sg["month"] = sg["month_num"].apply(lambda n: MONTH_NAMES[n - 1])
            fig = px.line(sg, x="month", y="engagement_rate", color="platform", markers=True,
                          color_discrete_map=COLORS)
            fig.update_layout(xaxis_title=None, yaxis_title="Engagement rate (%)", legend_title=None)
            show(fig)

        st.markdown("**Every post: reach vs engagement rate**")
        posts = social.copy()
        posts["engagement_rate"] = (posts["likes"] + posts["comments"] + posts["shares"] + posts["saves"]) / posts["reach"] * 100
        fig = px.scatter(posts, x="reach", y="engagement_rate", color="platform",
                         hover_data=["post_type", "date"], color_discrete_map=COLORS)
        fig.update_layout(xaxis_title="Reach", yaxis_title="Engagement rate (%)", legend_title=None)
        show(fig)

        st.markdown("**Platform summary**")
        plat = social_kpis_by(social, "platform")
        st.dataframe(plat[["platform", "posts", "reach", "engagement_rate", "share_rate", "save_rate",
                           "link_ctr", "follower_growth_rate", "avg_reach_per_post"]].round(2),
                     use_container_width=True, hide_index=True)

        st.markdown("**Top 10 posts by engagement rate**")
        top_posts = posts.sort_values("engagement_rate", ascending=False).head(10)
        top_posts = top_posts[["post_id", "date", "platform", "post_type", "reach", "likes",
                               "comments", "shares", "saves", "engagement_rate"]].copy()
        top_posts["engagement_rate"] = top_posts["engagement_rate"].round(2)
        top_posts["date"] = top_posts["date"].dt.date
        st.dataframe(top_posts, use_container_width=True, hide_index=True)

# tab 5: website traffic
with tab_web:
    if traffic.empty:
        st.info("No website data for these filters.")
    else:
        w = overall_web_kpis(traffic)
        st.subheader("Website traffic")
        kpi_row([("Sessions", f"{w['sessions']:,.0f}"),
                 ("Users", f"{w['users']:,.0f}"),
                 ("New User Share", f"{w['new_user_share']:.1f}%"),
                 ("Bounce Rate", f"{w['bounce_rate']:.1f}%"),
                 ("Avg Session (sec)", f"{w['avg_session_duration']:.0f}"),
                 ("Pages / Session", f"{w['pages_per_session']:.2f}")])

        st.markdown("**Monthly sessions by source**")
        td = traffic.copy()
        td["month_num"] = td["date"].dt.month
        tm = td.groupby(["month_num", "source"])["sessions"].sum().reset_index()
        tm["month"] = tm["month_num"].apply(lambda n: MONTH_NAMES[n - 1])
        fig = px.bar(tm, x="month", y="sessions", color="source", barmode="stack")
        fig.update_layout(xaxis_title=None, legend_title=None)
        show(fig)

        src = web_kpis_by(traffic, "source").sort_values("sessions", ascending=False)
        left, right = st.columns(2)
        with left:
            st.markdown("**Bounce rate by source (%)**")
            fig = px.bar(src.sort_values("bounce_rate"), x="source", y="bounce_rate", color="source",
                         color_discrete_map=COLORS, text=src.sort_values("bounce_rate")["bounce_rate"].round(0))
            fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Bounce rate (%)")
            show(fig)
        with right:
            st.markdown("**Average session duration by source (seconds)**")
            fig = px.bar(src.sort_values("avg_session_duration", ascending=False), x="source",
                         y="avg_session_duration", color="source", color_discrete_map=COLORS)
            fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Seconds")
            show(fig)

        st.markdown("**Traffic source summary**")
        st.dataframe(src.round(2), use_container_width=True, hide_index=True)

# tab 6: insights
with tab_insights:
    st.subheader("Business insights")
    st.caption("Generated automatically from the filtered data, so these change when you change the filters. "
               "They describe this synthetic dataset.")
    findings, recs = generate_insights(campaigns, social, traffic)
    for section, items in findings.items():
        if items:
            st.markdown(f"#### {section}")
            for line in items:
                st.markdown(f"- {line}")

    st.markdown("#### Recommendations")
    if recs:
        for number, line in enumerate(recs, 1):
            st.markdown(f"{number}. {line}")
    else:
        st.info("Select more channels or a longer date range to get recommendations.")

    st.download_button("Download insights (.md)", insights_text(campaigns, social, traffic),
                       file_name="insights.md", mime="text/markdown")

# tab 7: reports
with tab_reports:
    st.subheader("Report generation")
    report_type = st.radio("Choose a report", ["Campaign report", "Marketing summary", "Monthly analytics report"],
                           horizontal=True)

    if report_type == "Campaign report":
        st.caption("One row per campaign for the selected filters.")
        table = campaign_report(campaigns)
        st.dataframe(table, use_container_width=True, hide_index=True)
        st.download_button("Download Excel", to_excel_bytes({"Campaign report": table}),
                           file_name="campaign_report.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("Download CSV", table.to_csv(index=False),
                           file_name="campaign_report.csv", mime="text/csv")

    elif report_type == "Marketing summary":
        st.caption("Overall KPIs and the performance of every channel, platform and traffic source.")
        tables = marketing_summary(campaigns, social, traffic)
        for name, table in tables.items():
            st.markdown(f"**{name}**")
            st.dataframe(table, use_container_width=True, hide_index=True)
        st.download_button("Download Excel (all tables)", to_excel_bytes(tables),
                           file_name="marketing_summary.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    else:
        st.caption("Pick a month. The date filter is ignored here, the channel and campaign filters still apply.")
        months = sorted(camp_base["date"].dt.strftime("%Y-%m").unique())
        month = st.selectbox("Month", months, index=len(months) - 1)
        tables, summary = monthly_report(camp_base, soc_base, web_base, month)
        st.markdown(summary)
        for name, table in tables.items():
            st.markdown(f"**{name}**")
            st.dataframe(table, use_container_width=True, hide_index=True)
        st.download_button("Download Excel", to_excel_bytes(tables),
                           file_name=f"monthly_report_{month}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("Download summary (.md)", summary,
                           file_name=f"monthly_summary_{month}.md", mime="text/markdown")

# tab 8: data quality
with tab_quality:
    st.subheader("Data cleaning summary")
    st.write("Each dataset was created with deliberate quality problems and then cleaned "
             "with Pandas before being loaded into SQLite.")
    quality = load_quality_table()
    st.dataframe(quality, use_container_width=True, hide_index=True)

    melted = quality.melt(id_vars="Dataset", value_vars=["Raw rows", "Clean rows"],
                          var_name="Stage", value_name="Rows")
    fig = px.bar(melted, x="Dataset", y="Rows", color="Stage", barmode="group")
    fig.update_layout(xaxis_title=None, legend_title=None)
    show(fig)

    st.markdown("**Cleaning steps applied**")
    st.markdown("""
- Converted the date column to a real date type
- Standardised inconsistent channel, platform and source names (for example *insta*, *FB*, *Google_Ads*)
- Removed exact duplicate rows
- Filled missing numbers with the median of the same campaign, platform or source
- Removed impossible rows: negative spend, clicks above impressions, conversions above clicks,
  bounce rate above 100%, likes above reach
- Validated the result: no missing values and no duplicates remain
""")
    st.markdown("**Data model (SQLite: `marketing.db`)**")
    st.markdown("""
| Table | What it holds | Used for |
|---|---|---|
| `campaigns` | daily ad spend, impressions, clicks, conversions, revenue and engagement per campaign | ROI, CTR, conversion, CPA, trends |
| `social_media` | one row per social post with reach, likes, comments, shares, saves, link clicks | engagement and post-type analysis |
| `web_traffic` | daily sessions, bounce rate and session time per traffic source | website behaviour, ad-click-to-visit link |
""")
