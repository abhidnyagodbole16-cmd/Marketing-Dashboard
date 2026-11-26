# Generate a messy marketing dataset (Module 1: data collection).
# Run from the project root:  python src/generate_data.py
# Output: data/raw/campaigns_raw.csv
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

# campaign -> channel, plus how that channel tends to behave
CAMPAIGNS = {
    "Summer Sale": "Instagram", "Festive Offer": "Instagram", "Influencer Push": "Instagram",
    "Retargeting Wave": "Facebook", "Lead Gen Form": "Facebook",
    "Brand Search": "Google Ads", "Competitor Keywords": "Google Ads", "Shopping Ads": "Google Ads",
    "Welcome Series": "Email", "Cart Recovery": "Email",
    "Product Demo Video": "YouTube", "Brand Story": "YouTube",
}
# (daily spend, cost per click, CTR, conversion rate, revenue per conversion, engagement rate)
# ROI works out to roughly: conversion_rate * revenue_per_conversion / cost_per_click - 1
PROFILE = {
    "Instagram":  (4000, 12, 0.018, 0.020, 1800, 0.060),
    "Facebook":   (3500, 15, 0.012, 0.025, 1500, 0.030),
    "Google Ads": (5000, 30, 0.045, 0.060, 1800, 0.010),
    "Email":      (800,  15, 0.030, 0.070, 1500, 0.020),
    "YouTube":    (3000, 20, 0.008, 0.015, 1600, 0.040),
}

dates = pd.date_range("2025-01-01", "2025-12-31", freq="D")
rows = []
for name, channel in CAMPAIGNS.items():
    spend0, cpc0, ctr0, cvr0, rpc, eng0 = PROFILE[channel]
    # every campaign is a bit better or worse than its channel average
    cpc_c = cpc0 * rng.uniform(0.8, 1.2)
    cvr_c = cvr0 * rng.uniform(0.8, 1.2)
    for d in dates:
        season = 1 + 0.25 * np.sin((d.dayofyear / 365) * 2 * np.pi)  # seasonality
        if d.month in (10, 11):  # festive boost
            season *= 1.3
        spend = spend0 * rng.uniform(0.7, 1.3) * season
        clicks = int(spend / (cpc_c * rng.uniform(0.85, 1.15)))
        impressions = int(clicks / (ctr0 * rng.uniform(0.85, 1.15)))
        conversions = int(clicks * cvr_c * rng.uniform(0.6, 1.4))
        revenue = conversions * rpc * rng.uniform(0.8, 1.2)
        reach = int(impressions * rng.uniform(0.55, 0.8))
        engagement = reach * eng0 * rng.uniform(0.7, 1.3)
        rows.append({
            "date": d.strftime("%Y-%m-%d"), "campaign_name": name, "channel": channel,
            "spend": round(spend, 2), "impressions": impressions, "clicks": clicks,
            "conversions": conversions, "revenue": round(revenue, 2),
            "likes": int(engagement * 0.7), "shares": int(engagement * 0.1),
            "comments": int(engagement * 0.2), "reach": reach,
        })

df = pd.DataFrame(rows)

# add deliberate mess so there is real cleaning to do
n = len(df)

# 1) inconsistent channel names
variants = {"Instagram": ["insta", "INSTAGRAM", "Instagram "], "Facebook": ["facebook", "FB"],
            "Google Ads": ["google ads", "Google_Ads", "GoogleAds"], "Email": ["email", "E-mail"],
            "YouTube": ["youtube", "Youtube", "YT"]}
for idx in rng.choice(n, 400, replace=False):
    ch = df.at[idx, "channel"]
    df.at[idx, "channel"] = rng.choice(variants[ch])

# 2) missing values
for col, k in [("spend", 60), ("impressions", 50), ("clicks", 70), ("conversions", 40),
               ("revenue", 50), ("likes", 80), ("reach", 40)]:
    df.loc[rng.choice(n, k, replace=False), col] = np.nan

# 3) impossible values
df.loc[rng.choice(n, 15, replace=False), "spend"] = -abs(df["spend"].mean())  # negative spend
bad = rng.choice(n, 20, replace=False)
df.loc[bad, "clicks"] = df.loc[bad, "impressions"] + 500  # clicks > impressions

# 4) duplicate rows
df = pd.concat([df, df.sample(80, random_state=1)], ignore_index=True)

df = df.sample(frac=1, random_state=7).reset_index(drop=True)  # shuffle
df.to_csv("data/raw/campaigns_raw.csv", index=False)
print(f"Saved data/raw/campaigns_raw.csv with {len(df)} rows")
