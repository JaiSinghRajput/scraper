import pandas as pd
import json

# File paths
INPUT_CSV = "gujarat_all.csv"
CITY_JSON = "gujarat_cities.json"
OUTPUT_CSV = "output.csv"
UNMATCHED_CSV = "unmatched_cities.csv"

# Load city JSON
with open(CITY_JSON, "r", encoding="utf-8") as f:
    cities = json.load(f)

# Create lookup
city_lookup = {
    city["name"].strip().lower(): city["id"]
    for city in cities
}

# Read CSV
df = pd.read_csv(INPUT_CSV, dtype=str)

# Fill vendor_city
df["vendor_city"] = df["vendor_city_name"].apply(
    lambda x: str(city_lookup.get(str(x).strip().lower(), ""))
    if pd.notna(x) else ""
)

# Split data
matched_df = df[df["vendor_city"] != ""]
unmatched_df = df[df["vendor_city"] == ""]

# Save files
matched_df.to_csv(OUTPUT_CSV, index=False)
unmatched_df.to_csv(UNMATCHED_CSV, index=False)

print(f"Matched rows: {len(matched_df)} -> {OUTPUT_CSV}")
print(f"Unmatched rows: {len(unmatched_df)} -> {UNMATCHED_CSV}")