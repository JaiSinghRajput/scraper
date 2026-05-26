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
# CONFIG
# =========================================================

BASE_LIST_URL = (
    "https://www.wedmegood.com/vendors/udaipur/wedding-venues"
)

START_PAGE = 2
END_PAGE = 24

OUTPUT_JSON_FILE = (
    "wedding_venues_udaipur_cards.json"
)

REQUEST_DELAY = 5

BASE_URL = (
    "https://www.wedmegood.com"
)

TOR_PROXY = (
    "socks5://127.0.0.1:9050"
)

HEADLESS = True


# =========================================================
# HELPERS
# =========================================================

def clean_text(text):

    if not text:
        return None

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def clean_price(text):

    if not text:
        return None

    return (
        text
        .replace("₹", "")
        .replace(",", "")
        .strip()
    )


# =========================================================
# PLAYWRIGHT
# =========================================================

playwright = sync_playwright().start()

browser = playwright.chromium.launch(
    headless=HEADLESS,
    proxy={
        "server": TOR_PROXY
    }
)

context = browser.new_context(
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
)


# =========================================================
# PARSE CARD
# =========================================================

def parse_card(card):

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
        'a[href*="/wedding-venues/"]'
    )

    if profile_link:

        href = profile_link.get("href")

        if href:

            if href.startswith("http"):

                data["url"] = href

            else:

                data["url"] = (
                    BASE_URL + href
                )

    # =====================================================
    # RATING
    # =====================================================

    rating_tag = card.select_one(
        ".StarRatingNew"
    )

    if rating_tag:

        rating = clean_text(
            rating_tag.get_text()
        )

        if rating:

            rating = (
                rating
                .replace("★", "")
                .strip()
            )

            data["rating"] = rating

    # =====================================================
    # REVIEWS
    # =====================================================

    review_tag = card.select_one(
        ".review-cnt"
    )

    if review_tag:

        data["reviews"] = clean_text(
            review_tag.get_text()
        )

    # =====================================================
    # ADDRESS
    # =====================================================

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

            parts = [
                x.strip()
                for x in location_text.split(",")
                if x.strip()
            ]

            if len(parts) >= 1:

                data["address"]["area"] = (
                    parts[0]
                )

            if len(parts) >= 2:

                data["address"]["city"] = (
                    parts[-1]
                )

    # =====================================================
    # VENUE TYPE
    # =====================================================

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

    # =====================================================
    # PRICING
    # =====================================================

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

    # =====================================================
    # ABOUT
    # =====================================================

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

    # =====================================================
    # BOTTOM FIELDS
    # =====================================================

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

        lower_txt = (
            txt.lower().strip()
        )

        # Skip "+3 more"
        if re.search(
            r'^\+\d+\s+more$',
            lower_txt
        ):
            continue

        bottom_fields.append(txt)

    # =====================================================
    # TOOLTIP ITEMS
    # =====================================================

    tooltip_divs = card.find_all(
        "div",
        id=lambda x: (
            x and "tooltop" in x
        )
    )

    for tooltip in tooltip_divs:

        li_items = tooltip.find_all("li")

        for li in li_items:

            txt = clean_text(
                li.get_text()
            )

            if not txt:
                continue

            lower_txt = (
                txt.lower().strip()
            )

            if re.search(
                r'^\+\d+\s+more$',
                lower_txt
            ):
                continue

            bottom_fields.append(txt)

    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    seen = set()

    cleaned = []

    for item in bottom_fields:

        normalized = (
            item.lower().strip()
        )

        if normalized in seen:
            continue

        seen.add(normalized)

        cleaned.append(item)

    bottom_fields = cleaned

    data["bottom_fields"] = (
        bottom_fields
    )

    # =====================================================
    # STRUCTURED EXTRACTION
    # =====================================================

    for txt in bottom_fields:

        lower_txt = txt.lower()

        if "pax" in lower_txt:

            data["capacity"] = txt

        if "room" in lower_txt:

            data["rooms"] = txt

    # =====================================================
    # TYPE
    # =====================================================

    html_lower = str(card).lower()

    if "handpicked" in html_lower:

        data["type"] = "Handpicked"

    elif "popular" in html_lower:

        data["type"] = "Popular"

    elif "paid vendor" in html_lower:

        data["type"] = "Sponsored"

    return data


# =========================================================
# LOAD EXISTING
# =========================================================

all_results = []

existing_urls = set()

if os.path.exists(
    OUTPUT_JSON_FILE
):

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

                        existing_urls.add(url)

        print(
            f"Loaded existing venues: "
            f"{len(existing_urls)}"
        )

    except Exception as e:

        print(
            "Could not load existing JSON"
        )

        print(str(e))


# =========================================================
# SCRAPER
# =========================================================

for page_num in range(
    START_PAGE,
    END_PAGE + 1
):

    url = (
        f"{BASE_LIST_URL}?page={page_num}"
    )

    print("\n===================================")
    print(
        f"Scraping page {page_num}"
    )
    print(url)
    print("===================================")

    page = context.new_page()

    try:

        page.goto(
            url,
            wait_until="networkidle",
            timeout=120000
        )

        # Let tooltip JS render
        page.wait_for_timeout(5000)

        html = page.content()

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # =============================================
        # ONLY FIRST VendorList
        # =============================================

        vendor_lists = soup.select(
            ".VendorList"
        )

        if not vendor_lists:

            print(
                "No VendorList found"
            )

            continue

        main_vendor_list = (
            vendor_lists[0]
        )

        cards = main_vendor_list.select(
            'div[id^="card"]'
        )

        print(
            f"Found cards: "
            f"{len(cards)}"
        )

        # =============================================
        # PROCESS CARDS
        # =============================================

        for index, card in enumerate(cards):

            try:

                item = parse_card(card)

                if item["vendor_name"]:

                    item_url = item.get(
                        "url"
                    )

                    if (
                        item_url
                        in existing_urls
                    ):

                        print(
                            f"Duplicate skipped: "
                            f"{item['vendor_name']}"
                        )

                        continue

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
                    "\nCARD PARSE ERROR"
                )

                print(
                    "Card Index:",
                    index
                )

                print(
                    "Error:",
                    str(e)
                )

        # =============================================
        # SAVE
        # =============================================

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
            f"(Page {page_num}) "
            f"Total Venues: "
            f"{len(all_results)}"
        )

    finally:

        page.close()

    sleep_time = random.randint(
        REQUEST_DELAY,
        REQUEST_DELAY + 3
    )

    print(
        f"Sleeping "
        f"{sleep_time}s..."
    )

    time.sleep(sleep_time)


# =========================================================
# CLEANUP
# =========================================================

browser.close()

playwright.stop()

print("\n===================================")
print("SCRAPING COMPLETED")
print(
    f"Saved {len(all_results)} venues"
)
print(
    f"Output: {OUTPUT_JSON_FILE}"
)
print("===================================")