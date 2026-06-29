# =========================================================
# CONFIG
# =========================================================

BASE_LIST_URL = (
    "https://www.wedmegood.com/vendors/all/djs"
)

START_PAGE = 1
END_PAGE = 100

OUTPUT_JSON_FILE = "weddingDJ_all.json"

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

    t = text.lower()

    if "photo + video" in t:
        return "photo+video"

    if "photo" in t and "video" not in t:
        return "photo"

    if "video" in t and "photo" not in t:
        return "video"

    return None


# =========================================================
# PARSE CARD
# =========================================================

def parse_card(card):

    BASE_URL = "https://www.wedmegood.com"

    data = {

        "vendor_name": None,

        "url": None,

        "image_url": None,

        "address": None,

        "area": None,

        "city": None,

        "work": None,

        "price_per_day": None,

        "rating": None,

        "reviews_count": None,

        "about_preview": None,

        "bottom_fields": [],

        "type": None
    }

    # =====================================================
    # NAME
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
    # IMAGE
    # =====================================================

    image_tag = card.select_one(
        ".vendor-picture img"
    )

    if image_tag:

        data["image_url"] = (
            image_tag.get("src")
            or image_tag.get("data-src")
        )

    # =====================================================
    # LOCATION
    # =====================================================

    location_tag = card.select_one(
        "p.vendor-detail"
    )

    if location_tag:

        address = clean_text(
            location_tag.get_text(
                separator=", "
            )
        )

        data["address"] = address

        if address:

            parts = [
                x.strip()
                for x in address.split(",")
                if x.strip()
            ]

            if len(parts) >= 1:
                data["area"] = parts[0]

            if len(parts) >= 2:
                data["city"] = parts[-1]

    # =====================================================
    # WORK TYPE
    # =====================================================

    work_tag = card.select_one(
        ".vendor-price .text-secondary"
    )

    if work_tag:

        work_text = clean_text(
            work_tag.get_text()
        )

        data["work"] = detect_work_type(
            work_text
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

        if price_text:

            match = re.search(
                r'([\d,]+)',
                price_text
            )

            if match:

                data["price_per_day"] = int(
                    match.group(1)
                    .replace(",", "")
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

        match = re.search(
            r'(\d+(\.\d+)?)',
            rating_text
        )

        if match:

            data["rating"] = float(
                match.group(1)
            )

    # =====================================================
    # REVIEWS
    # =====================================================

    reviews_tag = card.select_one(
        ".review-cnt"
    )

    if reviews_tag:

        reviews_text = clean_text(
            reviews_tag.get_text()
        )

        match = re.search(
            r'(\d+)',
            reviews_text
        )

        if match:

            data["reviews_count"] = int(
                match.group(1)
            )

    # =====================================================
    # ABOUT PREVIEW
    # =====================================================

    tooltip_blocks = card.select(
        "div.__react_component_tooltip"
    )

    for tip in tooltip_blocks:

        txt = clean_text(
            tip.get_text(
                " ",
                strip=True
            )
        )

        if txt and "About vendor" in txt:

            txt = txt.replace(
                "About vendor",
                ""
            ).strip()

            data["about_preview"] = txt

            break

    # =====================================================
    # TYPE
    # =====================================================

    html_lower = str(card).lower()

    if "handpicked" in html_lower:

        data["type"] = "Handpicked"

    elif "popular" in html_lower:

        data["type"] = "Popular"

    # =====================================================
    # BOTTOM FIELDS
    # =====================================================

    bottom_fields = []

    li_tags = card.select("ul li")

    for li in li_tags:

        txt = clean_text(
            li.get_text()
        )

        if txt:

            bottom_fields.append(txt)

    data["bottom_fields"] = bottom_fields

    return data


# =========================================================
# LOAD EXISTING
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

            if isinstance(
                existing_data,
                list
            ):

                all_results = existing_data

                for item in existing_data:

                    url = item.get("url")

                    if url:

                        existing_urls.add(
                            url
                        )

        print(
            f"Loaded existing: "
            f"{len(existing_urls)}"
        )

    except Exception as e:

        print(
            f"Load error: {e}"
        )


# =========================================================
# SCROLL
# =========================================================

def auto_scroll(page):

    while True:

        current_height = page.evaluate(
            "document.body.scrollHeight"
        )

        page.evaluate(
            "window.scrollTo("
            "0,"
            "document.body.scrollHeight)"
        )

        page.wait_for_timeout(
            2500
        )

        new_height = page.evaluate(
            "document.body.scrollHeight"
        )

        if new_height == current_height:

            break


# =========================================================
# SCRAPE PAGE
# =========================================================

def scrape_page(
    context,
    page_number
):

    global all_results
    global existing_urls

    url = (
        f"{BASE_LIST_URL}"
        f"?page={page_number}"
    )

    print(
        "\n================================="
    )

    print(
        f"PAGE {page_number}"
    )

    print(url)

    print(
        "================================="
    )

    page = context.new_page()

    try:

        page.goto(
            url,
            timeout=120000,
            wait_until="domcontentloaded"
        )

        page.wait_for_timeout(
            3000
        )

        auto_scroll(page)

        page.wait_for_timeout(
            5000
        )

        soup = BeautifulSoup(
            page.content(),
            "html.parser"
        )

        cards = soup.find_all(
            "div",
            id=re.compile(
                r"^card\d+$"
            )
        )

        print(
            f"Found cards: "
            f"{len(cards)}"
        )

        for card in cards:

            try:

                item = parse_card(
                    card
                )

                if not item[
                    "vendor_name"
                ]:
                    continue

                item_url = item.get(
                    "url"
                )

                if (
                    item_url
                    and item_url
                    in existing_urls
                ):
                    continue

                if item_url:

                    existing_urls.add(
                        item_url
                    )

                all_results.append(
                    item
                )

                print(
                    f"Added: "
                    f"{item['vendor_name']}"
                )

            except Exception as e:

                print(
                    f"Card Error: "
                    f"{e}"
                )

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
            f"Saved: "
            f"{len(all_results)}"
        )

    finally:

        page.close()


# =========================================================
# MAIN
# =========================================================

with sync_playwright() as p:

    context = p.firefox.launch_persistent_context(

        user_data_dir=
        BROWSER_PROFILE_DIR,

        headless=HEADLESS,

        viewport={
            "width": 1400,
            "height": 900
        },

        locale="en-US",

        timezone_id="Asia/Kolkata",

        user_agent=(
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    )

    try:

        for page_number in range(
            START_PAGE,
            END_PAGE + 1
        ):

            try:

                scrape_page(
                    context,
                    page_number
                )

            except Exception as e:

                print(
                    f"Failed page "
                    f"{page_number}"
                )

                print(str(e))

            sleep_time = random.randint(
                REQUEST_DELAY,
                REQUEST_DELAY + 4
            )

            print(
                f"Sleeping "
                f"{sleep_time}s"
            )

            time.sleep(
                sleep_time
            )

    finally:

        context.close()

print(
    f"\nDONE. Saved "
    f"{len(all_results)} vendors"
)
