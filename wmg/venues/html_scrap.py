# =========================================================
# CONFIG
# =========================================================

INPUT_HTML_FILE = "deta/wedding-venues_jaipur.html"
OUTPUT_JSON_FILE = "wedding_venues_jaipur.json"

BASE_URL = "https://www.wedmegood.com"


# =========================================================
# IMPORTS
# =========================================================

from bs4 import BeautifulSoup
import json
import re


# =========================================================
# HELPERS
# =========================================================

def clean_text(text):

    if not text:
        return None

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_price(text):

    if not text:
        return None

    text = (
        text
        .replace("₹", "")
        .replace(",", "")
        .strip()
    )

    return text


# =========================================================
# LOAD HTML
# =========================================================

with open(INPUT_HTML_FILE, "r", encoding="utf-8") as f:

    html = f.read()

soup = BeautifulSoup(html, "html.parser")


# =========================================================
# FIND CARDS
# =========================================================

cards = soup.select('div[id^="card"]')

print(f"Found cards: {len(cards)}")

results = []


# =========================================================
# PARSE
# =========================================================

for index, card in enumerate(cards):

    try:

        data = {
            "vendor_name": None,

            "address": {
                "area": None,
                "city": None
            },

            "venue_type": None,

            "pricing": {
                "veg_per_plate": None,
                "non_veg_per_plate": None
            },

            "rating": None,
            "reviews": None,

            "capacity": None,
            "rooms": None,

            "about_preview": None,

            "bottom_fields": [],

            "type": None,

            "url": None
        }

        # =================================================
        # VENDOR NAME
        # =================================================

        vendor_tag = card.select_one(
            "a.vendor-detail.text-bold.h6"
        )

        if vendor_tag:

            data["vendor_name"] = clean_text(
                vendor_tag.get_text()
            )

        # =================================================
        # URL
        # =================================================

        profile_link = card.select_one(
            'a[href*="/wedding-venues/"]'
        )

        if profile_link:

            href = profile_link.get("href")

            if href:

                if href.startswith("http"):

                    data["url"] = href

                else:

                    data["url"] = BASE_URL + href

        # =================================================
        # RATING
        # =================================================

        rating_tag = card.select_one(
            ".StarRatingNew"
        )

        if rating_tag:

            rating_text = clean_text(
                rating_tag.get_text()
            )

            if rating_text:

                rating_text = (
                    rating_text
                    .replace("★", "")
                    .strip()
                )

                data["rating"] = rating_text

        # =================================================
        # REVIEWS
        # =================================================

        review_tag = card.select_one(
            ".review-cnt"
        )

        if review_tag:

            data["reviews"] = clean_text(
                review_tag.get_text()
            )

        # =================================================
        # ADDRESS
        # =================================================

        location_block = card.select(
            ".info-icon.text-tertiary.frow"
        )

        if location_block:

            first_location = location_block[0]

            location_text = clean_text(
                first_location.get_text(
                    " ",
                    strip=True
                )
            )

            if location_text:

                location_parts = [
                    x.strip()
                    for x in location_text.split(",")
                    if x.strip()
                ]

                if len(location_parts) >= 1:

                    data["address"]["area"] = (
                        location_parts[0]
                    )

                if len(location_parts) >= 2:

                    data["address"]["city"] = (
                        location_parts[-1]
                    )

        # =================================================
        # VENUE TYPE
        # =================================================

        venue_type_tag = card.select_one(
            '.info-icon img[alt="Venue"]'
        )

        if venue_type_tag:

            parent = venue_type_tag.find_parent(
                class_="info-icon"
            )

            if parent:

                type_p = parent.select_one("p")

                if type_p:

                    data["venue_type"] = clean_text(
                        type_p.get_text()
                    )

        # =================================================
        # VEG / NON VEG PRICE
        # =================================================

        veg_block = card.select_one(
            ".vendor-price"
        )

        if veg_block:

            price_tags = veg_block.select(
                ".text-bold"
            )

            # VEG
            if len(price_tags) >= 1:

                veg_price = clean_text(
                    price_tags[0].get_text()
                )

                if veg_price:

                    data["pricing"][
                        "veg_per_plate"
                    ] = clean_price(
                        veg_price
                    )

            # NON VEG
            if len(price_tags) >= 2:

                non_veg_price = clean_text(
                    price_tags[1].get_text()
                )

                if non_veg_price:

                    data["pricing"][
                        "non_veg_per_plate"
                    ] = clean_price(
                        non_veg_price
                    )

        # =================================================
        # ABOUT PREVIEW
        # =================================================

        tooltip_blocks = card.select(
            ".__react_component_tooltip"
        )

        for tip in tooltip_blocks:

            text = clean_text(
                tip.get_text(
                    " ",
                    strip=True
                )
            )

            if (
                text
                and "About venue" in text
            ):

                text = (
                    text
                    .replace(
                        "About venue",
                        ""
                    )
                    .strip()
                )

                data["about_preview"] = text

                break

        # =================================================
        # BOTTOM FIELDS
        # =================================================

        bottom_fields = []

        # Visible chips
        chip_ps = card.select(
            '.v-center.margin-10 > div > p'
        )

        for p in chip_ps:

            txt = clean_text(
                p.get_text()
            )

            if not txt:
                continue

            # Skip "+4 more"
            if "+more" in txt.lower():
                continue

            bottom_fields.append(txt)

        # Hidden tooltip chips
        tooltip_lists = card.select(
            'div[id$="tooltop"] li'
        )

        for li in tooltip_lists:

            txt = clean_text(
                li.get_text()
            )

            if not txt:
                continue

            bottom_fields.append(txt)

        # Remove duplicates
        bottom_fields = list(
            dict.fromkeys(bottom_fields)
        )

        data["bottom_fields"] = (
            bottom_fields
        )

        # =================================================
        # STRUCTURED EXTRACTION
        # =================================================

        for txt in bottom_fields:

            lower_txt = txt.lower()

            # Capacity
            if "pax" in lower_txt:

                data["capacity"] = txt

            # Rooms
            if "room" in lower_txt:

                data["rooms"] = txt

        # =================================================
        # TYPE
        # =================================================

        html_lower = str(card).lower()

        if "handpicked" in html_lower:

            data["type"] = "Handpicked"

        elif "popular" in html_lower:

            data["type"] = "Popular"

        elif "paid vendor" in html_lower:

            data["type"] = "Sponsored"

        # =================================================
        # SAVE
        # =================================================

        results.append(data)

    except Exception as e:

        print("\n====================")
        print("CARD PARSE ERROR")
        print("====================")

        print("Card Index:", index)

        vendor = card.select_one(
            "a.vendor-detail.text-bold.h6"
        )

        if vendor:

            print(
                "Vendor:",
                vendor.get_text(
                    strip=True
                )
            )

        print("Error:", str(e))


# =========================================================
# SAVE JSON
# =========================================================

with open(
    OUTPUT_JSON_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        results,
        f,
        indent=4,
        ensure_ascii=False
    )

print(
    f"\nSaved {len(results)} venues"
)