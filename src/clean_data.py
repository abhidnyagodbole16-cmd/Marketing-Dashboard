# clean_data.py - cleaning the raw marketing data
# run from the project folder:  python src/clean_data.py

import pandas as pd

# load the raw data
df = pd.read_csv("data/raw/campaigns_raw.csv")
print("Rows at start:", len(df))
print("Missing values at start:", df.isna().sum().sum())

# keep a copy of the starting row count for the report
start_rows = len(df)

# step 1: fix the date column
df["date"] = pd.to_datetime(df["date"])

# step 2: fix the channel names
# the raw data has things like 'insta', 'FB', 'Google_Ads'
# first make everything lowercase and remove extra spaces
df["channel"] = df["channel"].str.strip().str.lower()

# then replace each wrong name with the right one
df["channel"] = df["channel"].replace({
    "insta": "instagram",
    "fb": "facebook",
    "google_ads": "google ads",
    "googleads": "google ads",
    "e-mail": "email",
    "yt": "youtube",
})

# make them look nice again (Instagram, Google Ads...)
df["channel"] = df["channel"].str.title()
df["channel"] = df["channel"].replace({"Youtube": "YouTube"})

print("\nChannels now:", df["channel"].unique())

# step 3: remove duplicate rows
before = len(df)
df = df.drop_duplicates()
print("\nDuplicates removed:", before - len(df))

# step 4: fill missing values
# I fill each missing number with the median of that campaign
# (median is better than mean because a few big values won't change it much)
number_columns = ["spend", "impressions", "clicks", "conversions",
                  "revenue", "likes", "shares", "comments", "reach"]

print("Missing values filled:", df[number_columns].isna().sum().sum())

for col in number_columns:
    df[col] = df[col].fillna(df.groupby("campaign_name")[col].transform("median"))

# step 5: remove rows that make no sense
# spend can't be negative
before = len(df)
df = df[df["spend"] >= 0]
print("Negative spend rows removed:", before - len(df))

# clicks can't be more than impressions
before = len(df)
df = df[df["clicks"] <= df["impressions"]]
print("Clicks > impressions rows removed:", before - len(df))

# conversions can't be more than clicks
before = len(df)
df = df[df["conversions"] <= df["clicks"]]
print("Conversions > clicks rows removed:", before - len(df))

# step 6: final touches
# after filling, some count columns became decimals, so make them whole numbers
whole_columns = ["impressions", "clicks", "conversions", "likes", "shares", "comments", "reach"]
df[whole_columns] = df[whole_columns].round().astype(int)

# sort by date and reset the row numbers
df = df.sort_values("date")
df = df.reset_index(drop=True)

# step 7: check that everything is fine
print("\nMissing values left:", df.isna().sum().sum())
print("Duplicates left:", df.duplicated().sum())

# save the cleaned file
df.to_csv("data/cleaned/campaigns_clean.csv", index=False)
print("\nRows at start:", start_rows)
print("Rows at end:", len(df))
print("Saved to data/cleaned/campaigns_clean.csv")
