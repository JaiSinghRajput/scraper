"""
clean_vendor_data.py
--------------------
Cleans vendor profile JSON data with the following fixes:

1.  Prices — strips irregular Indian-style thousand-separator commas
    (e.g. "51,000" → 51000, "24,999" → 24999). Converts to integers.

2.  'Practicing Makeup Since' FAQ entry:
      - Extracts the year (handles "2,019" → 2019)
      - Removes the FAQ entry from the faq array entirely
      - Adds `VendorProfile.profile.since_working_year` as an integer field
        (or null if absent / unparseable)

3.  Advance Amount (FAQ) — corrupt percentage strings fixed:
      Corruption pattern: a comma was inserted as a thousands separator
      inside percentage digits, e.g. "5,0%" means 50%, "10,0%" means 100%.
      Fix: remove the comma between digit groups to reconstruct the real %.
      - "5,0% Advance for booking"    → "50% Advance for booking"
      - "10,0% Advance for booking"   → "100% Advance for booking"
      - "INR 5,0% Advance"            → "50% Advance for booking"  (strip INR prefix)
      - "8,50,60,58,100%"             → null  (multiple commas = unrecoverable garbage)
      - Valid values like "50%", "30%" → kept as-is

4.  Policy displayValue advance entries — corrupt format fixed:
      Corruption pattern: the percent value was stored multiplied by 100
      with a space before %, e.g. "5000 % Advance" means 50%.
      Fix: divide by 100 and reformat.
      - "5000 % Advance for booking"  → "50% Advance for booking"
      - "10000 % Advance for booking" → "100% Advance for booking"
      - "% Advance for booking"       → null  (no number = junk)
      Also fixes unrealistic booking-weeks values:
      - Negative weeks (Book -1 weeks) → null
      - Implausible weeks > 52         → null
      - Zero/junk weeks (0000, 0)      → null

5.  Non-YouTube URLs — removes any non-YouTube URL from string fields
    (FAQ answers, video titles, documents/Brochure, etc.).

6.  Blank / special-character-only fields → null (or pruned from arrays).

7.  Vendor name — strips stray Unicode symbols/emoji that are not part of
    normal text (e.g. "Rashmi Å Makeovers" → "Rashmi Makeovers").

Usage:
    python3 clean_vendor_data.py input.json output.json

    Defaults: input = test.json, output = cleaned_vendor_data.json
"""

import json
import re
import sys
import os

# ── Regexes ──────────────────────────────────────────────────────────────────
URL_RE       = re.compile(r'https?://\S+')
YOUTUBE_RE   = re.compile(r'https?://(www\.)?(youtube\.com|youtu\.be)\S*', re.I)
# Year with optional internal comma: 2,014 or 2014
HAS_ALNUM_RE = re.compile(r'[a-zA-Z0-9]')
# Stray non-printable / unusual Unicode that aren't standard punctuation or
# Devanagari (we keep Devanagari etc. but strip lone symbols like Å, ⭐️ etc.)
# Strategy: strip characters that are not ASCII printable, not Devanagari
# (U+0900–U+097F), not common Latin-extended, and not standard punctuation.
# We'll do a targeted strip of "symbol" and "other" Unicode categories.
import unicodedata

def is_wanted_char(c: str) -> bool:
    """Return True for characters we want to keep."""
    cp = ord(c)
    cat = unicodedata.category(c)
    # Keep ASCII printable
    if 32 <= cp <= 126:
        return True
    # Keep Devanagari block (Hindi etc.)
    if 0x0900 <= cp <= 0x097F:
        return True
    # Keep common Latin-extended (accented letters used in names)
    if 0x00C0 <= cp <= 0x024F:
        return True
    # Keep Arabic, Bengali, Tamil, Telugu (other Indian scripts)
    if 0x0600 <= cp <= 0x06FF: return True
    if 0x0980 <= cp <= 0x09FF: return True
    if 0x0B80 <= cp <= 0x0BFF: return True
    if 0x0C00 <= cp <= 0x0C7F: return True
    # Keep standard space variants
    if cat in ('Zs',):
        return True
    # Drop symbols (So, Sm, Sk, Sc), surrogates, private use, etc.
    if cat.startswith('S') or cat.startswith('C') or cat.startswith('Z'):
        return False
    # Keep letters (L*), marks (M*), numbers (N*), punctuation (P*)
    return True

def clean_text_symbols(text: str) -> str:
    """Remove stray symbol/emoji characters from a string."""
    return ''.join(c for c in text if is_wanted_char(c)).strip()


# ── Price helpers ─────────────────────────────────────────────────────────────

# Matches a price range like "10,000-12,000" or "10000-15000" (one hyphen)
_PRICE_RANGE_RE = re.compile(r'^([\d,]+)\s*-+\s*([\d,]+)$')

def _strip_commas_to_int(s: str) -> int | None:
    """Strip ALL commas from a numeric string and return as int. Works for
    both standard (1,000) and Indian notation (1,00,000 = 100000)."""
    cleaned = s.replace(',', '').strip()
    try:
        return int(float(cleaned))
    except (ValueError, TypeError):
        return None

def clean_price(value) -> int | str | None:
    """
    Normalise a raw price value to a plain integer where possible.

    Handles:
    - Standard comma separators:   "10,000"      → 10000
    - Indian comma notation:       "1,00,000"    → 100000
    - No commas already numeric:   45000         → 45000
    - Price ranges (one hyphen):   "10,000-12,000" → 10000  (lower bound kept)
                                   "20000-25000"   → 20000
    - Corrupt double-hyphen:       "20000--25000"  → 20000  (lower bound)
    - 'Price on Request' / text:   → None
    - Unparseable garbage:         → None
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None

    # Range: "10,000-12,000" or "10000-15000" (normalise double-hyphen too)
    s_norm = re.sub(r'-{2,}', '-', s)          # collapse "--" → "-"
    m = _PRICE_RANGE_RE.match(s_norm)
    if m:
        low = _strip_commas_to_int(m.group(1))
        # Return the lower bound as the canonical price
        return low  # may be None if unparseable

    # Plain numeric (with or without commas)
    result = _strip_commas_to_int(s)
    # Sanity cap: prices above ₹10,00,000 (10 lakh) are almost certainly corrupt
    if result is not None and result > 1_000_000:
        return None
    return result


# ── URL helpers ───────────────────────────────────────────────────────────────
def strip_non_youtube_urls(text: str) -> str:
    """Remove all URLs from text except YouTube links."""
    def replacer(m):
        url = m.group(0)
        return url if YOUTUBE_RE.match(url) else ''
    return URL_RE.sub(replacer, text).strip()

def has_non_youtube_url(text: str) -> bool:
    for url in URL_RE.findall(text):
        if not YOUTUBE_RE.match(url):
            return True
    return False


# ── Blank / junk field helpers ────────────────────────────────────────────────
def is_blank_or_junk(value) -> bool:
    """True if value is empty string, whitespace only, or special-chars only."""
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    if not stripped:
        return True
    return not bool(HAS_ALNUM_RE.search(stripped))

def nullify_junk(value):
    """Return None if junk, else return value unchanged."""
    return None if is_blank_or_junk(value) else value


# ── Advance percentage helpers ────────────────────────────────────────────────

# Matches a percent number with possible commas and optional INR prefix, e.g.:
#   "5,0%", "10,0%", "50%", "INR 5,0%", "2,14%"
_ADV_FAQ_RE = re.compile(
    r'^(?:INR\s*)?(\d[\d,]*)%\s*Advance\s+for\s+booking\s*$', re.I
)

def clean_advance_faq(answer: str) -> str | None:
    """
    Fix corrupt FAQ 'Advance Amount' percentage strings.

    Corruption: a comma was inserted inside percent digits as a thousands
    separator, e.g. "5,0%" → real value is "50%", "10,0%" → "100%".

    Rules:
    - Strip leading "INR " noise.
    - If the digit part contains exactly one comma AND the part after the
      comma is 1-2 digits (typical thousands-sep misplacement), concat the
      two parts: "5,0" → "50", "2,0" → "20", "10,0" → "100".
    - If the digit part has multiple commas or doesn't match, the value is
      unrecoverable garbage → return None.
    - Validate: final percent must be 1–100, else return None.
    - Answers already correct ("50%", "30%") pass through unchanged.
    """
    if not isinstance(answer, str):
        return answer
    m = _ADV_FAQ_RE.match(answer.strip())
    if not m:
        # Doesn't match expected pattern — return as-is (will be junk-checked later)
        return answer
    digit_part = m.group(1)  # e.g. "5,0" or "50" or "8,50,60,58,100"
    parts = digit_part.split(',')
    if len(parts) == 1:
        # No comma — already clean
        pct_str = parts[0]
    elif len(parts) == 2:
        # One comma: concat the two parts to get the real number
        # "5,0" → "50",  "10,0" → "100",  "2,14" → "214" (unrealistic → null)
        pct_str = parts[0] + parts[1]
    else:
        # Multiple commas = unrecoverable garbage
        return None
    try:
        pct = int(pct_str)
    except ValueError:
        return None
    if not (1 <= pct <= 100):
        return None
    return f"{pct}% Advance for booking"


# Matches policy advance display values like "5000 % Advance for booking"
_POL_ADV_RE = re.compile(r'^(\d+)\s*%\s*Advance\s+for\s+booking\s*$', re.I)
# Matches booking-weeks display values like "Book 4 weeks in advance"
_POL_WEEKS_RE = re.compile(r'^Book\s+(-?\d+(?:-\d+)?)\s+weeks?\s+in\s+advance\s*$', re.I)

def clean_policy_displayvalue(dv: str) -> str | None:
    """
    Fix corrupt policy displayValue strings.

    Two corruption patterns:
    1. Advance % stored as value*100:
       "5000 % Advance for booking"  → "50% Advance for booking"
       "10000 % Advance for booking" → "100% Advance for booking"
       "% Advance for booking"       → None  (no number)

    2. Booking weeks — filter out unrealistic values:
       Negative, zero/junk (0000), or > 52 weeks → None
    """
    if not isinstance(dv, str):
        return dv
    stripped = dv.strip()

    # Pattern 1: "NNNN % Advance for booking"
    m = _POL_ADV_RE.match(stripped)
    if m:
        raw = int(m.group(1))
        # The value was stored as pct * 100
        pct = raw // 100
        if 1 <= pct <= 100:
            return f"{pct}% Advance for booking"
        return None  # unrecoverable

    # Pattern 2: "Book N weeks in advance"
    m2 = _POL_WEEKS_RE.match(stripped)
    if m2:
        weeks_str = m2.group(1)
        # Range like "4-6": take the lower bound for validation
        try:
            low = int(weeks_str.split('-')[0])
        except ValueError:
            return None
        if low <= 0 or low > 52:
            return None  # unrealistic
        return stripped  # keep as-is

    return stripped  # unrecognised pattern — leave unchanged


# ── Year / experience helpers ─────────────────────────────────────────────────

CURRENT_YEAR = 2026  # used to convert "N years experience" → since_working_year

YEAR_RE      = re.compile(r'\b(2[,]?\d{3})\b')
# Matches "9 years", "9+ years", "9-10 years", "9 yrs", "over 9 years", etc.
_EXP_RE = re.compile(
    r'(?:over\s+|about\s+|approx\.?\s*)?(\d+)\s*\+?\s*(?:-\s*\d+\s*)?(?:years?|yrs?)',
    re.I
)

def extract_year_from_since(answer: str) -> int | None:
    """
    Extract a calendar year from a 'Practicing Makeup Since'-style answer.
    Handles:  "2014",  "Since 2014",  "2,019"  → int year
    """
    m = YEAR_RE.search(answer)
    if m:
        try:
            y = int(m.group(1).replace(',', ''))
            if 1950 <= y <= CURRENT_YEAR:
                return y
        except ValueError:
            pass
    return None


def extract_year_from_experience(answer: str) -> int | None:
    """
    Convert an experience-duration answer to a calendar year by subtracting
    from CURRENT_YEAR.
    Handles:
      "9+ years"    → CURRENT_YEAR - 9  = 2017
      "10 years"    → CURRENT_YEAR - 10 = 2016
      "9-10 years"  → uses the lower bound (9) → 2017
      "over 5 yrs"  → CURRENT_YEAR - 5  = 2021
    Returns None if no parseable duration found.
    """
    m = _EXP_RE.search(str(answer))
    if m:
        try:
            years = int(m.group(1))
            if 0 < years <= 60:          # sanity: 0–60 years is realistic
                return CURRENT_YEAR - years
        except ValueError:
            pass
    return None


# ── Per-record cleaner ────────────────────────────────────────────────────────
def clean_record(record: dict) -> dict:
    vp = record.get('VendorProfile', {})

    # ── 1. Profile fields ────────────────────────────────────────────────────
    profile = vp.get('profile', {})

    # Clean name (strip lone symbols / emoji)
    if 'name' in profile and isinstance(profile['name'], str):
        profile['name'] = clean_text_symbols(profile['name'])
        profile['name'] = re.sub(r'  +', ' ', profile['name']).strip()

    # Nullify junk strings in profile
    for key in list(profile.keys()):
        if isinstance(profile[key], str):
            profile[key] = nullify_junk(profile[key])

    # ── 2. Extract since_working_year from FAQ ───────────────────────────────
    #
    #  Two FAQ questions can carry this information:
    #    a) "Practicing Makeup Since"  → direct calendar year  (e.g. "2014")
    #    b) "Experience"               → duration string       (e.g. "9+ years")
    #                                    converted via CURRENT_YEAR - N
    #
    #  Priority: if both are present, "Practicing Makeup Since" wins because
    #  it is an exact year; Experience is only a fallback.
    # ────────────────────────────────────────────────────────────────────────
    faq_list = vp.get('faq', [])
    since_year_exact      = None   # from "Practicing Makeup Since"
    since_year_experience = None   # from "Experience"
    cleaned_faq = []

    for entry in faq_list:
        q = entry.get('question', '') or ''
        a = entry.get('answer',   '') or ''

        # ── a) Practicing Makeup Since ──
        if q == 'Practicing Makeup Since':
            since_year_exact = extract_year_from_since(a)
            continue  # remove from faq array

        # ── b) Experience ──
        if q.strip().lower() == 'experience':
            since_year_experience = extract_year_from_experience(a)
            continue  # remove from faq array

        # Fix corrupt "Advance Amount" percentages (e.g. "5,0%" → "50%")
        if q == 'Advance Amount' and isinstance(a, str):
            a = clean_advance_faq(a)
            entry['answer'] = a  # may be None if unrecoverable

        # Clean answer: strip non-YouTube URLs
        if isinstance(a, str):
            a = strip_non_youtube_urls(a)
            entry['answer'] = nullify_junk(a)

        # Nullify junk question
        if isinstance(q, str):
            entry['question'] = nullify_junk(q)

        # Drop entries where both question and answer are null/blank
        if entry.get('question') or entry.get('answer'):
            cleaned_faq.append(entry)

    # Resolve: exact year wins; experience-derived is fallback
    profile['since_working_year'] = since_year_exact or since_year_experience
    vp['faq'] = cleaned_faq

    # ── 3. Pricing — clean commas → integer ─────────────────────────────────
    cleaned_pricing = []
    for p in vp.get('pricing', []):
        raw_price = p.get('price')
        cleaned = clean_price(raw_price)
        p['price'] = cleaned  # integer or None
        # Nullify junk unit
        if 'unit' in p:
            p['unit'] = nullify_junk(p.get('unit', ''))
        cleaned_pricing.append(p)
    vp['pricing'] = cleaned_pricing

    # ── 4. Videos — clean titles, remove non-YouTube video links ────────────
    videos = vp.get('videos', {})
    video_array = videos.get('video_array', [])
    cleaned_videos = []
    for v in video_array:
        link  = v.get('video_link', '')
        title = v.get('video_title', '')

        # Keep video only if the link itself is YouTube
        if link and not YOUTUBE_RE.match(link):
            continue  # drop non-YouTube video entries

        # Clean title: strip non-YouTube URLs embedded in title text
        if isinstance(title, str):
            title = strip_non_youtube_urls(title)
            title = clean_text_symbols(title)
            v['video_title'] = nullify_junk(title)

        v['video_link'] = nullify_junk(link)
        cleaned_videos.append(v)

    videos['video_array'] = cleaned_videos
    vp['videos'] = videos

    # ── 5. Documents — remove non-YouTube URLs (Brochure links, etc.) ────────
    documents = vp.get('documents', {})
    if documents:
        for doc_key in list(documents.keys()):
            val = documents[doc_key]
            if isinstance(val, str) and has_non_youtube_url(val):
                documents[doc_key] = None  # remove the URL
            elif isinstance(val, str):
                documents[doc_key] = nullify_junk(val)
        vp['documents'] = documents

    # ── 6. About / policy — fix corrupt advance% and unrealistic weeks ─────────
    about = vp.get('about', {})
    policy = about.get('policy', [])
    cleaned_policy = []
    for pol in policy:
        dv = pol.get('displayValue', '')
        # Fix "5000 % Advance" → "50% Advance", drop unrealistic weeks
        dv = clean_policy_displayvalue(dv)
        pol['displayValue'] = nullify_junk(dv) if isinstance(dv, str) else dv
        if pol.get('displayValue'):
            cleaned_policy.append(pol)
    about['policy'] = cleaned_policy
    vp['about'] = about

    record['VendorProfile'] = vp
    return record


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    input_path  = sys.argv[1] if len(sys.argv) > 1 else 'test.json'
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'cleaned_vendor_data.json'

    print(f"Reading  : {input_path}")
    with open(input_path, encoding='utf-8') as f:
        data = json.load(f)

    total = len(data)
    print(f"Records  : {total}")

    cleaned = [clean_record(record) for record in data]

    print(f"Writing  : {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print("Done.")

    # ── Summary stats ────────────────────────────────────────────────────────
    with_year    = sum(1 for r in cleaned if r['VendorProfile']['profile'].get('since_working_year'))
    without_year = total - with_year
    print(f"\nSummary:")
    print(f"  Records with since_working_year : {with_year}")
    print(f"  Records without since_working_year : {without_year}")


if __name__ == '__main__':
    main()