# =========================================================
# CONFIG
# =========================================================

BASE_LIST_URL = (
    "https://www.wedmegood.com/vendors/all/wedding-planners/"
)

START_PAGE = 1
END_PAGE = 5

OUTPUT_JSON_FILE = "wedding_planners.json"

REQUEST_DELAY = 2

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


# =========================================================
# IMPORTS
# =========================================================

import requests
from bs4 import BeautifulSoup
import json
import re
import time


# =========================================================
# HELPERS
# =========================================================

def clean_text(text):

    if not text:
        return None

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def parse_card(card):

    BASE_URL = "https://www.wedmegood.com"

    data = {
        "vendor_name": None,

        "address": {
            "area": None,
            "city": None
        },

        "planning_fee": None,

        "pricing_label": None,

        "about_preview": None,

        "bottom_fields": [],

        "type": None,

        "verified": False,

        "url": None
    }

    # =====================================================
    # Vendor Name
    # =====================================================

    vendor_tag = card.select_one(
        "a.vendor-detail.text-bold.h6"
    )

    if vendor_tag:

        data["vendor_name"] = clean_text(
            vendor_tag.get_text()
        )

    # =====================================================
    # URL
    # =====================================================

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

    # =====================================================
    # VERIFIED
    # =====================================================

    verified_icon = card.select_one(
        'img[alt="verified_icon"]'
    )

    data["verified"] = verified_icon is not None

    # =====================================================
    # ADDRESS
    # =====================================================

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

    # =====================================================
    # PRICING LABEL
    # =====================================================

    label_tag = card.select_one(
        ".text-secondary"
    )

    if label_tag:

        data["pricing_label"] = clean_text(
            label_tag.get_text()
        )

    # =====================================================
    # PLANNING FEE
    # =====================================================

    price_tag = card.select_one(
        ".vendor-price .text-bold"
    )

    if price_tag:

        price_text = clean_text(
            price_tag.get_text()
        )

        price_text = (
            price_text
            .replace("₹", "")
            .strip()
        )

        data["planning_fee"] = price_text

    # =====================================================
    # ABOUT PREVIEW
    # =====================================================

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

    # =====================================================
    # BOTTOM FIELDS
    # FIXED FOR SINGLE CHIP
    # =====================================================

    bottom_fields = []

    chip_ps = card.select(
        '.v-center.margin-10 p'
    )

    for p in chip_ps:

        txt = clean_text(
            p.get_text()
        )

        if txt:
            bottom_fields.append(txt)

    data["bottom_fields"] = list(
        dict.fromkeys(bottom_fields)
    )

    # =====================================================
    # TYPE
    # =====================================================

    html_lower = str(card).lower()

    if "handpicked" in html_lower:

        data["type"] = "Handpicked"

    elif "popular" in html_lower:

        data["type"] = "Popular"

    return data


# =========================================================
# SCRAPER
# =========================================================

all_results = []

for page in range(
    START_PAGE,
    END_PAGE + 1
):

    url = f"{BASE_LIST_URL}?page={page}"

    print(f"\nScraping page {page}")
    print(url)

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

    except Exception as e:

        print("Request failed")
        print(str(e))

        continue

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    cards = soup.select(
        'div[id^="card"]'
    )

    print(f"Found cards: {len(cards)}")

    for card in cards:

        try:

            item = parse_card(card)

            if item["vendor_name"]:

                all_results.append(item)

        except Exception as e:

            print("Card parse error")
            print(str(e))

    time.sleep(REQUEST_DELAY)


# =========================================================
# SAVE JSON
# =========================================================

with open(
    OUTPUT_JSON_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        all_results,
        f,
        indent=4,
        ensure_ascii=False
    )

print("\n===================================")
print(f"Saved {len(all_results)} vendors")
print("===================================")