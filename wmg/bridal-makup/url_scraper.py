# =========================================================
# CONFIG
# =========================================================

BASE_LIST_URL = (
    "https://www.wedmegood.com/vendors/rajasthan/bridal-makeup/"
)

START_PAGE = 1
END_PAGE = 5

OUTPUT_JSON_FILE = "bridal_makeup_vendors_rajasthan.json"

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

        "bridal_makeup_price": None,

        "pricing_label": None,

        "about_preview": None,

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
    # PRICE LABEL
    # =====================================================

    label_tag = card.select_one(
        ".text-secondary"
    )

    if label_tag:

        data["pricing_label"] = clean_text(
            label_tag.get_text()
        )

    # =====================================================
    # PRICE
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
            .replace(",", "")
            .strip()
        )

        data["bridal_makeup_price"] = price_text

    # =====================================================
    # ABOUT
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
    # FEATURES
    # =====================================================

    features = []

    chip_ps = card.select(
        '.v-center.margin-10 p'
    )

    for p in chip_ps:

        txt = clean_text(
            p.get_text()
        )

        if txt:

            features.append(txt)

    features = list(
        dict.fromkeys(features)
    )

    data["features"] = features

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
            wait_until="networkidle"
        )

        # Random delay
        time.sleep(
            random.uniform(3, 6)
        )

        html = page.content()

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        cards = soup.select(
            'div[id^="card"]'
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

        # SAVE
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

    while current_page <= END_PAGE:

        browser = None
        context = None

        try:

            # =============================================
            # PERSISTENT FIREFOX PROFILE
            # =============================================

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
            print("SCRAPING FAILED")
            print(str(e))
            print("===================================")

            try:

                if context:
                    context.close()

            except:
                pass

            # =============================================
            # RESET PROFILE ON FAILURE
            # =============================================

            reset_browser_profile()

            print(
                "\nRetrying same page with "
                "fresh Firefox profile..."
            )

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