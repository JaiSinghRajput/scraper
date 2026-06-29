# =========================================================
# CONFIG
# =========================================================

BASE_LIST_URL = (
    "https://www.wedmegood.com/vendors/all/wedding-catering"
)

START_PAGE = 141
END_PAGE = 181

OUTPUT_JSON_FILE = "wedding_catering_vendors_all.json"

REQUEST_DELAY = 5

BROWSER_PROFILE_DIR = "./browser_profile"

HEADLESS = False

# =========================================================
# IMPORTS
# =========================================================

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

import json
import re
import time
import random
import os
import shutil

# =========================================================
# HELPERS
# =========================================================

def clean_text(text):

    if not text:
        return None

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# RESET PROFILE
# =========================================================

def reset_browser_profile():

    print("\n===================================")
    print("RESETTING FIREFOX PROFILE")
    print("===================================")

    try:

        if os.path.exists(BROWSER_PROFILE_DIR):

            shutil.rmtree(
                BROWSER_PROFILE_DIR,
                ignore_errors=True
            )

        os.makedirs(
            BROWSER_PROFILE_DIR,
            exist_ok=True
        )

        print("Browser profile reset complete")

    except Exception as e:

        print("Failed to reset profile")
        print(str(e))


# =========================================================
# PARSE CARD
# =========================================================

def parse_card(card):

    BASE_URL = "https://www.wedmegood.com"

    data = {

        "vendor_name": None,

        "url": None,

        "image_url": None,

        "location": None,

        "rating": None,

        "reviews_count": None,

        "catering_price": None,

        "pricing_label": None,

        "features": [],

        "offers_paid_trial": False,

        "travels_to_venue": False
    }

    # =====================================================
    # VENDOR NAME
    # =====================================================

    vendor_tag = card.select_one(
        "a.vendor-detail.text-bold.h6"
    )

    if vendor_tag:

        data["vendor_name"] = clean_text(
            vendor_tag.get_text()
        )

    # =====================================================
    # PROFILE URL
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
    # IMAGE URL
    # =====================================================

    image_tag = card.select_one(
        ".vendor-picture img.object-fit-cover"
    )

    if image_tag:

        data["image_url"] = image_tag.get("src")

    # =====================================================
    # LOCATION
    # =====================================================

    location_tag = card.select_one(
        ".info-icon.text-tertiary .vendor-detail"
    )

    if location_tag:

        data["location"] = clean_text(
            location_tag.get_text(
                " ",
                strip=True
            )
        )

    # =====================================================
    # RATING
    # =====================================================

    rating_tag = card.select_one(
        ".rating-new-5"
    )

    if rating_tag:

        rating_text = clean_text(
            rating_tag.get_text()
        )

        rating_match = re.search(
            r'(\d+(\.\d+)?)',
            rating_text
        )

        if rating_match:

            data["rating"] = float(
                rating_match.group(1)
            )

    # =====================================================
    # REVIEWS COUNT
    # =====================================================

    reviews_tag = card.select_one(
        ".review-cnt"
    )

    if reviews_tag:

        reviews_text = clean_text(
            reviews_tag.get_text()
        )

        reviews_match = re.search(
            r'(\d+)',
            reviews_text
        )

        if reviews_match:

            data["reviews_count"] = int(
                reviews_match.group(1)
            )

    # =====================================================
    # PRICE
    # =====================================================

    price_tag = card.select_one(
        ".vendor-price .vendor-detail.text-bold"
    )

    if price_tag:

        price_text = clean_text(
            price_tag.get_text()
        )

        data["pricing_label"] = price_text

        numeric_match = re.search(
            r'₹\s*([\d,]+)',
            price_text
        )

        if numeric_match:

            data["catering_price"] = (
                numeric_match.group(1)
                .replace(",", "")
            )

    # =====================================================
    # FEATURES
    # =====================================================

    features = []

    # ---------------------------------------------
    # Visible features
    # ---------------------------------------------

    visible_feature_ps = card.select(
        '.v-center.margin-10 > div > p'
    )

    for p in visible_feature_ps:

        txt = clean_text(
            p.get_text()
        )

        if not txt:
            continue

        if txt.startswith("+"):
            continue

        features.append(txt)

    # ---------------------------------------------
    # Tooltip hidden features
    # ---------------------------------------------

    tooltip_lis = card.select(
        'div.__react_component_tooltip li'
    )

    for li in tooltip_lis:

        txt = clean_text(
            li.get_text()
        )

        if txt:

            features.append(txt)

    # ---------------------------------------------
    # Remove duplicates
    # ---------------------------------------------

    features = list(
        dict.fromkeys(features)
    )

    data["features"] = features

    # =====================================================
    # BOOLEAN FLAGS
    # =====================================================

    lower_features = [
        x.lower() for x in features
    ]

    data["offers_paid_trial"] = (
        "offers paid trial" in lower_features
    )

    data["travels_to_venue"] = (
        "travels to venue" in lower_features
    )

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
# SCRAPE SINGLE PAGE
# =========================================================
def auto_scroll(page):

    previous_height = 0

    while True:

        current_height = page.evaluate(
            "document.body.scrollHeight"
        )

        page.evaluate(
            "window.scrollTo(0, document.body.scrollHeight)"
        )

        page.wait_for_timeout(2500)

        new_height = page.evaluate(
            "document.body.scrollHeight"
        )

        if new_height == current_height:
            break

        previous_height = current_height


def scrape_page(context, page_number):

    url = f"{BASE_LIST_URL}?page={page_number}"

    print("\n===================================")
    print(f"Scraping page {page_number}")
    print(url)
    print("===================================")

    page = context.new_page()

    try:

        page.goto(
            url,
            timeout=120000,
            wait_until="domcontentloaded"
        )

        page.wait_for_timeout(3000)
        auto_scroll(page)
        page.wait_for_timeout(10000)

        html = page.content()

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        cards = soup.find_all(
            "div",
            id=re.compile(r"^card\d+$")
        )

        print(
            f"Found cards: {len(cards)}"
        )

        for card in cards:

            try:

                item = parse_card(card)

                if item["vendor_name"]:

                    item_url = item.get("url")

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

        # =================================================
        # SAVE PROGRESS
        # =================================================

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
            f"(Page {page_number}) "
            f"Total Vendors: {len(all_results)}"
        )

    finally:

        page.close()


# =========================================================
# MAIN
# =========================================================

with sync_playwright() as p:

    current_page = START_PAGE

    context = None

    try:

        # =================================================
        # SINGLE PERSISTENT FIREFOX CONTEXT
        # =================================================

        context = p.firefox.launch_persistent_context(

            user_data_dir=BROWSER_PROFILE_DIR,

            headless=HEADLESS,

            viewport={
                "width": 1400,
                "height": 900
            },

            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),

            locale="en-US",

            timezone_id="Asia/Kolkata"
        )

        while current_page <= END_PAGE:

            try:

                scrape_page(
                    context,
                    current_page
                )

                current_page += 1

                sleep_time = random.randint(
                    REQUEST_DELAY,
                    REQUEST_DELAY + 4
                )

                print(
                    f"\nSleeping {sleep_time}s..."
                )

                time.sleep(sleep_time)

            except Exception as e:

                print("\n===================================")
                print(f"FAILED PAGE {current_page}")
                print(str(e))
                print("===================================")

                time.sleep(10)

                continue

    finally:

        try:

            if context:
                context.close()

        except:
            pass


# =========================================================
# DONE
# =========================================================

print("\n===================================")
print("SCRAPING COMPLETED")
print(f"Saved {len(all_results)} vendors")
print(f"Output: {OUTPUT_JSON_FILE}")
print("===================================")
