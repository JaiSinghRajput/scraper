import json
import csv
import re

# =========================================================
# INPUT / OUTPUT FILES
# =========================================================

DETAIL_JSON_FILE = "scraped_data.json"
LISTING_JSON_FILE = "wedding_venues_jodhpur_cards.json"

OUTPUT_FILE = "final_jodhpur.csv"


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

    vendor_name = item.get("vendor_name", "").strip()

    if vendor_name:
        listing_lookup[vendor_name] = item


# =========================================================
# FIND MAX BANQUETS
# =========================================================

max_banquets = 0

for vendor in detail_vendors:

    banquet_count = len(
        safe_get(
            vendor,
            "vendorProfile",
            "banquet",
            default=[]
        )
    )

    max_banquets = max(
        max_banquets,
        banquet_count
    )

print(f"Max banquet spaces found: {max_banquets}")


# =========================================================
# CSV HEADERS
# =========================================================

headers = [

    "vendor_name",
    "vendor_category",
    "vendor_state",
    "vendor_area",
    "vendor_city",
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
# DYNAMIC EVENT SPACE HEADERS
# =========================================================

for i in range(1, max_banquets + 1):

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

    vendor_name = profile.get("name", "").strip()

    # -----------------------------------------------------
    # MATCH LISTING DATA
    # -----------------------------------------------------

    listing_vendor = listing_lookup.get(
        vendor_name,
        {}
    )

    # -----------------------------------------------------
    # DETAIL DATA
    # -----------------------------------------------------

    address = safe_get(
        vp,
        "activeAddress",
        default={}
    )

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
    # PRIORITY:
    # LISTING JSON -> DETAIL JSON
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
    # SMALL PARTY
    # -----------------------------------------------------

    small_party = "No"

    for b in banquet:

        seating = b.get(
            "fixed_capacity",
            0
        )

        if seating and seating <= 150:

            small_party = "Yes"

            break

    # -----------------------------------------------------
    # CONTACT INFO
    # -----------------------------------------------------

    phones = profile.get("phone", [])

    contact_info = ""

    if isinstance(phones, list) and len(phones) > 0:

        phone = str(phones[0])

    elif isinstance(phones, str):

        phone = phones

    else:

        phone = ""

    # -----------------------------------
    # CLEAN PHONE
    # -----------------------------------

    # remove spaces
    phone = re.sub(r"\s+", "", phone)

    # remove commas if any
    phone = phone.split(",")[0]

    # remove +91 only at beginning
    phone = re.sub(r"^\+91", "", phone)

    # remove single leading 0
    if phone.startswith("0"):
        phone = phone[1:]

    contact_info = phone

    # -----------------------------------------------------
    # FALLBACK VALUES FROM LISTING JSON
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

    vendor_city = (
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

        "vendor_state": 83,

        "vendor_area": vendor_area,

        "vendor_city": 2037,

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

        # EXTRA LISTING FIELDS

        "vendor_rating": (
            profile.get("vendor_rating")
            or listing_vendor.get(
                "rating",
                ""
            )
        ),

        "vendor_reviews": listing_vendor.get(
            "reviews",
            ""
        ),

        "vendor_tag": listing_vendor.get(
            "type",
            ""
        ),

        "vendor_url": listing_vendor.get(
            "url",
            ""
        ),

        "no_of_rooms": no_of_rooms,

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

        # STATIC POLICIES

        "parking_policy": parking_policy,

        "catering_policy": catering_policy,

        "decor_policy": decor_policy,

        "dj_policy": dj_policy,

        "alcohol_policy": alcohol_policy,
    }

    # -----------------------------------------------------
    # DYNAMIC EVENT SPACES
    # -----------------------------------------------------

    for idx, space in enumerate(
        banquet,
        start=1
    ):

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