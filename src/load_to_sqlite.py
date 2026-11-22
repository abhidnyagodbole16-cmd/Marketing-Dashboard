# load_to_sqlite.py - put all the cleaned data into one SQLite database
# run from the project folder:  python src/load_to_sqlite.py

import sqlite3
import pandas as pd

# connect to the database (this creates marketing.db if it doesn't exist)
conn = sqlite3.connect("marketing.db")

# table name -> cleaned csv file
tables = {
    "campaigns": "data/cleaned/campaigns_clean.csv",
    "social_media": "data/cleaned/social_media_clean.csv",
    "web_traffic": "data/cleaned/web_traffic_clean.csv",
}

for table_name, csv_file in tables.items():
    df = pd.read_csv(csv_file)
    # if_exists="replace" means running this again won't create duplicates
    df.to_sql(table_name, conn, if_exists="replace", index=False)

    # test: count the rows that ended up in the database
    count = pd.read_sql(f"SELECT COUNT(*) AS n FROM {table_name}", conn)["n"][0]
    print(f"{table_name}: {len(df)} rows in csv, {count} rows in database")

# test with SQL: spend and revenue per channel
query = """
SELECT channel,
       ROUND(SUM(spend), 2)   AS total_spend,
       ROUND(SUM(revenue), 2) AS total_revenue
FROM campaigns
GROUP BY channel
ORDER BY total_revenue DESC
"""
print(pd.read_sql(query, conn))

# test with SQL: sessions per traffic source
query = """
SELECT source, SUM(sessions) AS total_sessions, ROUND(AVG(bounce_rate), 1) AS avg_bounce_rate
FROM web_traffic
GROUP BY source
ORDER BY total_sessions DESC
"""
print(pd.read_sql(query, conn))

# test with SQL: average post reach by post type
query = """
SELECT platform, post_type, COUNT(*) AS posts, ROUND(AVG(reach)) AS avg_reach
FROM social_media
GROUP BY platform, post_type
ORDER BY platform, avg_reach DESC
"""
print(pd.read_sql(query, conn))

conn.close()
print("Done! marketing.db is ready.")
