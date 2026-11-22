# check_kpis.py - test that the KPI numbers are correct
# run from the project folder:  python src/check_kpis.py

import sqlite3
import pandas as pd
from kpis import (kpis_by, overall_kpis, social_kpis_by, overall_social_kpis,
                  web_kpis_by, overall_web_kpis, channel_funnel)

# read the data from the database
conn = sqlite3.connect("marketing.db")
df = pd.read_sql("SELECT * FROM campaigns", conn)
social = pd.read_sql("SELECT * FROM social_media", conn)
traffic = pd.read_sql("SELECT * FROM web_traffic", conn)
conn.close()

# ---- 1. KPIs by channel ----
print("KPIs by channel:")
by_channel = kpis_by(df, "channel")
print(by_channel[["channel", "ctr", "conversion_rate", "cpa", "roi", "engagement_rate"]].round(2))

# ---- 2. overall KPIs ----
total = overall_kpis(df)
print("\nOverall KPIs:")
print("Total spend:", round(total["spend"], 2))
print("Total revenue:", round(total["revenue"], 2))
print("ROI %:", round(total["roi"], 2))
print("CTR %:", round(total["ctr"], 2))
print("Conversion rate %:", round(total["conversion_rate"], 2))

# ---- 3. hand check for one channel (calculated without kpis.py) ----
print("\nHand check for Email:")
email = df[df["channel"] == "Email"]
spend = email["spend"].sum()
revenue = email["revenue"].sum()
clicks = email["clicks"].sum()
impressions = email["impressions"].sum()

my_roi = (revenue - spend) / spend * 100
my_ctr = clicks / impressions * 100
print("My ROI:", round(my_roi, 2), "| function ROI:", round(by_channel[by_channel["channel"] == "Email"]["roi"].iloc[0], 2))
print("My CTR:", round(my_ctr, 2), "| function CTR:", round(by_channel[by_channel["channel"] == "Email"]["ctr"].iloc[0], 2))

# ---- 4. automatic checks (the program stops with an error if something is wrong) ----
assert abs(my_roi - by_channel[by_channel["channel"] == "Email"]["roi"].iloc[0]) < 0.001
assert abs(my_ctr - by_channel[by_channel["channel"] == "Email"]["ctr"].iloc[0]) < 0.001
assert (by_channel["ctr"] <= 100).all()
assert (by_channel["conversion_rate"] <= 100).all()
print("\nAll checks passed!")


# =====================================================================
# SOCIAL MEDIA CHECKS
# =====================================================================
print("\n--- Social media KPIs by platform ---")
by_platform = social_kpis_by(social, "platform")
print(by_platform[["platform", "posts", "engagement_rate", "save_rate", "link_ctr", "follower_growth_rate"]].round(2))

# hand check for Instagram
insta = social[social["platform"] == "Instagram"]
my_eng = (insta["likes"].sum() + insta["comments"].sum() + insta["shares"].sum() + insta["saves"].sum()) / insta["reach"].sum() * 100
func_eng = by_platform[by_platform["platform"] == "Instagram"]["engagement_rate"].iloc[0]
print("Instagram engagement rate -> mine:", round(my_eng, 3), "| function:", round(func_eng, 3))
assert abs(my_eng - func_eng) < 0.001
assert (by_platform["engagement_rate"] < 100).all()

# the platform totals must add up to the overall total
overall_social = overall_social_kpis(social)
assert overall_social["posts"] == by_platform["posts"].sum()
assert abs(overall_social["reach"] - by_platform["reach"].sum()) < 1

# =====================================================================
# WEBSITE TRAFFIC CHECKS
# =====================================================================
print("\n--- Website KPIs by source ---")
by_source = web_kpis_by(traffic, "source")
print(by_source[["source", "sessions", "bounce_rate", "avg_session_duration", "pages_per_session"]].round(2))

# hand check for Email bounce rate (weighted by sessions)
em = traffic[traffic["source"] == "Email"]
my_bounce = (em["sessions"] * em["bounce_rate"]).sum() / em["sessions"].sum()
func_bounce = by_source[by_source["source"] == "Email"]["bounce_rate"].iloc[0]
print("Email bounce rate -> mine:", round(my_bounce, 3), "| function:", round(func_bounce, 3))
assert abs(my_bounce - func_bounce) < 0.001
assert (by_source["bounce_rate"] <= 100).all()
assert overall_web_kpis(traffic)["sessions"] == traffic["sessions"].sum()

# =====================================================================
# CROSS-DATASET CHECK (ad clicks vs website sessions)
# =====================================================================
print("\n--- Ads vs website, per channel ---")
funnel = channel_funnel(df, traffic)
print(funnel[["channel", "clicks", "sessions", "click_to_session_rate", "cost_per_session", "revenue_per_session"]].round(2))
# paid-channel sessions were built as 80-95% of clicks, so this should be in that range
assert funnel["click_to_session_rate"].between(78, 97).all()

print("\nAll extra checks passed!")
