# ============================================================
# IMPORTS
# ============================================================

import json
import argparse
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

OUTPUT_FILE = "vendors_extracted.json"


# ============================================================
# HELPERS
# ============================================================

def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def save_json(data, path):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


def safe_get(obj, *keys):

    current = obj

    for key in keys:

        if current is None:
            return None

        if isinstance(current, dict):

            current = current.get(key)

        else:
            return None

    return current


# ============================================================
# EXTRACT VENDOR
# ============================================================

def extract_vendor(item):

    state = item.get(
        "initial_state",
        {}
    )

    vendor = safe_get(
        state,
        "vendorProfile",
        "profile"
    )

    if not vendor:

        return None

    extracted = {

        # ================================================
        # BASIC
        # ================================================

        "url": item.get("url"),

        "vendor_id": vendor.get("id"),

        "member_id": vendor.get("member_id"),

        "name": vendor.get("name"),

        "slug": vendor.get("slug"),

        "category": vendor.get(
            "category_alias"
        ),

        "city": vendor.get("city"),

        "locality": vendor.get(
            "locality_name"
        ),

        "address": None,

        "pincode": None,

        "latitude": None,

        "longitude": None,

        # ================================================
        # CONTACT
        # ================================================

        "phones": vendor.get("phone", []),

        "whatsapp_number": vendor.get(
            "vendor_whatsapp_number"
        ),

        "email": vendor.get(
            "login_email"
        ),

        # ================================================
        # PRICING
        # ================================================

        "veg_price": None,

        "non_veg_price": None,

        "price_unit": vendor.get(
            "vendor_price_subtext"
        ),

        # ================================================
        # RATING
        # ================================================

        "rating": vendor.get(
            "vendor_rating"
        ),

        "reviews_count": None,

        "love_count": vendor.get(
            "love_count"
        ),

        # ================================================
        # VENUE DETAILS
        # ================================================

        "room_count": None,

        "guest_capacity": None,

        "venue_types": [],

        "spaces": None,

        "catering_policy": None,

        "decor_policy": None,

        "dj_policy": None,

        "alcohol_policy": None,

        "parking": None,
       

        # ================================================
        # DESCRIPTION
        # ================================================

        "about": vendor.get(
            "information"
        ),
        
        "area_available":vendor.get(
            "banquet"
        ),

        # ================================================
        # EXTRA
        # ================================================

        "membership": vendor.get(
            "membership"
        ),

        "badge_tooltip": vendor.get(
            "badge_tooltip"
        ),

        "verified": vendor.get(
            "vendor_verification_status"
        ),

        "wedsafe": vendor.get(
            "is_wedsafe"
        ),
    }

    # ====================================================
    # ADDRESS
    # ====================================================

    addresses = vendor.get(
        "address",
        []
    )

    if addresses:

        addr = addresses[0]

        extracted["address"] = (
            addr.get(
                "display_address"
            )
        )

        extracted["pincode"] = (
            addr.get("pincode")
        )

        extracted["latitude"] = (
            addr.get("latitude")
        )

        extracted["longitude"] = (
            addr.get("longitude")
        )

    # ====================================================
    # VENUE HIGHLIGHTS
    # ====================================================

    highlights = vendor.get(
        "vendor_highlights",
        {}
    )

    extracted["room_count"] = (
        highlights.get("room_count")
    )

    extracted["guest_capacity"] = (
        highlights.get("pax_count")
    )

    # ====================================================
    # VENUE TYPES
    # ====================================================

    faq_data = safe_get(
        state,
        "vendorProfile",
        "similar_vendors",
        "vendors"
    )

    if faq_data and isinstance(
        faq_data,
        list
    ):

        pass

    # ====================================================
    # FAQ EXTRACTION
    # ====================================================

    faqs = safe_get(
        state,
        "vendorProfile",
        "faq"
    )

    if faqs:

        for faq in faqs:

            question = (
                faq.get("question", "")
                .lower()
                .strip()
            )

            answer = faq.get(
                "answer"
            )

            if not answer:
                continue

            if "room count" in question:

                extracted[
                    "room_count"
                ] = answer

            elif "space" in question:

                extracted[
                    "spaces"
                ] = answer

            elif "catering" in question:

                extracted[
                    "catering_policy"
                ] = answer

            elif "decor" in question:

                extracted[
                    "decor_policy"
                ] = answer

            elif "dj" in question:

                extracted[
                    "dj_policy"
                ] = answer

            elif "alcohol" in question:

                extracted[
                    "alcohol_policy"
                ] = answer

            elif "parking" in question:

                extracted[
                    "parking"
                ] = answer

    # ====================================================
    # PRICING
    # ====================================================

    pricing = safe_get(
        state,
        "vendorProfile",
        "pricing"
    )

    if pricing:

        for item in pricing:

            label = (
                item.get("label", "")
                .lower()
            )

            price = item.get("price")

            if "veg" in label:

                extracted[
                    "veg_price"
                ] = price

            elif "non veg" in label:

                extracted[
                    "non_veg_price"
                ] = price

    # ====================================================
    # REVIEWS COUNT
    # ====================================================

    reviews = safe_get(
        state,
        "collapsibleReviews",
        "reviews"
    )

    if reviews:

        extracted["reviews_count"] = (
            len(reviews)
        )

    # ====================================================
    # VENUE TYPES
    # ====================================================

    venue_types = []

    faq_cards = safe_get(
        state,
        "vendorProfile",
        "similar_vendors",
        "vendors"
    )

    if faq_cards:

        for v in faq_cards:

            if (
                v.get("member_id")
                == vendor.get(
                    "member_id"
                )
            ):

                venue_types = v.get(
                    "venue_type",
                    []
                )

                break

    extracted["venue_types"] = (
        venue_types
    )

    return extracted


# ============================================================
# MAIN
# ============================================================

def run(input_file, output_file):

    raw = load_json(input_file)

    results = []

    for idx, item in enumerate(
        raw,
        start=1
    ):

        try:

            vendor = extract_vendor(
                item
            )

            if vendor:

                results.append(
                    vendor
                )

                print(
                    f"[{idx}] "
                    f"Extracted: "
                    f"{vendor['name']}"
                )

        except Exception as e:

            print(
                f"[{idx}] ERROR: {e}"
            )

    save_json(
        results,
        output_file
    )

    print("\n================================")
    print("DONE")
    print(
        f"Saved: {output_file}"
    )
    print(
        f"Total Vendors: "
        f"{len(results)}"
    )
    print("================================")


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        help="initial state json file"
    )

    parser.add_argument(
        "-o",
        "--output",
        default=OUTPUT_FILE
    )

    args = parser.parse_args()

    run(
        args.input,
        args.output
    )


if __name__ == "__main__":

    main()