"""
Vendor Data Validators

This module ensures cleaned data is actually valid.

It does NOT modify structure heavily — it only:
- removes invalid values
- flags broken data
- enforces schema sanity
"""

from __future__ import annotations

import re
from typing import Any

from .rules.common import (
    get_profile,
    get_pricing,
    get_videos,
    get_documents,
    get_question_answers,
)

###############################################################################
# Regex
###############################################################################

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

PHONE_RE = re.compile(r"^[6-9]\d{9}$")

URL_RE = re.compile(r"^https?://", re.I)

YEAR_MIN = 1950
YEAR_MAX = 2100

###############################################################################
# Safe Helpers
###############################################################################

def _is_blank(value):

    if value is None:
        return True

    if isinstance(value, str) and not value.strip():
        return True

    if value == {} or value == []:
        return True

    return False


def _to_int(value):

    try:
        return int(value)
    except Exception:
        return None

###############################################################################
# Profile Validation
###############################################################################

def validate_profile(vendor):

    profile = get_profile(vendor)

    # Remove invalid emails
    for key in list(profile.keys()):

        if "email" in key:

            value = profile.get(key)

            if not isinstance(value, str) or not EMAIL_RE.match(value):
                profile.pop(key, None)

    # Remove invalid phones
    for key in list(profile.keys()):

        if "phone" in key or "mobile" in key:

            value = str(profile.get(key, ""))

            if not PHONE_RE.match(value):
                profile.pop(key, None)

    # Validate since_working_year
    year = profile.get("since_working_year")

    if year is not None:

        year = _to_int(year)

        if year is None or year < YEAR_MIN or year > YEAR_MAX:

            profile.pop("since_working_year", None)

        else:

            profile["since_working_year"] = year

    return vendor


###############################################################################
# Pricing Validation
###############################################################################

def validate_pricing(vendor):

    pricing = get_pricing(vendor)

    cleaned = []

    for item in pricing:

        if not isinstance(item, dict):
            continue

        answer = item.get("answer")

        if _is_blank(answer):
            continue

        cleaned.append(item)

    pricing.clear()
    pricing.extend(cleaned)

    return vendor


###############################################################################
# FAQ Validation
###############################################################################

def validate_faq(vendor):

    faq = get_question_answers(vendor)

    cleaned = []

    for item in faq:

        if not isinstance(item, dict):
            continue

        q = item.get("question")
        a = item.get("answer")

        if _is_blank(q) or _is_blank(a):
            continue

        if q.strip().lower() == a.strip().lower():
            continue

        cleaned.append(item)

    faq.clear()
    faq.extend(cleaned)

    return vendor


###############################################################################
# Media Validation
###############################################################################

def validate_media(vendor):

    videos = get_videos(vendor)

    videos[:] = [
        v for v in videos
        if isinstance(v, dict) and v.get("video_url")
    ]

    documents = get_documents(vendor)

    documents[:] = [
        d for d in documents
        if isinstance(d, dict) and d.get("document_url")
    ]

    return vendor


###############################################################################
# Global Validator
###############################################################################

def validate_vendor(vendor):

    vendor = validate_profile(vendor)

    vendor = validate_pricing(vendor)

    vendor = validate_faq(vendor)

    vendor = validate_media(vendor)

    return vendor


###############################################################################
# Export
###############################################################################

__all__ = [
    "validate_vendor",
    "validate_profile",
    "validate_pricing",
    "validate_faq",
    "validate_media",
]