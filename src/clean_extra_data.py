# clean_extra_data.py - cleaning the social media and website traffic data
# run from the project folder:  python src/clean_extra_data.py

import pandas as pd

# part 1: website traffic
print("Website traffic")
traffic = pd.read_csv("data/raw/web_traffic_raw.csv")
print("Rows at start:", len(traffic))
print("Missing values at start:", traffic.isna().sum().sum())

# fix the date
traffic["date"] = pd.to_datetime(traffic["date"])

# fix the source names
traffic["source"] = traffic["source"].str.strip().str.lower()
traffic["source"] = traffic["source"].replace({
    "insta": "instagram",
    "fb": "facebook",
    "google_ads": "google ads",
    "yt": "youtube",
})
traffic["source"] = traffic["source"].str.title()
traffic["source"] = traffic["source"].replace({"Youtube": "YouTube"})
print("Sources now:", traffic["source"].unique())

# remove duplicates
before = len(traffic)
traffic = traffic.drop_duplicates()
print("Duplicates removed:", before - len(traffic))

# bounce rate is a percentage, so it can't be more than 100
before = len(traffic)
traffic = traffic[traffic["bounce_rate"].isna() | (traffic["bounce_rate"] <= 100)]
print("Rows with bounce rate > 100 removed:", before - len(traffic))

# fill missing values with the median of that source
number_columns = ["sessions", "users", "new_users", "bounce_rate",
                  "avg_session_duration", "pages_per_session"]
print("Missing values filled:", traffic[number_columns].isna().sum().sum())
for col in number_columns:
    traffic[col] = traffic[col].fillna(traffic.groupby("source")[col].transform("median"))

# sessions and users are counts, so make them whole numbers
traffic[["sessions", "users", "new_users"]] = traffic[["sessions", "users", "new_users"]].round().astype(int)

traffic = traffic.sort_values(["date", "source"]).reset_index(drop=True)
print("Missing values left:", traffic.isna().sum().sum())
print("Duplicates left:", traffic.duplicated().sum())
print("Rows at end:", len(traffic))
traffic.to_csv("data/cleaned/web_traffic_clean.csv", index=False)

# part 2: social media
print("\nSocial media")
social = pd.read_csv("data/raw/social_media_raw.csv")
print("Rows at start:", len(social))
print("Missing values at start:", social.isna().sum().sum())

social["date"] = pd.to_datetime(social["date"])

# fix the platform names
social["platform"] = social["platform"].str.strip().str.lower()
social["platform"] = social["platform"].replace({
    "insta": "instagram",
    "fb": "facebook",
    "yt": "youtube",
})
social["platform"] = social["platform"].str.title()
social["platform"] = social["platform"].replace({"Youtube": "YouTube"})
print("Platforms now:", social["platform"].unique())

# remove duplicates
before = len(social)
social = social.drop_duplicates()
print("Duplicates removed:", before - len(social))

# fill missing values with the median of that platform
number_columns = ["impressions", "reach", "likes", "comments", "shares",
                  "saves", "link_clicks", "new_followers"]
print("Missing values filled:", social[number_columns].isna().sum().sum())
for col in number_columns:
    social[col] = social[col].fillna(social.groupby("platform")[col].transform("median"))

# likes can't be more than the people reached
before = len(social)
social = social[social["likes"] <= social["reach"]]
print("Rows with likes > reach removed:", before - len(social))

social[number_columns] = social[number_columns].round().astype(int)
social = social.sort_values("date").reset_index(drop=True)
print("Missing values left:", social.isna().sum().sum())
print("Duplicates left:", social.duplicated().sum())
print("Rows at end:", len(social))
social.to_csv("data/cleaned/social_media_clean.csv", index=False)

print("\nSaved both cleaned files in data/cleaned/")
