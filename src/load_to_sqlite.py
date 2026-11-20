# load_to_sqlite.py - put the cleaned data into a SQLite database
# run from the project folder:  python src/load_to_sqlite.py

import sqlite3
import pandas as pd

# read the cleaned csv
df = pd.read_csv("data/cleaned/campaigns_clean.csv")
print("Rows in csv:", len(df))

# connect to the database (this creates marketing.db if it doesn't exist)
conn = sqlite3.connect("marketing.db")

# write the dataframe into a table called 'campaigns'
# if_exists="replace" means running this again won't create duplicates
df.to_sql("campaigns", conn, if_exists="replace", index=False)

# test it: ask the database how many rows it has
result = pd.read_sql("SELECT COUNT(*) AS total_rows FROM campaigns", conn)
print("Rows in database:", result["total_rows"][0])

# another test: total spend and revenue for each channel using SQL
query = """
SELECT channel,
       ROUND(SUM(spend), 2)   AS total_spend,
       ROUND(SUM(revenue), 2) AS total_revenue
FROM campaigns
GROUP BY channel
ORDER BY total_revenue DESC
"""
print(pd.read_sql(query, conn))

conn.close()
print("Done! marketing.db is ready.")
