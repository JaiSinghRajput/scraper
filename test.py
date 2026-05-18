import json

# Path to your JSON file
file_path = "data.json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Count objects
if isinstance(data, list):
    count = len(data)
elif isinstance(data, dict):
    count = len(data.keys())
else:
    count = 1

print(f"Total objects: {count}")