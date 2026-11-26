# generate_extra_data.py - creates the social media and website traffic datasets
# (Module 1: social media performance + website traffic data)
# run AFTER clean_data.py, from the project folder:  python src/generate_extra_data.py
# output: data/raw/social_media_raw.csv and data/raw/web_traffic_raw.csv

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)

# 1. WEBSITE TRAFFIC  (one row per day per traffic source)
# paid traffic is based on the real clicks from our campaign data,
# so the two datasets agree with each other
campaigns = pd.read_csv("data/cleaned/campaigns_clean.csv")
daily_clicks = campaigns.groupby(["date", "channel"])["clicks"].sum().reset_index()

# typical bounce rate (%) and session time (seconds) for each source
traffic_profile = {
    "Email":         (30, 210), "Google Ads":    (40, 170), "Facebook": (50, 130),
    "Instagram":     (55, 110), "YouTube":       (60, 150),
    "Organic Search": (45, 190), "Direct":       (35, 240), "Referral": (48, 160),
}

dates = pd.date_range("2025-01-01", "2025-12-31", freq="D")
traffic_rows = []

for d in dates:
    day = d.strftime("%Y-%m-%d")
    season = 1 + 0.2 * np.sin((d.dayofyear / 365) * 2 * np.pi)
    if d.month in (10, 11):
        season *= 1.25
    for source, (bounce0, duration0) in traffic_profile.items():
        if source in ["Email", "Google Ads", "Facebook", "Instagram", "YouTube"]:
            # paid traffic: about 80-95% of ad clicks turn into website sessions
            row = daily_clicks[(daily_clicks["date"] == day) & (daily_clicks["channel"] == source)]
            clicks = row["clicks"].sum()
            sessions = int(clicks * rng.uniform(0.80, 0.95))
        elif source == "Organic Search":
            sessions = int(3500 * season * rng.uniform(0.8, 1.2))
        elif source == "Direct":
            sessions = int(2200 * season * rng.uniform(0.8, 1.2))
        else:  # Referral
            sessions = int(900 * season * rng.uniform(0.7, 1.3))

        users = int(sessions * rng.uniform(0.72, 0.9))
        new_users = int(users * rng.uniform(0.4, 0.65))
        traffic_rows.append({
            "date": day,
            "source": source,
            "sessions": sessions,
            "users": users,
            "new_users": new_users,
            "bounce_rate": round(bounce0 * rng.uniform(0.9, 1.1), 1),
            "avg_session_duration": round(duration0 * rng.uniform(0.85, 1.15), 0),
            "pages_per_session": round(rng.uniform(1.6, 4.2), 2),
        })

traffic = pd.DataFrame(traffic_rows)

# add some mess (like the campaign data)
n = len(traffic)
# wrong spellings of the SAME source (so the cleaning step can fix them)
source_variants = {
    "Instagram": ["insta", "INSTAGRAM"], "Facebook": ["FB", "facebook "],
    "Google Ads": ["google_ads", "google ads"], "Email": ["email", "EMAIL"],
    "YouTube": ["yt", "youtube"], "Organic Search": ["organic search", "ORGANIC SEARCH"],
    "Direct": ["DIRECT", "direct"], "Referral": ["referral ", "REFERRAL"],
}
for idx in rng.choice(n, 150, replace=False):
    traffic.at[idx, "source"] = rng.choice(source_variants[traffic.at[idx, "source"]])
for col, k in [("sessions", 20), ("bounce_rate", 25), ("avg_session_duration", 20)]:
    traffic.loc[rng.choice(n, k, replace=False), col] = np.nan  # missing values
traffic.loc[rng.choice(n, 10, replace=False), "bounce_rate"] = 140  # impossible (>100%)
traffic = pd.concat([traffic, traffic.sample(30, random_state=2)], ignore_index=True)  # duplicates
traffic = traffic.sample(frac=1, random_state=3).reset_index(drop=True)
traffic.to_csv("data/raw/web_traffic_raw.csv", index=False)
print("Saved data/raw/web_traffic_raw.csv with", len(traffic), "rows")

# 2. social media performance  (one row per post)
# (post types, typical engagement rate per type, posts per week)
platforms = {
    "Instagram": (["Reel", "Carousel", "Image", "Story"], [0.075, 0.055, 0.035, 0.020], 5),
    "Facebook":  (["Video", "Image", "Link", "Text"],     [0.040, 0.025, 0.015, 0.012], 4),
    "YouTube":   (["Video", "Short", "Live"],             [0.050, 0.070, 0.045],        2),
}
base_reach = {"Instagram": 14000, "Facebook": 11000, "YouTube": 18000}

post_rows = []
post_number = 1
for platform, (types, eng_rates, per_week) in platforms.items():
    num_posts = int(52 * per_week)
    post_dates = np.sort(rng.choice(dates, num_posts, replace=True))
    for pdate in post_dates:
        t = rng.integers(0, len(types))
        month = pd.Timestamp(pdate).month
        growth = 1 + (month - 1) * 0.02  # audience slowly grows
        reach = int(base_reach[platform] * growth * rng.uniform(0.5, 1.6))
        impressions = int(reach * rng.uniform(1.1, 1.5))
        engagement = int(reach * eng_rates[t] * rng.uniform(0.7, 1.3))
        post_rows.append({
            "post_id": f"P{post_number:04d}",
            "date": pd.Timestamp(pdate).strftime("%Y-%m-%d"),
            "platform": platform,
            "post_type": types[t],
            "impressions": impressions,
            "reach": reach,
            "likes": int(engagement * 0.68),
            "comments": int(engagement * 0.12),
            "shares": int(engagement * 0.10),
            "saves": int(engagement * 0.10),
            "link_clicks": int(reach * rng.uniform(0.004, 0.02)),
            "new_followers": int(reach * rng.uniform(0.0005, 0.004)),
        })
        post_number += 1

social = pd.DataFrame(post_rows)

# add some mess
n = len(social)
platform_variants = {
    "Instagram": ["insta", "INSTAGRAM"], "Facebook": ["fb", "facebook "], "YouTube": ["youtube", "YT"],
}
for idx in rng.choice(n, 40, replace=False):
    social.at[idx, "platform"] = rng.choice(platform_variants[social.at[idx, "platform"]])
for col, k in [("likes", 12), ("reach", 8), ("shares", 10), ("link_clicks", 10)]:
    social.loc[rng.choice(n, k, replace=False), col] = np.nan
bad = rng.choice(n, 6, replace=False)
social.loc[bad, "likes"] = social.loc[bad, "reach"] * 2  # likes > reach: impossible
social = pd.concat([social, social.sample(12, random_state=5)], ignore_index=True)
social = social.sample(frac=1, random_state=9).reset_index(drop=True)
social.to_csv("data/raw/social_media_raw.csv", index=False)
print("Saved data/raw/social_media_raw.csv with", len(social), "rows")
