import json
import re
from copy import deepcopy


# =========================================================
# HELPERS
# =========================================================

def clean_text(value):

    if not value:
        return ""

    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)

    return value


def unique_list(values):

    seen = set()
    result = []

    for val in values:

        val = clean_text(val)

        if val and val.lower() not in seen:
            seen.add(val.lower())
            result.append(val)

    return result


def merge_values(primary, secondary):

    if primary in [None, "", [], {}]:
        return secondary

    return primary


def normalize_to_list(data):

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return [data]

    return []


def normalize_name(name):

    return clean_text(name).lower()


# =========================================================
# EXTRACT DATA FROM DETAILED FILE
# =========================================================
def extract_from_file2(file2):

    vendor_profile = (
        file2.get("initial_state", {})
        .get("vendorProfile", {})
        .get("profile", {})
    )

    faq = (
        file2.get("initial_state", {})
        .get("vendorProfile", {})
        .get("faq", [])
    )

    pricing_data = (
        file2.get("initial_state", {})
        .get("vendorProfile", {})
        .get("pricing", [])
    )

    extracted = {}

    # =====================================================
    # BASIC INFO
    # =====================================================

    address_data = vendor_profile.get("address", [])

    full_address = ""

    if address_data:
        full_address = address_data[0].get(
            "display_address",
            ""
        )

    reviews = (
        file2.get("initial_state", {})
        .get("collapsibleReviews", {})
        .get("reviews", [])
    )

    extracted["basic_info"] = {
        "url": file2.get("url", ""),
        "name": vendor_profile.get("name", ""),
        "formerly_known_as": "",
        "location": vendor_profile.get(
            "locality_name",
            ""
        ),
        "address": clean_text(full_address),
        "rating": str(
            vendor_profile.get(
                "vendor_rating",
                ""
            )
        ),
        "review_count": str(len(reviews)),
        "venue_type": (
            vendor_profile.get(
                "vendor_highlights",
                {}
            ).get(
                "vendor_highlight_text",
                ""
            )
        ),
        "contact_no": (
            vendor_profile.get(
                "vendor_whatsapp_number",
                ""
            )
        ),
        "photo_url": vendor_profile.get(
            "profile_pic_url",
            ""
        ),
        "maps_url": ""
    }

    # =====================================================
    # PRICING
    # =====================================================

    veg_price = ""
    non_veg_price = ""

    for item in pricing_data:

        label = item.get(
            "label",
            ""
        ).lower()

        if "veg" in label and "non" not in label:
            veg_price = item.get("price")

        if "non veg" in label:
            non_veg_price = item.get("price")

    extracted["pricing"] = {
        "room_price": "",
        "starting_decor_price": "",
        "veg_price_per_plate": clean_text(
            veg_price
        ).replace(",", ""),
        "non_veg_price_per_plate": clean_text(
            non_veg_price
        ).replace(",", ""),
        "destination_price": "",
        "destination_details": ""
    }

    # =====================================================
    # VENUE AREAS
    # =====================================================

    extracted["venue_areas"] = []

    # =====================================================
    # POLICIES
    # =====================================================

    policies = {
        "space_types": "",
        "on_wedmegood_since": "WedMeGood",
        "room_count": "",
        "catering_policy": "",
        "decor_policy": "",
        "started_in": "",
        "alcohol_policy": "",
        "dj_policy": ""
    }

    for item in faq:

        question = item.get(
            "question",
            ""
        ).lower()

        answer = clean_text(
            item.get("answer", "")
        )

        if "space" in question:
            policies["space_types"] = answer

        elif "room count" in question:
            policies["room_count"] = answer

        elif "catering" in question:
            policies["catering_policy"] = answer

        elif "decor" in question:
            policies["decor_policy"] = answer

        elif "alcohol" in question:
            policies["alcohol_policy"] = answer

        elif "dj" in question:
            policies["dj_policy"] = answer

    extracted["policies"] = policies

    # =====================================================
    # ABOUT
    # =====================================================

    extracted["about"] = clean_text(
        vendor_profile.get(
            "information",
            ""
        )
    )

    # =====================================================
    # IMAGES
    # =====================================================

    images = []

    cover_images = vendor_profile.get(
        "cover_images",
        []
    )

    portfolio_images = vendor_profile.get(
        "portfolio_images",
        []
    )

    images.extend(cover_images)
    images.extend(portfolio_images)

    extracted["images"] = unique_list(images)

    return extracted

# =========================================================
# MERGE SINGLE OBJECT
# =========================================================

def merge_json(file1, file2):

    extracted2 = extract_from_file2(file2)

    final_data = deepcopy(file1)

    for key, value in extracted2.items():

        # =================================================
        # PRICING
        # =================================================

        if key == "pricing":

            if "pricing" not in final_data:
                final_data["pricing"] = {}

            for p_key, p_val in value.items():

                final_data["pricing"][p_key] = (
                    merge_values(
                        final_data["pricing"].get(p_key),
                        p_val
                    )
                )

        # =================================================
        # ADDRESS
        # =================================================

        elif key == "address":

            if "address" not in final_data:
                final_data["address"] = {}

            for a_key, a_val in value.items():

                final_data["address"][a_key] = (
                    merge_values(
                        final_data["address"].get(a_key),
                        a_val
                    )
                )

        # =================================================
        # LISTS
        # =================================================

        elif key == "bottom_fields":

            combined = (
                final_data.get(
                    "bottom_fields",
                    []
                ) + value
            )

            final_data["bottom_fields"] = (
                unique_list(combined)
            )

        # =================================================
        # NORMAL VALUES
        # =================================================

        else:

            final_data[key] = merge_values(
                final_data.get(key),
                value
            )

    return final_data


# =========================================================
# LOAD FILES
# =========================================================

with open(
    "wedding_venues_jodhpur_cards.json",
    "r",
    encoding="utf-8"
) as f:

    file1_data = json.load(f)

with open(
    "jodhpur_detailed.json",
    "r",
    encoding="utf-8"
) as f:

    file2_data = json.load(f)

# =========================================================
# NORMALIZE TO LIST
# =========================================================

file1_list = normalize_to_list(file1_data)
file2_list = normalize_to_list(file2_data)

# =========================================================
# CREATE LOOKUP MAP
# =========================================================

file2_map = {}

for item in file2_list:

    try:

        vendor_profile = (
            item.get("initial_state", {})
            .get("vendorProfile", {})
            .get("profile", {})
        )

        vendor_name = normalize_name(
            vendor_profile.get("name", "")
        )

        if vendor_name:
            file2_map[vendor_name] = item

    except Exception:
        pass

# =========================================================
# MERGE ALL MATCHING OBJECTS
# =========================================================

final_output = []

for file1_item in file1_list:

    vendor_name = normalize_name(
        file1_item.get("vendor_name", "")
    )

    matched_file2 = file2_map.get(vendor_name)

    if matched_file2:

        merged = merge_json(
            file1_item,
            matched_file2
        )

        final_output.append(merged)

    else:

        # no match found
        final_output.append(file1_item)

# =========================================================
# SAVE FINAL OUTPUT
# =========================================================

with open(
    "final_output.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        final_output,
        f,
        indent=4,
        ensure_ascii=False
    )

print(
    f"final_output.json created successfully "
    f"with {len(final_output)} objects"
)