# =========================================================
# CONFIG
# =========================================================

BASE_LIST_URL = (
    "https://www.wedmegood.com/vendors/all/wedding-cakes/"
)

START_PAGE = 1
END_PAGE = 62

OUTPUT_JSON_FILE = "wedding_cakes.json"

REQUEST_DELAY = 5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; Win64; x64) "
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
import random
import os


# =========================================================
# HELPERS
# =========================================================
def auto_scroll(page):
    while True:
        old_height = page.evaluate("document.body.scrollHeight")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2500)
        new_height = page.evaluate("document.body.scrollHeight")
        if old_height == new_height:
            break
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1000)



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
# LOAD EXISTING DATA
# =========================================================

all_results = []

existing_urls = set()

if os.path.exists(OUTPUT_JSON_FILE):

    try:

        with open(
            OUTPUT_JSON_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            existing_data = json.load(f)

            if isinstance(existing_data, list):

                all_results = existing_data

                for item in existing_data:

                    url = item.get("url")

                    if url:
                        existing_urls.add(url)

        print(
            f"Loaded existing vendors: "
            f"{len(existing_urls)}"
        )

    except Exception as e:

        print("Could not load existing JSON")
        print(str(e))


# =========================================================
# SCRAPER
# =========================================================

for page in range(
    START_PAGE,
    END_PAGE + 1
):

    url = f"{BASE_LIST_URL}?page={page}"

    print("\n===================================")
    print(f"Scraping page {page}")
    print(url)
    print("===================================")

    MAX_RETRIES = 999999

    response = None

    # =====================================================
    # RETRY LOOP
    # =====================================================

    for attempt in range(MAX_RETRIES):

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=30
            )

            # =============================================
            # RATE LIMIT HANDLING
            # =============================================

            if response.status_code == 429:

                wait_time = random.randint(120, 180)

                print(
                    f"\n429 Rate Limit Hit "
                    f"on page {page}"
                )

                print(
                    f"Sleeping for "
                    f"{wait_time} seconds..."
                )

                time.sleep(wait_time)

                # Retry SAME page
                continue

            response.raise_for_status()

            print(
                f"Page {page} loaded successfully"
            )

            break

        except requests.exceptions.RequestException as e:

            print(
                f"\nRequest failed "
                f"on page {page}"
            )

            print(str(e))

            wait_time = random.randint(30, 60)

            print(
                f"Retrying in "
                f"{wait_time} seconds..."
            )

            time.sleep(wait_time)

    # =====================================================
    # PARSE HTML
    # =====================================================

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    cards = soup.select(
        'div[id^="card"]'
    )

    print(f"Found cards: {len(cards)}")

    # =====================================================
    # PROCESS CARDS
    # =====================================================

    for card in cards:

        try:

            item = parse_card(card)

            if item["vendor_name"]:

                item_url = item.get("url")

                # =========================================
                # SKIP DUPLICATES
                # =========================================

                if item_url in existing_urls:

                    print(
                        f"Duplicate skipped: "
                        f"{item['vendor_name']}"
                    )

                    continue

                existing_urls.add(item_url)

                all_results.append(item)

                print(
                    f"Added: "
                    f"{item['vendor_name']}"
                )

        except Exception as e:

            print("Card parse error")
            print(str(e))

    # =====================================================
    # SAVE AFTER EACH PAGE
    # =====================================================

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

    print(
        f"\nProgress Saved "
        f"(Page {page}) "
        f"Total Vendors: {len(all_results)}"
    )

    sleep_time = random.randint(
        REQUEST_DELAY,
        REQUEST_DELAY + 3
    )

    print(
        f"Sleeping {sleep_time}s "
        f"before next page..."
    )

    time.sleep(sleep_time)


# =========================================================
# DONE
# =========================================================

print("\n===================================")
print("SCRAPING COMPLETED")
print(f"Saved {len(all_results)} vendors")
print(f"Output: {OUTPUT_JSON_FILE}")
print("===================================")