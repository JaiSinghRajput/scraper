# =========================================================
# WEDDING VENUES SCRAPER (PLAYWRIGHT)
# =========================================================

BASE_LIST_URL = (
    "https://www.wedmegood.com/vendors/telangana/wedding-venues/"
)

START_PAGE = 82
END_PAGE = 103

OUTPUT_JSON_FILE = "wedding_venues_telangana_cards.json"
# TOR_PROXY = "socks5://127.0.0.1:9050"

REQUEST_DELAY = 5
BROWSER_PROFILE_DIR = "./browser_profile"
HEADLESS = False

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from html_scrap import parse_cards_from_soup
import json
import time
import random
import os


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


all_results = []
existing_urls = set()

if os.path.exists(OUTPUT_JSON_FILE):
    try:
        with open(OUTPUT_JSON_FILE, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            if isinstance(existing_data, list):
                all_results = existing_data
                for item in existing_data:
                    item_url = item.get("url")
                    if item_url:
                        existing_urls.add(item_url)

        print(f"Loaded existing venues: {len(existing_urls)}")
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

        vendor_lists = soup.select(".VendorList")

        if not vendor_lists:
            print("No VendorList found")
            return

        cards_scope = vendor_lists[0]
        parsed_items = parse_cards_from_soup(cards_scope)

        for item in parsed_items:
            try:
                if not item.get("vendor_name"):
                    continue

                item_url = item.get("url")

                if item_url and item_url in existing_urls:
                    continue

                if item_url:
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
        #  proxy={
        #     "server": TOR_PROXY
        # },
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
                print(f"FAILED PAGE {current_page}")
                print(str(e))
                time.sleep(10)

    finally:
        context.close()

print("SCRAPING COMPLETED")
print(f"Saved {len(all_results)} venues")
