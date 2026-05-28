import json
import re

# Input and output file paths
input_file = "bridal_makeup_vendors_rajasthan.json"
output_file = "bridal_makeup_vendors_rajasthan_data.json"

# Load JSON data
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# Regex pattern to match strings like "+3 more", "+10 more", etc.
pattern = re.compile(r"^\+\d+\s+more$")

# Process all items
for item in data:
    if "features" in item and isinstance(item["features"], list):
        item["features"] = [
            feature for feature in item["features"]
            if not pattern.match(feature.strip())
        ]

# Save cleaned data
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f"Cleaned data saved to {output_file}")