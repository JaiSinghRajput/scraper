# =========================================================
# CONFIG
# =========================================================

INPUT_HTML_FILE = "mehendi.html"
OUTPUT_JSON_FILE = "mehendi_artists.json"

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
# PARSE EACH CARD
# =========================================================

for card in cards:

    try:

        data = {
            "vendor_name": None,
            "address": {
                "area": None,
                "city": None
            },
            "starting_price": None,
            "pricing_label": None,
            "about_preview": None,
            "bottom_fields": [],
            "type": None,
            "url": None
        }

        # =================================================
        # Vendor Name
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
            'a[href*="/profile/"]'
        )

        if profile_link:

            href = profile_link.get("href")

            if href:

                if href.startswith("http"):

                    data["url"] = href

                else:

                    data["url"] = BASE_URL + href

        # =================================================
        # Address
        # =================================================

        location_parts = card.select(
            "p.vendor-detail span"
        )

        clean_locations = []

        for loc in location_parts:

            txt = clean_text(loc.get_text())

            if txt and txt != ",":
                clean_locations.append(txt)

        if len(clean_locations) >= 1:
            data["address"]["area"] = clean_locations[0]

        if len(clean_locations) >= 2:
            data["address"]["city"] = clean_locations[-1]

        # =================================================
        # Pricing Label
        # =================================================

        pricing_label = card.select_one(
            ".text-secondary"
        )

        if pricing_label:

            data["pricing_label"] = clean_text(
                pricing_label.get_text()
            )

        # =================================================
        # Starting Price
        # =================================================

        price_tag = card.select_one(
            ".vendor-price .text-bold"
        )

        if price_tag:

            price_text = clean_text(
                price_tag.get_text()
            )

            price_text = price_text.replace("₹", "").strip()

            data["starting_price"] = price_text

        # =================================================
        # About Preview
        # =================================================

        tooltip_blocks = card.select(
            ".__react_component_tooltip"
        )

        for tip in tooltip_blocks:

            text = clean_text(
                tip.get_text(" ", strip=True)
            )

            if text and "About vendor" in text:

                text = text.replace(
                    "About vendor",
                    ""
                ).strip()

                data["about_preview"] = text

                break

        # =================================================
        # Bottom Fields
        # =================================================

        bottom_fields = []

        chips = card.select(
            'div[style*="background-color"] p'
        )

        for chip in chips:

            txt = clean_text(
                chip.get_text()
            )

            if txt:
                bottom_fields.append(txt)

        data["bottom_fields"] = bottom_fields

        # =================================================
        # Type
        # =================================================

        html_lower = str(card).lower()

        if "handpicked" in html_lower:

            data["type"] = "Handpicked"

        elif "popular" in html_lower:

            data["type"] = "Popular"

        # =================================================
        # SAVE
        # =================================================

        results.append(data)

    except Exception as e:

        print("Card parse error")
        print(str(e))


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

print(f"\nSaved {len(results)} vendors")