"""
Generic reusable utility functions.

This module should contain only generic helpers.
No vendor-specific logic belongs here.
"""

from __future__ import annotations

import copy
import hashlib
import html
import re
import unicodedata
from typing import Any, Iterable

from .config import (
    CONTROL_CHAR_REGEX,
    EMAIL_REGEX,
    HTML_REGEX,
    JUNK_VALUES,
    MULTIPLE_SPACE_REGEX,
    PHONE_REGEX,
    SPECIAL_ONLY_REGEX,
    URL_REGEX,
)


##############################################################################
# String Normalization
##############################################################################

def normalize_unicode(text: str) -> str:
    """Normalize unicode characters into ASCII when possible."""
    if not isinstance(text, str):
        return text

    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode("ascii")


def html_unescape(text: str) -> str:
    if not isinstance(text, str):
        return text
    return html.unescape(text)


def strip_html(text: str) -> str:
    if not isinstance(text, str):
        return text

    return re.sub(HTML_REGEX, " ", text)


def remove_control_characters(text: str) -> str:
    if not isinstance(text, str):
        return text

    return re.sub(CONTROL_CHAR_REGEX, "", text)


def normalize_whitespace(text: str) -> str:
    if not isinstance(text, str):
        return text

    text = re.sub(MULTIPLE_SPACE_REGEX, " ", text)

    return text.strip()


def clean_text(text: str) -> str:
    """
    Generic string cleaning.
    """

    if not isinstance(text, str):
        return text

    text = html_unescape(text)
    text = normalize_unicode(text)
    text = strip_html(text)
    text = remove_control_characters(text)
    text = normalize_whitespace(text)

    return text.strip()


##############################################################################
# Detection
##############################################################################

def extract_urls(text: str) -> list[str]:
    if not isinstance(text, str):
        return []

    return re.findall(URL_REGEX, text, flags=re.IGNORECASE)


def extract_emails(text: str) -> list[str]:
    if not isinstance(text, str):
        return []

    return re.findall(EMAIL_REGEX, text)


def extract_phone_numbers(text: str) -> list[str]:
    if not isinstance(text, str):
        return []

    return re.findall(PHONE_REGEX, text)


##############################################################################
# Validation
##############################################################################

def is_blank(value: Any) -> bool:

    if value is None:
        return True

    if isinstance(value, str):

        text = clean_text(value).lower()

        return text in JUNK_VALUES

    return False


def is_special_character_only(value: Any) -> bool:

    if not isinstance(value, str):
        return False

    value = value.strip()

    if value == "":
        return False

    return bool(re.fullmatch(SPECIAL_ONLY_REGEX, value))


##############################################################################
# Safe Conversions
##############################################################################

def safe_int(value, default=None):

    try:

        return int(value)

    except Exception:

        return default


def safe_float(value, default=None):

    try:

        return float(value)

    except Exception:

        return default


##############################################################################
# Dictionary Helpers
##############################################################################

def remove_none_values(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not None}


def remove_empty_strings(data: dict) -> dict:

    cleaned = {}

    for k, v in data.items():

        if isinstance(v, str):

            if is_blank(v):
                continue

        cleaned[k] = v

    return cleaned


##############################################################################
# Hashing
##############################################################################

def deep_hash(obj: Any) -> str:
    """
    Stable hash for nested dict/list.
    Used for duplicate removal.
    """

    return hashlib.md5(
        repr(make_hashable(obj)).encode("utf8")
    ).hexdigest()


def make_hashable(obj):

    if isinstance(obj, dict):

        return tuple(
            sorted(
                (k, make_hashable(v))
                for k, v in obj.items()
            )
        )

    if isinstance(obj, list):

        return tuple(make_hashable(i) for i in obj)

    return obj


##############################################################################
# List Helpers
##############################################################################

def deduplicate_list(items: list[Any]) -> list[Any]:

    seen = set()

    result = []

    for item in items:

        h = deep_hash(item)

        if h in seen:
            continue

        seen.add(h)

        result.append(item)

    return result


def flatten_list(items):

    result = []

    for item in items:

        if isinstance(item, list):

            result.extend(flatten_list(item))

        else:

            result.append(item)

    return result


##############################################################################
# Dictionary Merge
##############################################################################

def merge_dicts(a: dict, b: dict) -> dict:
    """
    Recursively merge dictionaries.
    """

    result = copy.deepcopy(a)

    for key, value in b.items():

        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):

            result[key] = merge_dicts(result[key], value)

        else:

            result[key] = value

    return result


##############################################################################
# Coordinate Validation
##############################################################################

def valid_latitude(value) -> bool:

    try:

        value = float(value)

    except Exception:

        return False

    return -90 <= value <= 90


def valid_longitude(value) -> bool:

    try:

        value = float(value)

    except Exception:

        return False

    return -180 <= value <= 180


##############################################################################
# Generic Recursive Walk
##############################################################################

def walk(obj, callback):
    """
    Walk recursively over nested structures.

    callback(value) -> new_value
    """

    if isinstance(obj, dict):

        return {
            k: walk(v, callback)
            for k, v in obj.items()
        }

    if isinstance(obj, list):

        return [
            walk(i, callback)
            for i in obj
        ]

    return callback(obj)