import json
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Filter cities by state slug and generate a new JSON file."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="State slug to filter (e.g. rajasthan)",
    )
    parser.add_argument(
        "--source",
        default="cities.json",
        help="Source JSON file (default: cities.json)",
    )

    args = parser.parse_args()

    state_slug = args.input.strip().lower()

    with open(args.source, "r", encoding="utf-8") as f:
        data = json.load(f)

    filtered = [
        item
        for item in data
        if item.get("state_slug", "").lower() == state_slug
    ]

    output_file = f"{state_slug}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    print(
        f"✓ Generated {output_file} with {len(filtered)} records"
    )


if __name__ == "__main__":
    main()