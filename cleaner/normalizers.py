"""
Normalization helpers.

This module contains only PURE functions.

Input  -> value
Output -> normalized value

No JSON traversal should happen here.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from .config import (
    ALLOWED_VIDEO_DOMAINS,
    CURRENT_YEAR,
    PRICE_PREFIXES,
    SINCE_WORKING_QUESTIONS,
    YEAR_REGEX,
)

from .utils import (
    clean_text,
    normalize_whitespace,
)

##############################################################################
# FAQ Question Normalization
##############################################################################

QUESTION_REPLACEMENTS = {
    "working since": "working since",
    "since working": "working since",
    "working from": "working since",
    "experience": "experience",
    "years of experience": "experience",
    "practicing makeup since": "working since",
    "practicing since": "working since",
    "business since": "working since",
    "started in": "working since",
    "established in": "working since",
}


def normalize_question(question: str) -> str:
    """
    Normalize FAQ question names.

    Example:

        Products used
        products Used
        PRODUCTS USED

    ↓

        Products Used
    """

    if not isinstance(question, str):
        return ""

    question = clean_text(question)

    question = question.lower()

    question = re.sub(r"[:\-]+$", "", question)

    question = question.strip()

    if question in QUESTION_REPLACEMENTS:
        question = QUESTION_REPLACEMENTS[question]

    return question.title()


##############################################################################
# FAQ Answer Normalization
##############################################################################

def normalize_answer(answer: str) -> str:

    if not isinstance(answer, str):
        return answer

    answer = clean_text(answer)

    answer = re.sub(r"\s*:\s*", ": ", answer)

    answer = re.sub(r"\s*,\s*", ", ", answer)

    answer = normalize_whitespace(answer)

    return answer


##############################################################################
# Since Working Extraction
##############################################################################

def extract_year(value: str):
    """
    Extract year from arbitrary text.

    Examples

    2014

    Working Since 2015

    Practicing Makeup Since 2,014

    Since 2018

    Established in 2006
    """

    if not isinstance(value, str):
        return None

    value = clean_text(value)

    match = re.search(YEAR_REGEX, value)

    if not match:
        return None

    year = int(match.group(1) + match.group(2))

    if year < 1900:
        return None

    if year > CURRENT_YEAR:
        return None

    return year


def is_since_working_question(question: str) -> bool:

    if not isinstance(question, str):
        return False

    q = clean_text(question).lower()

    return q in SINCE_WORKING_QUESTIONS


##############################################################################
# URL Normalization
##############################################################################

def normalize_url(url: str):

    if not isinstance(url, str):
        return None

    url = clean_text(url)

    if url == "":
        return None

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url


def is_allowed_video_url(url: str):

    url = normalize_url(url)

    if not url:
        return False

    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return False

    if domain.startswith("www."):
        domain = domain[4:]

    return domain in {
        d.replace("www.", "")
        for d in ALLOWED_VIDEO_DOMAINS
    }


##############################################################################
# Comma Cleanup
##############################################################################

def normalize_commas(text: str):

    if not isinstance(text, str):
        return text

    text = clean_text(text)

    text = re.sub(r"\s*,\s*", ", ", text)

    text = re.sub(r",\s*,+", ", ", text)

    text = re.sub(r"\s{2,}", " ", text)

    return text.strip(" ,")


##############################################################################
# List Normalization
##############################################################################

def normalize_string_list(values):

    if not isinstance(values, list):
        return values

    output = []
    seen = set()

    for item in values:

        if not isinstance(item, str):
            continue

        item = normalize_commas(item)

        if item == "":
            continue

        key = item.lower()

        if key in seen:
            continue

        seen.add(key)

        output.append(item)

    return output


##############################################################################
# Unicode Title Case
##############################################################################

def smart_title(text):

    if not isinstance(text, str):
        return text

    words = []

    for word in clean_text(text).split():

        if word.upper() == word and len(word) <= 4:
            words.append(word)
        else:
            words.append(word.capitalize())

    return " ".join(words)


##############################################################################
# Price Normalization
##############################################################################

PRICE_NUMBER_REGEX = re.compile(r"[\d,\s]+")


def extract_numeric_amount(value):
    """
    Extract numeric amount from a string.

    Examples
    --------
    ₹45,000             -> 45000
    Rs 45,000           -> 45000
    INR45000            -> 45000
    45, 000             -> 45000
    4,5,000             -> 45000
    """

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return int(value)

    if not isinstance(value, str):
        return None

    value = clean_text(value)

    value = value.lower()

    for prefix in PRICE_PREFIXES:
        value = value.replace(prefix.lower(), "")

    value = value.replace("only", "")
    value = value.replace("/-", "")
    value = value.replace("/ day", "")
    value = value.replace("/day", "")
    value = value.replace("/ person", "")
    value = value.replace("/person", "")
    value = value.replace("/ plate", "")
    value = value.replace("/plate", "")

    match = PRICE_NUMBER_REGEX.search(value)

    if not match:
        return None

    digits = re.sub(r"\D", "", match.group())

    if digits == "":
        return None

    try:
        return int(digits)
    except Exception:
        return None


##############################################################################
# Indian Number Formatting
##############################################################################

def format_indian_number(number):
    """
    45000      -> 45,000
    120000     -> 1,20,000
    1250000    -> 12,50,000
    """

    if number is None:
        return None

    try:
        number = int(number)
    except Exception:
        return None

    sign = ""

    if number < 0:
        sign = "-"
        number = abs(number)

    s = str(number)

    if len(s) <= 3:
        return sign + s

    last3 = s[-3:]
    rest = s[:-3]

    groups = []

    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]

    if rest:
        groups.insert(0, rest)

    return sign + ",".join(groups + [last3])


##############################################################################
# Currency Formatting
##############################################################################

def normalize_price(value):
    """
    Normalize price strings.

    Examples
    --------
    45000
    Rs45000
    ₹45000
    INR 45000
    45,000
    45, 000

    ↓

    ₹45,000
    """

    if value is None:
        return None

    if isinstance(value, (int, float)):
        amount = int(value)

    else:
        amount = extract_numeric_amount(value)

    if amount is None:
        return None

    if amount <= 0:
        return None

    return "₹" + format_indian_number(amount)


##############################################################################
# Price Range
##############################################################################

PRICE_RANGE_REGEX = re.compile(
    r"(.+?)\s*(?:-|to)\s*(.+)",
    flags=re.IGNORECASE,
)


def normalize_price_range(value):
    """
    Examples

    40000-60000

    Rs 20,000 to 30,000

    ₹10000 - ₹20000
    """

    if not isinstance(value, str):
        return normalize_price(value)

    value = clean_text(value)

    match = PRICE_RANGE_REGEX.match(value)

    if not match:
        return normalize_price(value)

    left = normalize_price(match.group(1))
    right = normalize_price(match.group(2))

    if left and right:
        return f"{left} - {right}"

    return left or right


##############################################################################
# Percentage
##############################################################################

def normalize_percentage(value):
    """
    Examples

    50
    50 %
    5,0%
    0050 %
    """

    if value is None:
        return None

    if isinstance(value, (int, float)):
        value = str(int(value))

    if not isinstance(value, str):
        return None

    value = clean_text(value)

    value = value.replace(" ", "")

    value = value.replace(",", "")

    value = value.replace("%", "")

    digits = re.sub(r"\D", "", value)

    if digits == "":
        return None

    try:
        pct = int(digits)
    except Exception:
        return None

    if pct < 0 or pct > 100:
        return None

    return f"{pct}%"


##############################################################################
# Money Detection
##############################################################################

MONEY_REGEX = re.compile(
    r"(₹|rs\.?|inr)?\s*[\d,\s]{3,}",
    flags=re.IGNORECASE,
)


def contains_money(value):

    if not isinstance(value, str):
        return False

    return bool(MONEY_REGEX.search(value))


##############################################################################
# Normalize Monetary Fields
##############################################################################

def normalize_monetary_value(value):
    """
    Automatically normalize either

    single price

    or

    price range.
    """

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return normalize_price(value)

    if not isinstance(value, str):
        return value

    if "-" in value.lower() or " to " in value.lower():
        return normalize_price_range(value)

    return normalize_price(value)

##############################################################################
# Generic Field Normalization
##############################################################################

def normalize_name(name: str):
    """
    Normalize vendor/person/business names.
    """

    if not isinstance(name, str):
        return name

    name = clean_text(name)

    name = normalize_commas(name)

    return smart_title(name)


def normalize_city(city: str):

    if not isinstance(city, str):
        return city

    city = clean_text(city)

    city = normalize_commas(city)

    return smart_title(city)


def normalize_locality(locality: str):

    if not isinstance(locality, str):
        return locality

    locality = clean_text(locality)

    locality = normalize_commas(locality)

    return smart_title(locality)


##############################################################################
# Coordinate Normalization
##############################################################################

def normalize_latitude(value):

    try:
        value = float(value)
    except Exception:
        return None

    if value < -90 or value > 90:
        return None

    if value == 0:
        return None

    return round(value, 7)


def normalize_longitude(value):

    try:
        value = float(value)
    except Exception:
        return None

    if value < -180 or value > 180:
        return None

    if value == 0:
        return None

    return round(value, 7)


##############################################################################
# Phone Normalization
##############################################################################

def normalize_phone(phone):

    if not isinstance(phone, str):
        return None

    phone = re.sub(r"\D", "", phone)

    if phone.startswith("91") and len(phone) == 12:
        phone = phone[2:]

    if len(phone) != 10:
        return None

    if phone[0] not in "6789":
        return None

    return phone


##############################################################################
# Email Normalization
##############################################################################

def normalize_email(email):

    if not isinstance(email, str):
        return None

    email = clean_text(email)

    email = email.lower()

    if "@" not in email:
        return None

    return email


##############################################################################
# Remove Question Prefix From Answer
##############################################################################

def remove_question_prefix(question, answer):

    if not isinstance(question, str):
        return answer

    if not isinstance(answer, str):
        return answer

    q = clean_text(question).lower()

    a = clean_text(answer)

    pattern = rf"^{re.escape(q)}\s*[:\-]?\s*"

    a = re.sub(
        pattern,
        "",
        a,
        flags=re.IGNORECASE,
    )

    return a.strip()


##############################################################################
# Normalize Documents
##############################################################################

def normalize_document_name(name):

    if not isinstance(name, str):
        return None

    name = clean_text(name)

    name = normalize_commas(name)

    return smart_title(name)


##############################################################################
# Normalize Video
##############################################################################

def normalize_video(video):

    if not isinstance(video, dict):
        return None

    url = (
        video.get("video_url")
        or video.get("url")
        or video.get("link")
    )

    if not is_allowed_video_url(url):
        return None

    return {
        "title": normalize_name(
            video.get("title", "")
        ),
        "video_url": normalize_url(url),
    }


##############################################################################
# Generic Object Normalization
##############################################################################

def normalize_object_strings(obj):

    if isinstance(obj, dict):

        cleaned = {}

        for key, value in obj.items():

            cleaned[key] = normalize_object_strings(value)

        return cleaned

    elif isinstance(obj, list):

        return [
            normalize_object_strings(i)
            for i in obj
        ]

    elif isinstance(obj, str):

        return clean_text(obj)

    return obj


##############################################################################
# Normalize Generic String Lists
##############################################################################

def normalize_csv_string(text):

    if not isinstance(text, str):
        return text

    text = normalize_commas(text)

    values = []

    seen = set()

    for item in text.split(","):

        item = item.strip()

        if item == "":
            continue

        key = item.lower()

        if key in seen:
            continue

        seen.add(key)

        values.append(item)

    return ", ".join(values)


##############################################################################
# Normalize Tags
##############################################################################

def normalize_tags(tags):

    if not isinstance(tags, list):
        return []

    output = []

    seen = set()

    for tag in tags:

        if not isinstance(tag, str):
            continue

        tag = smart_title(tag)

        key = tag.lower()

        if key in seen:
            continue

        seen.add(key)

        output.append(tag)

    return output

def normalize_state(value: str) -> str:
    if not value:
        return ""

    value = value.strip()

    # basic cleanup
    value = " ".join(value.split())

    return value.title()


##############################################################################
# Exported Helpers
##############################################################################

__all__ = [
    "normalize_question",
    "normalize_answer",
    "extract_year",
    "is_since_working_question",
    "normalize_price",
    "normalize_percentage",
    "normalize_url",
    "is_allowed_video_url",
    "normalize_commas",
    "normalize_name",
    "normalize_city",
    "normalize_locality",
    "normalize_phone",
    "normalize_email",
    "normalize_latitude",
    "normalize_longitude",
    "normalize_video",
    "normalize_document_name",
    "normalize_csv_string",
    "normalize_string_list",
    "remove_question_prefix",
    "normalize_object_strings",
    "normalize_tags",
    "smart_title",
    "normalize_state"
]