import json
import argparse

# =========================================================
# ARGUMENTS
# =========================================================

parser = argparse.ArgumentParser(
    description="Count total objects in a JSON file"
)

parser.add_argument(
    "file_path",
    help="Path to JSON file"
)

args = parser.parse_args()

# =========================================================
# LOAD JSON
# =========================================================

with open(args.file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# =========================================================
# COUNT OBJECTS
# =========================================================

if isinstance(data, list):

    count = len(data)

elif isinstance(data, dict):

    count = len(data.keys())

else:

    count = 1

# =========================================================
# OUTPUT
# =========================================================

print(f"Total objects: {count}")