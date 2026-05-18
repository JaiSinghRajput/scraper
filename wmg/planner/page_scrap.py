# =========================================================
# CONFIG
# =========================================================

INPUT_JSON_FILE = "wedding_planners.json"
OUTPUT_JSON_FILE = "wedding_planners_detailed.json"

REQUEST_DELAY = 2
TIMEOUT = 30

RATE_LIMIT_SLEEP = 30

PROXIES = None
# Example:
# PROXIES = {
#     "http": "http://user:pass@host:port",
#     "https": "http://user:pass@host:port"
# }

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
# SESSION
# =========================================================

session = requests.Session()

session.headers.update(HEADERS)

if PROXIES:
    session.proxies.update(PROXIES)


# =========================================================
# HELPERS
# =========================================================

def clean_text(text):

    if not text:
        return None

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_number(text):

    if not text:
        return None

    match = re.search(r'([\d,]+)', text)

    if not match:
        return None

    return int(
        match.group(1).replace(",", "")
    )


# =========================================================
# EXTRACT VIDEOS
# =========================================================

def extract_videos(profile_url):

    videos = []

    try:

        albums_url = (
            profile_url.rstrip("/") + "/albums"
        )

        response = session.get(
            albums_url,
            timeout=TIMEOUT
        )

        if response.status_code == 429:

            print(f"[429] Sleeping {RATE_LIMIT_SLEEP}s")

            time.sleep(RATE_LIMIT_SLEEP)

            return videos

        response.raise_for_status()

        html = response.text

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # =============================================
        # FIND YOUTUBE IDS
        # =============================================

        youtube_ids = re.findall(
            r'youtube_\d+_([A-Za-z0-9_-]{5,})\.jpg',
            html
        )

        youtube_ids = list(set(youtube_ids))

        # =============================================
        # TITLES
        # =============================================

        title_map = {}

        video_blocks = soup.select(
            ".VideoItem"
        )

        for block in video_blocks:

            try:

                title_tag = block.select_one(
                    ".video-detail"
                )

                video_title = None

                if title_tag:

                    video_title = clean_text(
                        title_tag.get_text()
                    )

                style = block.get("style", "")

                yt_match = re.search(
                    r'youtube_\d+_([A-Za-z0-9_-]+)\.',
                    style
                )

                if yt_match:

                    youtube_id = yt_match.group(1)

                    title_map[youtube_id] = video_title

            except:
                pass

        # =============================================
        # FINAL VIDEOS
        # =============================================

        for youtube_id in youtube_ids:

            videos.append({
                "youtube_id": youtube_id,
                "youtube_url": (
                    f"https://www.youtube.com/watch?v={youtube_id}"
                ),
                "title": title_map.get(youtube_id)
            })

    except Exception as e:

        print("Video extraction failed")
        print(str(e))

    return videos


# =========================================================
# EXTRACT ALBUMS
# =========================================================

def extract_albums(soup, base_url):

    albums = []

    album_cards = soup.select(
        ".AlbumCover a[href*='/project/']"
    )

    seen = set()

    for card in album_cards:

        try:

            href = card.get("href")

            if not href:
                continue

            if href in seen:
                continue

            seen.add(href)

            full_url = (
                "https://www.wedmegood.com" + href
            )

            title = None
            location = None
            event_type = None
            image_count = None

            paragraphs = card.select(
                ".cover-title-content p"
            )

            if len(paragraphs) >= 1:
                title = clean_text(
                    paragraphs[0].get_text()
                )

            if len(paragraphs) >= 2:

                location_text = clean_text(
                    paragraphs[1].get_text()
                )

                location = (
                    location_text
                    .replace("Shot in ", "")
                    .strip()
                )

            if len(paragraphs) >= 3:

                event_type = clean_text(
                    paragraphs[2].get_text()
                )

            count_tag = card.select_one(
                ".image-count"
            )

            if count_tag:

                image_count = extract_number(
                    count_tag.get_text()
                )

            albums.append({
                "title": title,
                "location": location,
                "event_type": event_type,
                "image_count": image_count,
                "url": full_url
            })

        except:
            pass

    return albums


# =========================================================
# PARSE PROFILE
# =========================================================

def parse_profile(url):

    result = {
        "vendor_name": None,

        "type": None,

        "rating": None,

        "review_count": None,

        "address": {
            "area": None,
            "city": None
        },

        "additional_cities": [],

        "pricing": {
            "starting_price": None,
            "pricing_label": None
        },

        "about": None,

        "services": [],

        "planned_cities": [],

        "business_details": {},

        "albums": [],

        "videos": [],

        "stats": {
            "portfolio_images": None,
            "albums": None,
            "videos": None
        },

        "rating_distribution": {},

        "last_review_updated": None,

        "url": url
    }

    try:

        response = session.get(
            url,
            timeout=TIMEOUT
        )

        if response.status_code == 429:

            print(f"[429] Sleeping {RATE_LIMIT_SLEEP}s")

            time.sleep(RATE_LIMIT_SLEEP)

            return result

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # =================================================
        # NAME
        # =================================================

        name_tag = soup.select_one("h1")

        if name_tag:

            result["vendor_name"] = clean_text(
                name_tag.get_text()
            )

        # =================================================
        # TYPE
        # =================================================

        html_lower = str(soup).lower()

        if "handpicked" in html_lower:

            result["type"] = "Handpicked"

        elif "popular" in html_lower:

            result["type"] = "Popular"

        # =================================================
        # RATING
        # =================================================

        rating_tag = soup.select_one(
            ".StarRating"
        )

        if rating_tag:

            try:

                result["rating"] = float(
                    clean_text(
                        rating_tag.get_text()
                    )
                    .replace("★", "")
                    .strip()
                )

            except:
                pass

        # =================================================
        # REVIEW COUNT
        # =================================================

        review_tag = soup.select_one(
            ".review-cnt"
        )

        if review_tag:

            result["review_count"] = extract_number(
                review_tag.get_text()
            )

        # =================================================
        # ADDRESS
        # =================================================

        addr_spans = soup.select(
            ".vendor-address span"
        )

        clean_addr = []

        for sp in addr_spans:

            txt = clean_text(
                sp.get_text()
            )

            if (
                txt
                and "more city" not in txt
                and "View on Map" not in txt
            ):
                clean_addr.append(txt)

        if clean_addr:

            parts = clean_addr[0].split(",")

            if len(parts) >= 1:
                result["address"]["area"] = (
                    parts[0].strip()
                )

            if len(parts) >= 2:
                result["address"]["city"] = (
                    parts[-1].strip()
                )

        # =================================================
        # ADDITIONAL CITIES
        # =================================================

        city_tip = soup.select_one(
            "#tooltip-cities"
        )

        if city_tip:

            city_text = clean_text(
                city_tip.get_text()
            )

            if city_text:

                result["additional_cities"].append(
                    city_text
                )

        # =================================================
        # PRICING
        # =================================================

        pricing_box = soup.select_one(
            ".VendorPricing"
        )

        if pricing_box:

            price_text = clean_text(
                pricing_box.get_text(" ")
            )

            result["pricing"][
                "starting_price"
            ] = extract_number(price_text)

            label_tag = pricing_box.select_one(
                ".text-secondary"
            )

            if label_tag:

                result["pricing"][
                    "pricing_label"
                ] = clean_text(
                    label_tag.get_text()
                )

        # =================================================
        # ABOUT
        # =================================================

        about_section = soup.select_one(
            ".AboutSection .info"
        )

        if about_section:

            paragraphs = about_section.select("p")

            if paragraphs:

                result["about"] = clean_text(
                    paragraphs[0].get_text()
                )

        # =================================================
        # SERVICES
        # =================================================

        services_heading = soup.find(
            string=re.compile(
                r"Services provided",
                re.I
            )
        )

        if services_heading:

            ul = (
                services_heading
                .find_parent()
                .find_next("ul")
            )

            if ul:

                for li in ul.select("li"):

                    txt = clean_text(
                        li.get_text()
                    )

                    if txt:

                        result["services"].append(
                            txt
                        )

        # =================================================
        # PLANNED CITIES
        # =================================================

        planned_heading = soup.find(
            string=re.compile(
                r"planned weddings in cities",
                re.I
            )
        )

        if planned_heading:

            ul = (
                planned_heading
                .find_parent()
                .find_next("ul")
            )

            if ul:

                for li in ul.select("li"):

                    txt = clean_text(
                        li.get_text()
                    )

                    if txt:

                        result[
                            "planned_cities"
                        ].append(txt)

        # =================================================
        # FAQ DETAILS
        # =================================================

        faq_boxes = soup.select(
            ".faqs .faq"
        )

        for faq in faq_boxes:

            title_tag = faq.select_one(
                ".text-bold"
            )

            value_tag = faq.select_one(
                ".text-tertiary"
            )

            if not title_tag or not value_tag:
                continue

            key = clean_text(
                title_tag.get_text()
            ).lower()

            value = clean_text(
                value_tag.get_text()
            )

            result["business_details"][
                key
            ] = value

        # =================================================
        # STATS
        # =================================================

        tab_texts = soup.select(
            ".MuiTab-wrapper-27"
        )

        for txt in tab_texts:

            value = clean_text(
                txt.get_text()
            )

            if not value:
                continue

            if "Portfolio" in value:

                result["stats"][
                    "portfolio_images"
                ] = extract_number(value)

            elif "Albums" in value:

                result["stats"][
                    "albums"
                ] = extract_number(value)

            elif "Videos" in value:

                result["stats"][
                    "videos"
                ] = extract_number(value)

        # =================================================
        # ALBUMS
        # =================================================

        result["albums"] = extract_albums(
            soup,
            url
        )

        # =================================================
        # VIDEOS
        # =================================================

        result["videos"] = extract_videos(
            url
        )

        # =================================================
        # RATING DISTRIBUTION
        # =================================================

        rows = soup.select(".rating-row")

        for row in rows:

            try:

                rating_num = row.select_one(
                    ".rating-number"
                )

                review_text = row.select_one(
                    ".fixed-width-right"
                )

                if (
                    not rating_num
                    or not review_text
                ):
                    continue

                star = clean_text(
                    rating_num.get_text()
                )

                count = extract_number(
                    review_text.get_text()
                )

                result["rating_distribution"][
                    star
                ] = count

            except:
                pass

        # =================================================
        # LAST REVIEW UPDATED
        # =================================================

        updated_tag = soup.find(
            string=re.compile(
                r"Last Review Updated",
                re.I
            )
        )

        if updated_tag:

            result["last_review_updated"] = (
                clean_text(updated_tag)
                .replace(
                    "Last Review Updated on",
                    ""
                )
                .strip()
            )

    except Exception as e:

        print("Profile parse failed")
        print(str(e))

    return result


# =========================================================
# LOAD URLS
# =========================================================

with open(
    INPUT_JSON_FILE,
    "r",
    encoding="utf-8"
) as f:

    input_data = json.load(f)


# =========================================================
# EXTRACT URLS
# =========================================================

urls = []

for item in input_data:

    if isinstance(item, str):

        urls.append(item)

    elif isinstance(item, dict):

        url = item.get("url")

        if url:
            urls.append(url)


print(f"Loaded {len(urls)} URLs")


# =========================================================
# SCRAPE
# =========================================================

results = []

for index, url in enumerate(urls, start=1):

    print("\n================================")
    print(f"[{index}/{len(urls)}]")
    print(url)

    data = parse_profile(url)

    results.append(data)

    # =====================================================
    # SAVE PROGRESS
    # =====================================================

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

    print(f"Saved progress ({index})")

    time.sleep(REQUEST_DELAY)


# =========================================================
# DONE
# =========================================================

print("\n================================")
print("SCRAPING COMPLETED")
print(f"Saved: {OUTPUT_JSON_FILE}")
print("================================")