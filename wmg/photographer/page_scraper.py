# =========================================================
# CONFIG
# =========================================================

INPUT_JSON_FILE = "1st_Page_photographers.json"
OUTPUT_JSON_FILE = "1st_Page_photographers_detailed.json"

REQUEST_DELAY = 2
MAX_RETRIES = 5

# Sleep when HTTP 429 happens
RATE_LIMIT_SLEEP = 120

TIMEOUT = 30

USE_PROXY = False

PROXIES = {
    "http": "http://username:password@host:port",
    "https": "http://username:password@host:port",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

# Save after every N vendors
SAVE_EVERY = 1


# =========================================================
# IMPORTS
# =========================================================

import requests
from bs4 import BeautifulSoup
import json
import re
import time
import traceback


# =========================================================
# SESSION
# =========================================================

session = requests.Session()
session.headers.update(HEADERS)

if USE_PROXY:
    session.proxies.update(PROXIES)


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

    text = re.sub(r"[^\d]", "", text)

    if not text:
        return None

    try:
        return int(text)
    except:
        return text


def safe_get_text(element):
    if not element:
        return None

    return clean_text(element.get_text(" ", strip=True))


def get_soup(url):

    for attempt in range(MAX_RETRIES):

        try:

            response = session.get(
                url,
                timeout=TIMEOUT
            )

            # =========================================
            # RATE LIMIT
            # =========================================

            if response.status_code == 429:

                print(f"[429] Sleeping {RATE_LIMIT_SLEEP}s")

                time.sleep(RATE_LIMIT_SLEEP)

                continue

            response.raise_for_status()

            return BeautifulSoup(response.text, "html.parser")

        except Exception as e:

            print(f"[Retry {attempt + 1}] {url}")
            print(str(e))

            if attempt < MAX_RETRIES - 1:
                time.sleep(5)

    return None


# =========================================================
# EXTRACT PRICING
# =========================================================

def extract_pricing(soup):

    pricing = {}

    # =====================================================
    # MAIN PACKAGE PRICING
    # =====================================================

    pricing_rows = soup.select(
        ".VendorPricing .f-space-between"
    )

    for row in pricing_rows:

        text = clean_text(
            row.get_text(" ", strip=True)
        )

        if not text:
            continue

        # =============================================
        # Photo Package
        # =============================================

        if "Photo Package" in text:

            match = re.search(
                r"₹\s*([\d,]+)",
                text
            )

            if match:

                pricing["photo_package_per_day"] = int(
                    match.group(1).replace(",", "")
                )

        # =============================================
        # Photo + Video
        # =============================================

        elif "Photo + Video" in text:

            match = re.search(
                r"₹\s*([\d,]+)",
                text
            )

            if match:

                pricing["photo_video_package_per_day"] = int(
                    match.group(1).replace(",", "")
                )

    # =====================================================
    # COLLAPSIBLE PRICING BREAKUP
    # =====================================================

    breakup_boxes = soup.select(
        ".pricing-breakup .grid__col"
    )

    for box in breakup_boxes:

        title_tag = box.select_one(
            "p.text-bold"
        )

        value_tags = box.select(
            "span.text-tertiary"
        )

        if not title_tag:
            continue

        title = clean_text(
            title_tag.get_text()
        ).lower()

        # =============================================
        # Build value correctly
        # =============================================

        value_parts = []

        for v in value_tags:

            txt = clean_text(v.get_text())

            if txt:
                value_parts.append(txt)

        if not value_parts:
            continue

        value = "".join(value_parts)

        pricing[title] = value

    return pricing

# =========================================================
# EXTRACT FAQS
# =========================================================

def extract_bottom_details(soup):

    faqs = {}

    faq_blocks = soup.select(".faq")

    for faq in faq_blocks:

        title = faq.select_one(".text-bold")
        value = faq.select_one(".text-tertiary")

        if not title or not value:
            continue

        key = clean_text(title.get_text()).lower()

        key = (
            key.replace(" ", "_")
               .replace("/", "_")
        )

        faqs[key] = clean_text(value.get_text())

    return faqs

# =========================================================
# EXTRACT VIDEOS
# =========================================================

def extract_videos(profile_url):

    videos = []

    try:

        # =================================================
        # BUILD ALBUMS URL
        # =================================================

        albums_url = profile_url.rstrip("/") + "/albums"

        print(f"[VIDEOS] {albums_url}")

        # =================================================
        # REQUEST
        # =================================================

        response = session.get(
            albums_url,
            timeout=TIMEOUT
        )

        # =================================================
        # RATE LIMIT
        # =================================================

        if response.status_code == 429:

            print(f"[429] Sleeping {RATE_LIMIT_SLEEP}s")

            time.sleep(RATE_LIMIT_SLEEP)

            return videos

        response.raise_for_status()

        html = response.text

        # =================================================
        # FIND ALL YOUTUBE IDS
        # =================================================

        youtube_ids = re.findall(
            r'youtube_\d+_([A-Za-z0-9_-]{5,})\.jpg',
            html
        )

        youtube_ids = list(set(youtube_ids))

        print(f"Found YouTube IDs: {len(youtube_ids)}")

        # =================================================
        # BUILD TITLE MAP
        # =================================================

        title_map = {}

        soup = BeautifulSoup(html, "html.parser")

        video_blocks = soup.select(".VideoItem")

        print(f"Video blocks: {len(video_blocks)}")

        for block in video_blocks:

            try:

                # =========================================
                # Title
                # =========================================

                title_tag = block.select_one(
                    ".video-detail"
                )

                video_title = None

                if title_tag:

                    video_title = clean_text(
                        title_tag.get_text()
                    )

                # =========================================
                # Style
                # =========================================

                style = block.get("style", "")

                if not style:
                    continue

                # =========================================
                # Extract YouTube ID
                # =========================================

                yt_match = re.search(
                    r'youtube_\d+_([A-Za-z0-9_-]+)\.',
                    style
                )

                if not yt_match:
                    continue

                youtube_id = yt_match.group(1)

                title_map[youtube_id] = video_title

            except Exception as e:

                print("Video block parse error")
                print(str(e))

        # =================================================
        # BUILD FINAL VIDEO LIST
        # =================================================

        for youtube_id in youtube_ids:

            try:

                video = {
                    "youtube_id": youtube_id,
                    "youtube_url": (
                        f"https://www.youtube.com/watch?v={youtube_id}"
                    ),
                    "title": title_map.get(youtube_id)
                }

                videos.append(video)

            except Exception as e:

                print("Final video build error")
                print(str(e))

    except Exception as e:

        print("Video extraction failed")
        print(str(e))

    return videos


# =========================================================
# MAIN PROFILE PARSER
# =========================================================

def parse_profile(url):

    soup = get_soup(url)

    if not soup:
        return None

    result = {}

    # =====================================================
    # Basic Info
    # =====================================================

    h1 = soup.select_one("h1")

    if h1:
        result["vendor_name_detailed"] = clean_text(h1.get_text())

    rating = soup.select_one(".StarRating")

    if rating:
        result["rating"] = clean_text(rating.get_text())

    review = soup.select_one(".review-cnt")

    if review:
        result["review_count"] = clean_text(review.get_text())

    address = soup.select_one(".vendor-address")

    if address:
        result["full_address"] = clean_text(address.get_text())

    # =====================================================
    # Membership
    # =====================================================

    html = str(soup).lower()

    if "handpicked" in html:
        result["membership_type"] = "Handpicked"

    elif "popular" in html:
        result["membership_type"] = "Popular"

    # =====================================================
    # Stats
    # =====================================================

    action_buttons = soup.select(".action-buttons .grid__col")

    stats = {}

    for item in action_buttons:

        txt = clean_text(item.get_text())

        if not txt:
            continue

        if "Photos" in txt:
            stats["photos_count"] = clean_price(txt)

        elif "Shortlist" in txt:
            pass

    result["stats"] = stats

    # =====================================================
    # About
    # =====================================================

    about_section = soup.select_one(".about-body")

    if about_section:
        result["about_text"] = clean_text(
            about_section.get_text(" ", strip=True)
        )

    # =====================================================
    # Pricing
    # =====================================================

    result["pricing"] = extract_pricing(soup)

    # =====================================================
    # FAQs
    # =====================================================

    result["business_details"] = extract_bottom_details(soup)


    # =====================================================
    # Videos
    # =====================================================

    result["videos"] = extract_videos(url)

    return result


# =========================================================
# LOAD INPUT JSON
# =========================================================

with open(INPUT_JSON_FILE, "r", encoding="utf-8") as f:
    vendors = json.load(f)

print(f"Loaded {len(vendors)} vendors")


# =========================================================
# PROCESS
# =========================================================

output = []

for idx, vendor in enumerate(vendors, start=1):

    try:

        url = vendor.get("url")

        if not url:
            output.append(vendor)
            continue

        print(f"\n[{idx}/{len(vendors)}]")
        print(url)

        profile_data = parse_profile(url)

        if profile_data:
            vendor.update(profile_data)

        output.append(vendor)

        # =============================================
        # SAVE PROGRESS
        # =============================================

        if idx % SAVE_EVERY == 0:

            with open(
                OUTPUT_JSON_FILE,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    output,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

            print(f"Progress saved ({idx})")

        time.sleep(REQUEST_DELAY)

    except Exception as e:

        print("ERROR")
        print(traceback.format_exc())

        output.append(vendor)


# =========================================================
# FINAL SAVE
# =========================================================

with open(
    OUTPUT_JSON_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        indent=4,
        ensure_ascii=False
    )

print("\n===================================")
print(f"Completed : {len(output)} vendors")
print(f"Saved to  : {OUTPUT_JSON_FILE}")
print("===================================")