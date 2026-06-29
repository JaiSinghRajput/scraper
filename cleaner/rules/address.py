"""
Address Business Rules

Responsible for

- Address normalization
- City/State normalization
- Locality cleanup
- Pincode validation
- Latitude/Longitude validation

This module ONLY handles address data.
"""

from __future__ import annotations

import re

from ..normalizers import (
    normalize_city,
    normalize_locality,
    normalize_state,
)

from .common import (
    deduplicate_by,
    get_profile,
)

###############################################################################
# Constants
###############################################################################

ADDRESS_FIELDS = (
    "address",
    "full_address",
    "street_address",
)

CITY_FIELDS = (
    "city",
)

STATE_FIELDS = (
    "state",
)

LOCALITY_FIELDS = (
    "locality",
    "area",
    "region",
)

PINCODE_FIELDS = (
    "pincode",
    "postal_code",
    "zip",
    "zipcode",
)

LATITUDE_FIELDS = (
    "latitude",
    "lat",
)

LONGITUDE_FIELDS = (
    "longitude",
    "lng",
    "lon",
)

PIN_RE = re.compile(r"^\d{6}$")

###############################################################################
# Helpers
###############################################################################

def _clean_spaces(text):

    if not isinstance(text, str):
        return text

    text = re.sub(r"\s+", " ", text)

    text = text.replace(" ,", ",")

    text = text.replace(",,", ",")

    return text.strip(" ,")


def _normalize_address(value):

    if not isinstance(value, str):
        return ""

    value = _clean_spaces(value)

    return value


def _normalize_pincode(value):

    if value is None:
        return None

    value = str(value)

    value = re.sub(r"\D", "", value)

    if not PIN_RE.fullmatch(value):
        return None

    return value


def _normalize_latitude(value):

    try:

        value = float(value)

    except Exception:

        return None

    if value < -90:
        return None

    if value > 90:
        return None

    return round(value, 6)


def _normalize_longitude(value):

    try:

        value = float(value)

    except Exception:

        return None

    if value < -180:
        return None

    if value > 180:
        return None

    return round(value, 6)


###############################################################################
# Normalize Address Fields
###############################################################################

def normalize_address_fields(vendor):

    profile = get_profile(vendor)

    for field in ADDRESS_FIELDS:

        if field not in profile:
            continue

        profile[field] = _normalize_address(
            profile[field]
        )

    for field in CITY_FIELDS:

        if field in profile:

            profile[field] = normalize_city(
                profile[field]
            )

    for field in STATE_FIELDS:

        if field in profile:

            profile[field] = normalize_state(
                profile[field]
            )

    for field in LOCALITY_FIELDS:

        if field in profile:

            profile[field] = normalize_locality(
                profile[field]
            )

    return vendor


###############################################################################
# Normalize Coordinates
###############################################################################

def normalize_coordinates(vendor):

    profile = get_profile(vendor)

    for field in LATITUDE_FIELDS:

        if field in profile:

            value = _normalize_latitude(
                profile[field]
            )

            if value is None:

                profile.pop(field, None)

            else:

                profile[field] = value

    for field in LONGITUDE_FIELDS:

        if field in profile:

            value = _normalize_longitude(
                profile[field]
            )

            if value is None:

                profile.pop(field, None)

            else:

                profile[field] = value

    return vendor


###############################################################################
# Normalize Pincode
###############################################################################

def normalize_pincode(vendor):

    profile = get_profile(vendor)

    for field in PINCODE_FIELDS:

        if field not in profile:
            continue

        value = _normalize_pincode(
            profile[field]
        )

        if value is None:

            profile.pop(field, None)

        else:

            profile[field] = value

    return vendor
###############################################################################
# Recursive Address Cleanup
###############################################################################

def clean_recursive_addresses(obj):

    """
    Recursively clean address-like fields anywhere in vendor object.
    """

    if isinstance(obj, dict):

        for key, value in list(obj.items()):

            if key in ADDRESS_FIELDS and isinstance(value, str):

                obj[key] = _normalize_address(value)

            elif key in CITY_FIELDS:

                obj[key] = normalize_city(value)

            elif key in STATE_FIELDS:

                obj[key] = normalize_state(value)

            elif key in LOCALITY_FIELDS:

                obj[key] = normalize_locality(value)

            else:

                clean_recursive_addresses(value)

    elif isinstance(obj, list):

        for item in obj:

            clean_recursive_addresses(item)


###############################################################################
# Remove Empty Address Fields
###############################################################################

def remove_empty_address_fields(vendor):

    profile = get_profile(vendor)

    remove_keys = []

    for key, value in profile.items():

        if value is None:
            remove_keys.append(key)
            continue

        if isinstance(value, str) and not value.strip():
            remove_keys.append(key)
            continue

        if value == [] or value == {}:
            remove_keys.append(key)
            continue

    for key in remove_keys:

        profile.pop(key, None)

    return vendor


###############################################################################
# Deduplicate Address-Like Strings
###############################################################################

def deduplicate_addresses(vendor):

    profile = get_profile(vendor)

    seen = set()

    for key in ADDRESS_FIELDS:

        value = profile.get(key)

        if not isinstance(value, str):
            continue

        norm = value.lower().strip()

        if norm in seen:
            profile.pop(key, None)
            continue

        seen.add(norm)

    return vendor


###############################################################################
# Normalize Full Address Block
###############################################################################

def normalize_full_address_block(vendor):

    profile = get_profile(vendor)

    for field in ADDRESS_FIELDS:

        value = profile.get(field)

        if not isinstance(value, str):
            continue

        value = _clean_spaces(value)

        value = value.replace(" ,", ", ")

        value = value.replace(",,", ",")

        profile[field] = value.strip()

    return vendor


###############################################################################
# Address Cleaning Pipeline
###############################################################################

def clean_addresses(vendor):

    vendor = normalize_address_fields(vendor)

    vendor = normalize_coordinates(vendor)

    vendor = normalize_pincode(vendor)

    clean_recursive_addresses(vendor)

    vendor = normalize_full_address_block(vendor)

    vendor = deduplicate_addresses(vendor)

    vendor = remove_empty_address_fields(vendor)

    return vendor


###############################################################################
# Exports
###############################################################################

__all__ = [
    "normalize_address_fields",
    "normalize_coordinates",
    "normalize_pincode",
    "clean_recursive_addresses",
    "normalize_full_address_block",
    "deduplicate_addresses",
    "remove_empty_address_fields",
    "clean_addresses",
]