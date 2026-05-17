# =========================================================
# CONFIG
# =========================================================

BASE_LIST_URL = "https://www.wedmegood.com/vendors/all/wedding-photographers/"

START_PAGE = 2
END_PAGE = 5

OUTPUT_JSON_FILE = "photographers.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

REQUEST_DELAY = 2  # seconds between requests


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


def detect_work_type(text):
    if not text:
        return None

    t = text.lower().strip()

    if "photo + video" in t:
        return "photo+video"

    if "photo" in t and "video" not in t:
        return "photo"

    if "video" in t and "photo" not in t:
        return "video"

    return None


def parse_card(card):
    data = {
        "vendor_name": None,
        "price_per_day": None,
        "work": None,
        "bottom_fields": [],
        "address": None,
        "url": None,
        "type": None,
    }

    # =====================================================
    # Vendor Name
    # =====================================================

    vendor_tag = card.select_one("a.vendor-detail.text-bold.h6")

    if vendor_tag:
        data["vendor_name"] = clean_text(vendor_tag.get_text())

    # =====================================================
    # URL
    # =====================================================

    profile_link = card.select_one('a[href*="/profile/"]')

    if profile_link:
        href = profile_link.get("href")

        if href:
            if href.startswith("http"):
                data["url"] = href
            else:
                data["url"] = "https://www.wedmegood.com" + href

    # =====================================================
    # Address
    # =====================================================

    location_tag = card.select_one("p.vendor-detail")

    if location_tag:
        data["address"] = clean_text(
            location_tag.get_text(separator=", ")
        )

    # =====================================================
    # Work Type
    # =====================================================

    work_tag = card.select_one(".vendor-price .text-secondary")

    if work_tag:
        work_text = clean_text(work_tag.get_text())
        data["work"] = detect_work_type(work_text)

    # =====================================================
    # Price
    # =====================================================

    price_tag = card.select_one(".vendor-price .text-bold span:last-child")

    if price_tag:
        price_text = clean_text(price_tag.get_text())

        if price_text:
            price_text = price_text.replace(",", "")

            try:
                data["price_per_day"] = int(price_text)
            except:
                data["price_per_day"] = price_text

    # =====================================================
    # Type
    # =====================================================

    card_html = str(card).lower()

    if "handpicked" in card_html:
        data["type"] = "Handpicked"

    elif "popular" in card_html:
        data["type"] = "Popular"

    # =====================================================
    # Bottom Fields
    # =====================================================

    li_tags = card.select("ul li")

    bottom_fields = []

    for li in li_tags:
        text = clean_text(li.get_text())

        if text:
            bottom_fields.append(text)

    data["bottom_fields"] = bottom_fields

    return data


# =========================================================
# SCRAPER
# =========================================================

all_results = []

for page in range(START_PAGE, END_PAGE + 1):

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
        print(f"Request failed: {e}")
        continue

    soup = BeautifulSoup(response.text, "html.parser")

    cards = soup.select("div[id^='card']")

    print(f"Found {len(cards)} cards")

    for card in cards:

        try:
            item = parse_card(card)

            # skip empty entries
            if item["vendor_name"]:
                all_results.append(item)

        except Exception as e:
            print(f"Card parse error: {e}")

    time.sleep(REQUEST_DELAY)


# =========================================================
# SAVE JSON
# =========================================================

with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
    json.dump(
        all_results,
        f,
        indent=4,
        ensure_ascii=False
    )

print("\n====================================")
print(f"Saved {len(all_results)} vendors")
print(f"Output: {OUTPUT_JSON_FILE}")
print("====================================")