import json


def format_indian_number(num):
    """Format a number using the Indian numbering system."""
    num = int(num)
    sign = "-" if num < 0 else ""
    num = str(abs(num))

    if len(num) <= 3:
        return sign + num

    last_three = num[-3:]
    remaining = num[:-3]

    parts = []
    while len(remaining) > 2:
        parts.insert(0, remaining[-2:])
        remaining = remaining[:-2]

    if remaining:
        parts.insert(0, remaining)

    return sign + ",".join(parts + [last_three])


def format_pricing(vendors):
    """Format all numeric prices in VendorProfile.pricing."""
    for vendor in vendors:
        pricing = vendor.get("VendorProfile", {}).get("pricing", [])

        for item in pricing:
            price = item.get("price")

            if isinstance(price, (int, float)):
                item["price"] = format_indian_number(price)

    return vendors


if __name__ == "__main__":
    # Read list of vendor objects
    with open("step_1_c.json", "r", encoding="utf-8") as f:
        vendors = json.load(f)

    # Format pricing
    vendors = format_pricing(vendors)

    # Write output
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(vendors, f, indent=2, ensure_ascii=False)

    print(f"Done! Processed {len(vendors)} vendor(s).")