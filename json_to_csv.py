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
    required=False,
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

def build_google_map(lat, lng):

    if not lat or not lng:
        return ""

    return f"https://www.google.com/maps?q={lat},{lng}"

def normalize(text):

    if not text:
        return ""

    return re.sub(
        r"[^a-z0-9 ]",
        "",
        str(text).lower()
    ).strip()

def clean_price(value):

    if not value:
        return ""

    value = str(value)

    match = re.search(
        r"[\d,]+",
        value
    )

    if not match:
        return ""

    return match.group(0).replace(",", "")
    

def extract_price_fields(vp, faq_map):

    result = {
        "per_room_price": "",
        "venue_rental_price": "",
        "starting_decor_price": "",
        "veg_price": "",
        "nonveg_price": "",
        "destination_price": "",
    }

    # ----------------------------------
    # pricing[]
    # ----------------------------------

    for item in vp.get("pricing", []):

        question = normalize(
            item.get("question", "")
        )

        price = clean_price(item.get("price", ""))

        if "rental" in question:

            result["venue_rental_price"] = price

        elif "veg" in question:

            result["veg_price"] = price

        elif ("nonveg" in question or "non veg" in question):
            result["nonveg_price"] = price

    # ----------------------------------
    # price_faq[]
    # ----------------------------------

    for item in vp.get("price_faq", []):

        question = normalize(
            item.get("question", "")
        )

        answer = clean_price(item.get("answer", ""))

        if "decor" in question:

            result["starting_decor_price"] = answer

        elif any(
            keyword in question
            for keyword in [
                "room price",
                "room tariff",
                "room rent",
                "room cost",
                "per room"
            ]
        ):

            result["per_room_price"] = answer

        elif "destination" in question:

            result["destination_price"] = answer

    # ----------------------------------
    # fallback veg/nonveg from faq
    # ----------------------------------

    if not result["veg_price"]:
        result["veg_price"] = clean_price(faq_map.get("veg price",""))

    if not result["nonveg_price"]:result["nonveg_price"] = clean_price(faq_map.get("non veg price",""))
    return result


def extract_venue_start_year(profile, faq_map):

    start_text = faq_map.get(
        "start of venue",
        ""
    )

    match = re.search(
        r"(\d{4})",
        str(start_text)
    )

    if match:

        return match.group(1)

    information = profile.get(
        "information",
        ""
    )

    match = re.search(r"(?:since|started in|established in)\s+(\d{4})",information,re.IGNORECASE)

    if match:

        return match.group(1)

    return ""

def clean_rooms(room_text):

    if not room_text:
        return ""

    match = re.search(r"(\d+)", str(room_text))

    return match.group(1) if match else room_text


# =========================================================
# PHONE HELPERS
# =========================================================


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
    "venue_rental_price",
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

        question = normalize(item.get("question",""))

        faq_map[question] = item.get(
            "answer",
            ""
        )
    price_fields = extract_price_fields(
    vp,
    faq_map
)

    # -----------------------------------------------------
    # PROPERTY TYPE
    # -----------------------------------------------------
    property_type = listing_vendor.get(
    "venue_type",
    []
    )

    if isinstance(
        property_type,
        list
    ):

        property_type = ", ".join(
            property_type
        )

    elif property_type is None:

        property_type = ""

    if not property_type:

        venue_types = profile.get(
            "venue_type",
            []
        )

        if isinstance(
            venue_types,
            list
        ):

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

    contact_info = ( valid_phones[0] if valid_phones else "")
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

    price_fields["veg_price"]

    or vp.get("veg_price")

    or safe_get(
        listing_vendor,
        "pricing",
        "veg_per_plate",
        default=""
    )
)

    nonveg_price = (

    price_fields["nonveg_price"]

    or vp.get("nonveg_price")

    or safe_get(
        listing_vendor,
        "pricing",
        "non_veg_per_plate",
        default=""
    )
)

    no_of_rooms = (

    clean_rooms(
        safe_get(
            profile,
            "vendor_highlights",
            "room_count",
            default=""
        )
    )

    or clean_rooms(
        faq_map.get(
            "how many rooms are available in your accomodation?",
            ""
        )
    )

    or clean_rooms(
        listing_vendor.get(
            "rooms",
            ""
        )
    )
)

    # -----------------------------------------------------
    # POLICIES
    # -----------------------------------------------------

    parking_policy = faq_map.get("parking","")

    if not parking_policy:

        info = profile.get(
            "information",
            ""
        ).lower()

        if "parking" in info:
            parking_policy = (
                "There is sufficient parking available"
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
    veg_price_clean = str(veg_price).replace(",", "").strip()
    rental_price_clean = str(
        price_fields["venue_rental_price"]
    ).replace(",", "").strip()

    if (
        veg_price_clean
        and rental_price_clean
        and veg_price_clean == rental_price_clean
    ):
        veg_price = ""

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

        "venue_start_year":
    extract_venue_start_year(
        profile,
        faq_map
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

        "per_room_price": price_fields["per_room_price"],

        "starting_decor_price": price_fields["starting_decor_price"],

        "veg_price_per_plate": veg_price,

        "nonveg_price_per_plate": nonveg_price,
        "venue_rental_price": price_fields["venue_rental_price"],
        
        "destination_price": price_fields["destination_price"] or vp.get("destination_price",""),

        "destination_details": " ".join(filter(None,[vp.get("destination_price_incl_text",""),vp.get("destination_price_unit","")])),

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
    banquet = sorted(
    banquet,
    key=lambda x: (
        x.get(
            "floating_capacity",
            0
        ) or 0
    ),
    reverse=True
    )
    
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
