import json
import csv
import re
import argparse

# =========================================================
# ARGUMENTS
# =========================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--detail_json",
    required=True,
    help="Detail JSON file"
)

parser.add_argument(
    "--listing_json",
    required=True,
    help="Listing JSON file"
)

parser.add_argument(
    "--output_csv",
    required=True,
    help="Output CSV file"
)

parser.add_argument(
    "--vendor_state",
    required=True,
    help="Vendor state ID"
)

parser.add_argument(
    "--vendor_city",
    required=True,
    help="Vendor city ID"
)


args = parser.parse_args()

DETAIL_JSON_FILE = args.detail_json
LISTING_JSON_FILE = args.listing_json
OUTPUT_FILE = args.output_csv
VENDOR_STATE = args.vendor_state
VENDOR_CITY = args.vendor_city


# =========================================================
# HELPERS
# =========================================================

def safe_get(obj, *keys, default=None):

    for key in keys:

        if obj is None:
            return default

        if isinstance(obj, list):

            try:
                key = int(key)
                obj = obj[key]

            except:
                return default

        elif isinstance(obj, dict):

            obj = obj.get(key)

        else:
            return default

    return obj if obj is not None else default


def extract_year(text):

    if not text:
        return ""

    match = re.search(
        r"since\s+(\d{4})",
        text,
        re.IGNORECASE
    )

    return match.group(1) if match else ""


def build_google_map(lat, lng):

    if not lat or not lng:
        return ""

    return f"https://www.google.com/maps?q={lat},{lng}"


def clean_rooms(room_text):

    if not room_text:
        return ""

    match = re.search(r"(\d+)", str(room_text))

    return match.group(1) if match else room_text


# =========================================================
# PHONE HELPERS
# =========================================================

used_phone_numbers = set()


def extract_valid_phones(phone_data):

    """
    Extract all valid 10-digit Indian mobile numbers
    """

    candidates = []

    # normalize input
    if isinstance(phone_data, list):

        raw_phones = phone_data

    elif isinstance(phone_data, str):

        raw_phones = [phone_data]

    else:

        raw_phones = []

    for raw in raw_phones:

        if not raw:
            continue

        # split multiple numbers
        parts = str(raw).split(",")

        for part in parts:

            # keep digits only
            cleaned = re.sub(r"\D", "", part)

            # remove country code
            if cleaned.startswith("91") and len(cleaned) > 10:

                cleaned = cleaned[-10:]

            # remove leading zero
            if cleaned.startswith("0") and len(cleaned) > 10:

                cleaned = cleaned[-10:]

            # validate 10 digit number
            if len(cleaned) == 10:

                candidates.append(cleaned)

    # remove duplicates preserving order
    unique_candidates = []

    for phone in candidates:

        if phone not in unique_candidates:

            unique_candidates.append(phone)

    return unique_candidates


def select_best_phone(phone_list):

    """
    Rules:
    1. Prefer unused phone
    2. If all duplicated -> use first valid
    """

    if not phone_list:
        return ""

    # prefer unique phone
    for phone in phone_list:

        if phone not in used_phone_numbers:

            used_phone_numbers.add(phone)

            return phone

    # fallback duplicate
    return phone_list[0]


# =========================================================
# LOAD DETAIL JSON
# =========================================================

with open(DETAIL_JSON_FILE, "r", encoding="utf-8") as f:

    detail_data = json.load(f)

detail_vendors = (
    detail_data
    if isinstance(detail_data, list)
    else [detail_data]
)


# =========================================================
# LOAD LISTING JSON
# =========================================================

with open(LISTING_JSON_FILE, "r", encoding="utf-8") as f:

    listing_data = json.load(f)

listing_vendors = (
    listing_data
    if isinstance(listing_data, list)
    else [listing_data]
)


# =========================================================
# BUILD LISTING LOOKUP
# =========================================================

listing_lookup = {}

for item in listing_vendors:

    vendor_name = item.get(
        "vendor_name",
        ""
    ).strip()

    if vendor_name:

        listing_lookup[vendor_name] = item


# =========================================================
# FIXED EVENT SPACES
# =========================================================

MAX_EVENT_SPACES = 17


# =========================================================
# CSV HEADERS
# =========================================================

headers = [

    "vendor_name",
    "vendor_category",
    "vendor_state",
    "vendor_area",
    "vendor_city",
    "vendor_city_name",
    "property_type",
    "venue_start_year",
    "vendor_address",
    "vendor_contact_info",
    "vendor_google_map",
    "no_of_rooms",
    "per_room_price",
    "starting_decor_price",
    "veg_price_per_plate",
    "nonveg_price_per_plate",
    "destination_price",
    "destination_details",
    "small_party_venue",
    "space_available",

    "parking_policy",
    "catering_policy",
    "decor_policy",
    "dj_policy",
    "alcohol_policy",
]


# =========================================================
# EVENT SPACE HEADERS
# =========================================================

for i in range(1, MAX_EVENT_SPACES + 1):

    headers.extend([

        f"event_space_name_{i}",
        f"event_space_type_{i}",
        f"seating_guests_{i}",
        f"floating_guests_{i}",

    ])


# =========================================================
# BUILD ROWS
# =========================================================

rows = []

for vendor in detail_vendors:

    vp = safe_get(
        vendor,
        "vendorProfile",
        default={}
    )

    profile = safe_get(
        vp,
        "profile",
        default={}
    )

    vendor_name = profile.get(
        "name",
        ""
    ).strip()

    # -----------------------------------------------------
    # MATCH LISTING DATA
    # -----------------------------------------------------

    listing_vendor = listing_lookup.get(
        vendor_name,
        {}
    )

    # -----------------------------------------------------
    # ADDRESS
    # -----------------------------------------------------

    address_list = profile.get(
        "address",
        []
    )

    address = {}

    if isinstance(address_list, list) and len(address_list) > 0:

        address = address_list[0]

    # -----------------------------------------------------
    # FAQ / BANQUET
    # -----------------------------------------------------

    faq = safe_get(
        vp,
        "faq",
        default=[]
    )

    banquet = safe_get(
        vp,
        "banquet",
        default=[]
    )

    # -----------------------------------------------------
    # FAQ MAP
    # -----------------------------------------------------

    faq_map = {}

    for item in faq:

        question = item.get(
            "question",
            ""
        ).lower()

        faq_map[question] = item.get(
            "answer",
            ""
        )

    # -----------------------------------------------------
    # PROPERTY TYPE
    # -----------------------------------------------------

    property_type = listing_vendor.get(
        "venue_type",
        ""
    )

    if not property_type:

        venue_types = profile.get(
            "venue_type",
            []
        )

        if isinstance(venue_types, list):

            property_type = ", ".join(
                venue_types
            )

    # -----------------------------------------------------
    # SMALL PARTY VENUE
    # -----------------------------------------------------

    small_party = faq_map.get(
        "small party venue",
        ""
    )

    # -----------------------------------------------------
    # CONTACT INFO
    # -----------------------------------------------------

    phones = profile.get(
        "phone",
        []
    )

    valid_phones = extract_valid_phones(
        phones
    )

    contact_info = select_best_phone(
        valid_phones
    )

    # -----------------------------------------------------
    # FALLBACK VALUES
    # -----------------------------------------------------

    vendor_area = (

        profile.get("locality_name")

        or safe_get(
            listing_vendor,
            "address",
            "area",
            default=""
        )
    )

    vendor_city_name = (

        profile.get("city")

        or safe_get(
            listing_vendor,
            "address",
            "city",
            default=""
        )
    )

    veg_price = (

        vp.get("veg_price")

        or safe_get(
            listing_vendor,
            "pricing",
            "veg_per_plate",
            default=""
        )
    )

    nonveg_price = (

        vp.get("nonveg_price")

        or safe_get(
            listing_vendor,
            "pricing",
            "non_veg_per_plate",
            default=""
        )
    )

    no_of_rooms = (

        faq_map.get("room count")

        or clean_rooms(
            listing_vendor.get("rooms", "")
        )
    )

    # -----------------------------------------------------
    # POLICIES
    # -----------------------------------------------------

    parking_policy = faq_map.get(
        "parking",
        ""
    )

    catering_policy = faq_map.get(
        "catering policy",
        ""
    )

    decor_policy = faq_map.get(
        "decor policy",
        ""
    )

    dj_policy = faq_map.get(
        "dj policy",
        ""
    )

    alcohol_policy = faq_map.get(
        "outside alcohol",
        ""
    )

    # -----------------------------------------------------
    # ROW
    # -----------------------------------------------------

    row = {

        "vendor_name": vendor_name,

        "vendor_category": profile.get(
            "category_alias",
            ""
        ),

        "vendor_state": VENDOR_STATE,

        "vendor_area": vendor_area,

        "vendor_city": VENDOR_CITY,

        "vendor_city_name": str(
            vendor_city_name
        ).strip(),

        "property_type": property_type,

        "venue_start_year": extract_year(
            profile.get(
                "information",
                ""
            )
        ),

        "vendor_address": address.get(
            "display_address",
            ""
        ),

        "vendor_contact_info": contact_info,

        "vendor_google_map": build_google_map(
            address.get("latitude"),
            address.get("longitude"),
        ),

        "no_of_rooms": str(
            no_of_rooms
        ).replace("Rooms", "").strip(),

        "per_room_price": safe_get(
            vp,
            "price_faq",
            0,
            "answer",
            default=""
        ),

        "starting_decor_price": safe_get(
            vp,
            "price_faq",
            1,
            "answer",
            default=""
        ),

        "veg_price_per_plate": veg_price,

        "nonveg_price_per_plate": nonveg_price,

        "destination_price": vp.get(
            "destination_price",
            ""
        ),

        "destination_details":
            f"{vp.get('destination_price_incl_text', '')} "
            f"{vp.get('destination_price_unit', '')}",

        "small_party_venue": small_party,

        "space_available": faq_map.get(
            "space",
            ""
        ),

        "parking_policy": parking_policy,

        "catering_policy": catering_policy,

        "decor_policy": decor_policy,

        "dj_policy": dj_policy,

        "alcohol_policy": alcohol_policy,
    }

    # -----------------------------------------------------
    # EVENT SPACES
    # -----------------------------------------------------

    for idx, space in enumerate(
        banquet,
        start=1
    ):

        if idx > MAX_EVENT_SPACES:
            break

        row[f"event_space_name_{idx}"] = space.get(
            "title",
            ""
        )

        row[f"event_space_type_{idx}"] = space.get(
            "indoor_outdoor_text",
            ""
        )

        row[f"seating_guests_{idx}"] = space.get(
            "fixed_capacity",
            ""
        )

        row[f"floating_guests_{idx}"] = space.get(
            "floating_capacity",
            ""
        )

    rows.append(row)


# =========================================================
# WRITE CSV
# =========================================================

with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as csvfile:

    writer = csv.DictWriter(
        csvfile,
        fieldnames=headers,
        extrasaction="ignore"
    )

    writer.writeheader()

    for row in rows:

        writer.writerow(row)

print(
    f"\nCSV generated successfully: {OUTPUT_FILE}"
)
