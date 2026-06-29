import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

with open(args.input, "r", encoding="utf-8") as f:
    data = json.load(f)

filtered = []

removed = 0

for item in data:
    vendor = item.get("vendorProfile") or {}

    profile = vendor.get("profile")

    if profile is None:
        removed += 1
        continue

    filtered.append(item)

with open(args.output, "w", encoding="utf-8") as f:
    json.dump(
        filtered,
        f,
        ensure_ascii=False,
        indent=2
    )

print(f"Original records: {len(data)}")
print(f"Removed records : {removed}")
print(f"Remaining records: {len(filtered)}")