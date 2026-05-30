# =========================================================
# WEDDING PLANNERS SCRAPER (PLAYWRIGHT)
# =========================================================

BASE_LIST_URL = "https://www.wedmegood.com/vendors/all/wedding-planners/"

START_PAGE = 1
END_PAGE = 5

OUTPUT_JSON_FILE = "wedding_planners.json"

REQUEST_DELAY = 5
BROWSER_PROFILE_DIR = "./browser_profile"
HEADLESS = False

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re
import time
import random
import os

def clean_text(text):
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip()

def auto_scroll(page):
    while True:
        old_height = page.evaluate("document.body.scrollHeight")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2500)
        new_height = page.evaluate("document.body.scrollHeight")
        if old_height == new_height:
            break
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(1000)

def parse_card(card):

    BASE_URL = "https://www.wedmegood.com"

    data = {
        "vendor_name": None,
        "url": None,
        "image_url": None,
        "area": None,
        "city": None,
        "rating": None,
        "reviews_count": None,
        "planning_fee": None,
        "pricing_label": None,
        "about_preview": None,
        "features": [],
        "verified": False,
        "type": None
    }

    vendor_tag = card.select_one("a.vendor-detail.text-bold.h6")
    if vendor_tag:
        data["vendor_name"] = clean_text(vendor_tag.get_text())

    profile_link = card.select_one('a[href*="/profile/"]')
    if profile_link:
        href = profile_link.get("href")
        if href:
            data["url"] = href if href.startswith("http") else BASE_URL + href

    image_tag = card.select_one(".vendor-picture img.object-fit-cover")
    if image_tag:
        data["image_url"] = image_tag.get("src")

    rating_tag = card.select_one(".rating-new-5")
    if rating_tag:
        m = re.search(r'(\d+(\.\d+)?)', rating_tag.get_text())
        if m:
            data["rating"] = float(m.group(1))

    reviews_tag = card.select_one(".review-cnt")
    if reviews_tag:
        m = re.search(r'(\d+)', reviews_tag.get_text())
        if m:
            data["reviews_count"] = int(m.group(1))

    location_tag = card.select_one(".info-icon.text-tertiary .vendor-detail")
    if location_tag:
        vals = []
        for span in location_tag.select("span"):
            txt = clean_text(span.get_text())
            if txt and txt != ",":
                vals.append(txt)

        if len(vals) == 1:
            data["city"] = vals[0]
        elif len(vals) >= 2:
            data["area"] = vals[0]
            data["city"] = vals[-1]

    label = card.select_one(".text-secondary")
    if label:
        data["pricing_label"] = clean_text(label.get_text())

    price_tag = card.select_one(".vendor-price .text-bold")
    if price_tag:
        m = re.search(r'([\d,]+)', clean_text(price_tag.get_text()))
        if m:
            data["planning_fee"] = m.group(1).replace(",", "")

    for tip in card.select("div.__react_component_tooltip"):
        txt = clean_text(tip.get_text(" ", strip=True))
        if txt and "About vendor" in txt:
            data["about_preview"] = txt.replace("About vendor", "").strip()
            break

    features = []
    for chip in card.select('div[style*="background-color"] p'):
        txt = clean_text(chip.get_text())
        if txt:
            features.append(txt)
    data["features"] = list(dict.fromkeys(features))

    data["verified"] = card.select_one('img[alt="verified_icon"]') is not None

    html_lower = str(card).lower()
    if "paid vendor" in html_lower:
        data["type"] = "Paid"
    elif "handpicked" in html_lower:
        data["type"] = "Handpicked"
    elif "popular" in html_lower:
        data["type"] = "Popular"

    return data

all_results = []
existing_urls = set()

if os.path.exists(OUTPUT_JSON_FILE):
    try:
        with open(OUTPUT_JSON_FILE, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            if isinstance(existing_data, list):
                all_results = existing_data
                for item in existing_data:
                    if item.get("url"):
                        existing_urls.add(item["url"])
    except Exception as e:
        print(e)

def scrape_page(context, page_number):

    global all_results, existing_urls

    url = f"{BASE_LIST_URL}?page={page_number}"
    print(f"Scraping page {page_number}: {url}")

    page = context.new_page()

    try:
        page.goto(url, timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        auto_scroll(page)

        html = page.content()

        soup = BeautifulSoup(html, "html.parser")

        cards = soup.find_all("div", id=re.compile(r"^card\d+$"))

        print("Found cards:", len(cards))

        for card in cards:
            try:
                item = parse_card(card)

                if not item["vendor_name"]:
                    continue

                item_url = item.get("url")

                if item_url in existing_urls:
                    continue

                existing_urls.add(item_url)
                all_results.append(item)

                print("Added:", item["vendor_name"])

            except Exception as e:
                print("Card parse error:", e)

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

        print("Progress Saved")

    finally:
        page.close()

with sync_playwright() as p:

    context = p.firefox.launch_persistent_context(
        user_data_dir=BROWSER_PROFILE_DIR,
        headless=HEADLESS,
        viewport={"width": 1400, "height": 900},
        locale="en-US",
        timezone_id="Asia/Kolkata"
    )

    try:
        current_page = START_PAGE

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

                time.sleep(sleep_time)

            except Exception as e:

                print(
                    f"FAILED PAGE {current_page}"
                )

                print(str(e))

                time.sleep(10)

    finally:

        context.close()

print("SCRAPING COMPLETED")
print(f"Saved {len(all_results)} vendors")
