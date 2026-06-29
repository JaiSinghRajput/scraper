import pandas as pd
import json
import re
from rapidfuzz import process, fuzz

# Files
INPUT_CSV = "punjab.csv"
CITY_JSON = "punjab.json"
OUTPUT_CSV = "output_punjab.csv"
UNMATCHED_CSV = "unmatched_cities_punjab.csv"

FUZZY_THRESHOLD = 85

# ---------------------------
# Load cities
# ---------------------------

with open(CITY_JSON, "r", encoding="utf-8") as f:
    cities = json.load(f)

city_lookup = {
    city["name"].strip().lower(): city["id"]
    for city in cities
}

city_names = list(city_lookup.keys())

# ---------------------------
# Helpers
# ---------------------------

def normalize(text):
    if pd.isna(text):
        return ""

    text = str(text).lower()

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def exact_city_match(text):
    """
    Direct city name match.
    """
    text = normalize(text)

    if text in city_lookup:
        return city_lookup[text]

    return ""


def address_phrase_match(address):
    """
    Exact phrase search in address.
    Longest city names first.
    """

    address = normalize(address)

    for city_name in sorted(city_names, key=len, reverse=True):
        pattern = r"\b" + re.escape(city_name) + r"\b"

        if re.search(pattern, address):
            return city_lookup[city_name]

    return ""


def generate_ngrams(words, max_size=4):
    """
    Creates:
    rajouri
    rajouri garden

    south
    south delhi

    etc.
    """

    phrases = []

    for n in range(1, max_size + 1):
        for i in range(len(words) - n + 1):
            phrases.append(" ".join(words[i:i+n]))

    return phrases


def fuzzy_address_match(address):
    """
    Fuzzy match city names against address phrases.
    """

    address = normalize(address)

    if not address:
        return ""

    words = address.split()

    candidates = generate_ngrams(words, max_size=4)

    best_city = None
    best_score = 0

    for phrase in candidates:

        match = process.extractOne(
            phrase,
            city_names,
            scorer=fuzz.token_sort_ratio
        )

        if not match:
            continue

        city_name, score, _ = match

        if score > best_score:
            best_score = score
            best_city = city_name

    if best_score >= FUZZY_THRESHOLD:
        return city_lookup[best_city]

    return ""


def get_vendor_city(row):

    vendor_city_name = normalize(row.get("vendor_city_name", ""))
    vendor_address = row.get("vendor_address", "")

    # --------------------------------
    # 1. Exact city name
    # --------------------------------

    city_id = exact_city_match(vendor_city_name)

    if city_id:
        return city_id

    # --------------------------------
    # 2. Exact address phrase
    # --------------------------------

    city_id = address_phrase_match(vendor_address)

    if city_id:
        return city_id

    # --------------------------------
    # 3. Fuzzy address lookup
    # --------------------------------

    city_id = fuzzy_address_match(vendor_address)

    if city_id:
        return city_id

    return ""


# ---------------------------
# Read CSV
# ---------------------------

df = pd.read_csv(INPUT_CSV, dtype=str)

# Fill vendor_city

df["vendor_city"] = df.apply(get_vendor_city, axis=1)

# Split

matched_df = df[df["vendor_city"] != ""]
unmatched_df = df[df["vendor_city"] == ""]

# Save

matched_df.to_csv(OUTPUT_CSV, index=False)
unmatched_df.to_csv(UNMATCHED_CSV, index=False)

print(f"Matched rows: {len(matched_df)}")
print(f"Unmatched rows: {len(unmatched_df)}")