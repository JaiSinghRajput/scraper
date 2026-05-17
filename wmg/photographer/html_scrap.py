# =========================
# CONFIG
# =========================

INPUT_HTML_FILE = "data/wedding-photographer.html"
OUTPUT_JSON_FILE = "1st_Page_photographers.json"

# Prefix for profile URLs
BASE_URL = "https://www.wedmegood.com"


# =========================
# IMPORTS
# =========================

from bs4 import BeautifulSoup
import json
import re


# =========================
# LOAD HTML
# =========================

with open(INPUT_HTML_FILE, "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")


# =========================
# HELPERS
# =========================

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


# =========================
# FIND ALL CARDS
# =========================

cards = soup.select("div[id^='card']")

results = []


# =========================
# PARSE EACH CARD
# =========================

for card in cards:

    data = {
        "vendor_name": None,
        "price_per_day": None,
        "work": None,
        "bottom_fields": [],
        "address": None,
        "url": None,
        "type": None,
    }

    # -------------------------
    # Vendor Name
    # -------------------------
    vendor_tag = card.select_one("a.vendor-detail.text-bold.h6")

    if vendor_tag:
        data["vendor_name"] = clean_text(vendor_tag.get_text())

    # -------------------------
    # URL
    # -------------------------
    profile_link = card.select_one('a[href*="/profile/"]')

    if profile_link:
        href = profile_link.get("href")

        if href:
            data["url"] = BASE_URL + href

    # -------------------------
    # Address
    # -------------------------
    location_tag = card.select_one("p.vendor-detail")

    if location_tag:
        data["address"] = clean_text(location_tag.get_text(separator=", "))

    # -------------------------
    # Work Type
    # -------------------------
    work_tag = card.select_one(".vendor-price .text-secondary")

    if work_tag:
        work_text = clean_text(work_tag.get_text())
        data["work"] = detect_work_type(work_text)

    # -------------------------
    # Price Per Day
    # -------------------------
    price_tag = card.select_one(".vendor-price .text-bold span:last-child")

    if price_tag:
        price_text = clean_text(price_tag.get_text())

        if price_text:
            price_text = price_text.replace(",", "")
            try:
                data["price_per_day"] = int(price_text)
            except:
                data["price_per_day"] = price_text

    # -------------------------
    # Type (Handpicked / Popular)
    # -------------------------
    card_html = str(card).lower()

    if "handpicked" in card_html:
        data["type"] = "Handpicked"
    elif "popular" in card_html:
        data["type"] = "Popular"

    # -------------------------
    # Bottom LI Fields
    # -------------------------
    li_tags = card.select("ul li")

    bottom_fields = []

    for li in li_tags:
        text = clean_text(li.get_text())

        if text:
            bottom_fields.append(text)

    data["bottom_fields"] = bottom_fields

    # -------------------------
    # Save
    # -------------------------
    results.append(data)


# =========================
# WRITE JSON
# =========================

with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4, ensure_ascii=False)

print(f"Saved {len(results)} vendors to {OUTPUT_JSON_FILE}")