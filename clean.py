import json
import re

# Input and output file paths
input_file = "final_data_raw/wedding-venues/uttar_pradesh/wedding_venues_uttar-pradesh_cards.json"
output_file = "final_data_raw/wedding-venues/uttar_pradesh/wedding_venues_uttar-pradesh_cards.json"

# Load JSON data
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# Regex pattern to match strings like "+3 more", "+10 more", etc.
pattern = re.compile(r"^\+\d+\s+more$")

# Process all items
for item in data:
    if "bottom_fields" in item and isinstance(item["bottom_fields"], list):
        item["bottom_fields"] = [
            feature for feature in item["bottom_fields"]
            if not pattern.match(feature.strip())
        ]

# Save cleaned data
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f"Cleaned data saved to {output_file}")