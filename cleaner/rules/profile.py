"""
Profile Business Rules

Responsible for:

- Vendor profile normalization
- About/description cleanup
- Name normalization
- Social link cleanup
- Contact cleanup
- Basic profile normalization
"""

from __future__ import annotations

import re

from ..normalizers import (
    normalize_name,
    normalize_city,
    normalize_locality,
    normalize_phone,
    normalize_email,
)

from .common import (
    get_profile,
)

###############################################################################
# Profile Keys
###############################################################################

NAME_FIELDS = (
    "name",
    "vendor_name",
    "business_name",
    "owner_name",
    "contact_person",
)

DESCRIPTION_FIELDS = (
    "about",
    "description",
    "vendor_description",
    "business_description",
    "summary",
    "details",
)

EMAIL_FIELDS = (
    "email",
    "contact_email",
    "business_email",
)

PHONE_FIELDS = (
    "phone",
    "mobile",
    "contact_number",
    "whatsapp_number",
)

CITY_FIELDS = (
    "city",
)

LOCALITY_FIELDS = (
    "locality",
    "area",
)

###############################################################################
# Regular Expressions
###############################################################################

URL_RE = re.compile(
    r"https?://\S+|www\.\S+",
    flags=re.IGNORECASE,
)

EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    flags=re.IGNORECASE,
)

PHONE_RE = re.compile(
    r"(\+91[\-\s]?)?[6-9]\d{9}"
)

###############################################################################
# Text Helpers
###############################################################################

def _clean_spaces(text):

    if not isinstance(text, str):
        return ""

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def remove_urls(text):

    if not isinstance(text, str):
        return text

    text = URL_RE.sub("", text)

    return _clean_spaces(text)


def remove_emails(text):

    if not isinstance(text, str):
        return text

    text = EMAIL_RE.sub("", text)

    return _clean_spaces(text)


def remove_phones(text):

    if not isinstance(text, str):
        return text

    text = PHONE_RE.sub("", text)

    return _clean_spaces(text)


###############################################################################
# Name Normalization
###############################################################################

def normalize_names(vendor):

    profile = get_profile(vendor)

    for field in NAME_FIELDS:

        if field not in profile:
            continue

        profile[field] = normalize_name(
            profile[field]
        )

    return vendor


###############################################################################
# Contact Normalization
###############################################################################

def normalize_contacts(vendor):

    profile = get_profile(vendor)

    for field in EMAIL_FIELDS:

        if field not in profile:
            continue

        profile[field] = normalize_email(
            profile[field]
        )

    for field in PHONE_FIELDS:

        if field not in profile:
            continue

        profile[field] = normalize_phone(
            profile[field]
        )

    return vendor


###############################################################################
# Location Normalization
###############################################################################

def normalize_location(vendor):

    profile = get_profile(vendor)

    for field in CITY_FIELDS:

        if field in profile:

            profile[field] = normalize_city(
                profile[field]
            )

    for field in LOCALITY_FIELDS:

        if field in profile:

            profile[field] = normalize_locality(
                profile[field]
            )

    return vendor


###############################################################################
# Description Cleanup
###############################################################################

def clean_descriptions(vendor):

    profile = get_profile(vendor)

    for field in DESCRIPTION_FIELDS:

        value = profile.get(field)

        if not isinstance(value, str):
            continue

        value = remove_urls(value)

        value = remove_emails(value)

        value = remove_phones(value)

        value = _clean_spaces(value)

        profile[field] = value

    return vendor


###############################################################################
# Remove Blank Values
###############################################################################

def remove_blank_profile_fields(vendor):

    profile = get_profile(vendor)

    remove = []

    for key, value in profile.items():

        if value is None:
            remove.append(key)
            continue

        if value == "":
            remove.append(key)
            continue

        if value == []:
            remove.append(key)
            continue

        if value == {}:
            remove.append(key)
            continue

    for key in remove:

        profile.pop(key, None)

    return vendor 

###############################################################################
# List Normalization
###############################################################################

LIST_FIELDS = (
    "languages",
    "services",
    "specializations",
    "features",
    "facilities",
    "amenities",
    "payment_modes",
    "payment_methods",
    "categories",
    "tags",
    "styles",
    "occasions",
)


def _normalize_list(value):

    if value is None:
        return []

    if isinstance(value, str):

        value = value.replace("|", ",")

        value = value.replace("/", ",")

        value = value.split(",")

    if not isinstance(value, list):
        return []

    cleaned = []

    seen = set()

    for item in value:

        if item is None:
            continue

        item = str(item).strip()

        if not item:
            continue

        item = " ".join(item.split())

        item = item.title()

        key = item.lower()

        if key in seen:
            continue

        seen.add(key)

        cleaned.append(item)

    return sorted(cleaned)


###############################################################################
# Normalize Lists
###############################################################################

def normalize_lists(vendor):

    profile = get_profile(vendor)

    for field in LIST_FIELDS:

        if field not in profile:
            continue

        profile[field] = _normalize_list(
            profile[field]
        )

    return vendor


###############################################################################
# Social Links
###############################################################################

SOCIAL_FIELDS = (
    "website",
    "facebook",
    "instagram",
    "youtube",
    "twitter",
    "linkedin",
    "pinterest",
)


def normalize_social_links(vendor):

    profile = get_profile(vendor)

    for field in SOCIAL_FIELDS:

        if field not in profile:
            continue

        value = profile[field]

        if not isinstance(value, str):

            profile.pop(field, None)

            continue

        value = value.strip()

        if not value:

            profile.pop(field, None)

            continue

        #
        # Keep only youtube
        #

        if field == "youtube":

            if "youtube.com" not in value.lower() and \
               "youtu.be" not in value.lower():

                profile.pop(field, None)

                continue

            profile[field] = value

            continue

        #
        # Remove every other social link
        #

        profile.pop(field, None)

    return vendor


###############################################################################
# Working Year
###############################################################################

def normalize_since_working_year(vendor):

    profile = get_profile(vendor)

    year = profile.get("since_working_year")

    if year is None:
        return vendor

    try:

        year = int(year)

    except Exception:

        profile.pop("since_working_year", None)

        return vendor

    if year < 1950:

        profile.pop("since_working_year", None)

        return vendor

    if year > 2100:

        profile.pop("since_working_year", None)

        return vendor

    profile["since_working_year"] = year

    return vendor


###############################################################################
# Remove Special Character Only Values
###############################################################################

SPECIAL_RE = re.compile(r"^[^A-Za-z0-9]+$")


def remove_special_values(vendor):

    profile = get_profile(vendor)

    remove = []

    for key, value in profile.items():

        if not isinstance(value, str):
            continue

        if SPECIAL_RE.fullmatch(value):

            remove.append(key)

    for key in remove:

        profile.pop(key, None)

    return vendor


###############################################################################
# Normalize Recursive Text
###############################################################################

TEXT_FIELDS = (
    "about",
    "description",
    "details",
    "summary",
)


def clean_recursive(obj):

    if isinstance(obj, dict):

        for key, value in list(obj.items()):

            if key in TEXT_FIELDS and isinstance(value, str):

                value = remove_urls(value)

                value = remove_emails(value)

                value = remove_phones(value)

                value = _clean_spaces(value)

                obj[key] = value

            else:

                clean_recursive(value)

    elif isinstance(obj, list):

        for item in obj:

            clean_recursive(item)


def recursive_profile_cleanup(vendor):

    profile = get_profile(vendor)

    clean_recursive(profile)

    return vendor