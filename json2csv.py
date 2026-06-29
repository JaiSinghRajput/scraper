import json
import pandas as pd
import argparse

CITY_ALIASES = {
    "gurgaon": "gurugram",
    "bangalore": "bengaluru",
    "bombay": "mumbai",
    "calcutta": "kolkata",
    "madras": "chennai",
    "delhi ncr": "delhi",
}

STATE_ALIASES = {
    "orissa": "odisha",
    "uttaranchal": "uttarakhand",
}

def normalize_name(name, aliases=None):
    if not name:
        return ""

    name = name.strip().lower()

    if aliases:
        name = aliases.get(name, name)

    return name

def flatten_json(obj, parent_key=""):
    """
    Flatten nested dicts/lists into columns.
    Skip None values to avoid useless columns.
    """

    items = {}

    if isinstance(obj, dict):
        for k, v in obj.items():

            if v is None:
                continue

            new_key = (
                f"{parent_key}_{k}"
                if parent_key
                else k
            )

            items.update(
                flatten_json(v, new_key)
            )

    elif isinstance(obj, list):

        if not obj:
            return items

        for i, item in enumerate(obj):
            new_key = f"{parent_key}_{i}"

            items.update(
                flatten_json(
                    item,
                    new_key,
                )
            )

    else:
        items[parent_key] = obj

    return items


def add_map_url(record):
    """
    Convert lat/long to map_url and
    remove lat/long fields.
    """

    vendor = record.get(
        "VendorProfile",
        {},
    )

    profile = vendor.get(
        "profile",
        {},
    )

    addresses = profile.get(
        "addresses",
        [],
    )

    if not addresses:
        return record

    for address in addresses:

        lat = address.get("lat")
        lng = address.get("long")

        if lat and lng:

            record["map_url"] = (
                f"https://www.google.com/maps?q="
                f"{lat},{lng}"
            )

        address.pop("lat", None)
        address.pop("long", None)

    return record


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
        help="Input JSON file",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output CSV file",
    )
    parser.add_argument(
    "--cities",
    required=True,
    help="Cities JSON file",
    )
    parser.add_argument(
        "--states",
        required=True,
        help="States JSON file",
    )

    args = parser.parse_args()

    with open(
        args.input,
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)
        
    with open(
    args.cities,
    "r",
    encoding="utf-8",
    ) as f:
        cities = json.load(f)

    with open(
        args.states,
        "r",
        encoding="utf-8",
    ) as f:
        states = json.load(f)

    city_map = {
        normalize_name(city["name"], CITY_ALIASES): city
            for city in cities
    }

    state_map = {
        normalize_name(state["state"], STATE_ALIASES): state
        for state in states
    }

    rows = []

    for record in data:

        record = add_map_url(record)

        flattened = flatten_json(
            record
        )

        vendor = record.get(
            "VendorProfile",
            {}
        )

        profile = vendor.get(
            "profile",
            {}
        )

        city_obj = None

        # --------------------
        # Match profile.city
        # --------------------

        city_name = normalize_name(
        profile.get("city", ""),
        CITY_ALIASES,
    )

    if city_name:
        city_obj = city_map.get(city_name)

        # --------------------
        # Fallback to address
        # --------------------

        if not city_obj:

            address = ""

            addresses = profile.get(
                "addresses",
                [],
            )

            if addresses:

                address = (
                    addresses[0]
                    .get(
                        "display_address",
                        "",
                    )
                    .lower()
                )

            for (
                lookup_city,
                lookup_obj,
            ) in city_map.items():

                if lookup_city in address:
                    city_obj = lookup_obj
                    break

        # --------------------
        # Fill IDs
        # --------------------

        if city_obj:

            flattened[
                "vendor_city"
            ] = city_obj["id"]

            state_obj = state_map.get(
                city_obj[
                    "state_name"
                ]
                .strip()
                .lower()
            )

            if state_obj:

                flattened[
                    "vendor_state"
                ] = state_obj["id"]

        rows.append(flattened)

    df = pd.DataFrame(rows)

    # Remove columns that are completely empty
    df = df.dropna(
        axis=1,
        how="all",
    )

    # Remove columns that became empty strings everywhere
    empty_cols = []

    for col in df.columns:

        values = (
            df[col]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        if (values == "").all():
            empty_cols.append(col)

    if empty_cols:
        df = df.drop(
            columns=empty_cols
        )
    priority_cols = [
    "VendorProfile_vendorSlug",
    "VendorProfile_profile_name",
    "vendor_state",
    "vendor_city",
]

    priority_cols = [
        col
        for col in priority_cols
        if col in df.columns
    ]

    remaining_cols = [
        col
        for col in df.columns
        if col not in priority_cols
    ]

    df = df[
        priority_cols + remaining_cols
    ]

    df.to_csv(
        args.output,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"Exported {len(df)} records"
    )
    print(
        f"Generated {len(df.columns)} columns"
    )
    print(
        f"Saved CSV to {args.output}"
    )


if __name__ == "__main__":
    main()