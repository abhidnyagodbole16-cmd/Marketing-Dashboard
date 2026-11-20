# check_kpis.py - test that the KPI numbers are correct
# run from the project folder:  python src/check_kpis.py

import sqlite3
import pandas as pd
from kpis import kpis_by, overall_kpis

# read the data from the database
conn = sqlite3.connect("marketing.db")
df = pd.read_sql("SELECT * FROM campaigns", conn)
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
