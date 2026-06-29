"""
Shared helper functions for business rules.

These helpers are intentionally generic and reusable across all rule modules.

Do NOT place business logic in this file.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from ..utils import deep_hash

###############################################################################
# Generic Nested Getters
###############################################################################

def ensure_dict(parent: dict, key: str) -> dict:
    """
    Ensure parent[key] exists and is a dict.
    """

    value = parent.get(key)

    if not isinstance(value, dict):
        value = {}
        parent[key] = value

    return value


def ensure_list(parent: dict, key: str) -> list:
    """
    Ensure parent[key] exists and is a list.
    """

    value = parent.get(key)

    if not isinstance(value, list):
        value = []
        parent[key] = value

    return value


###############################################################################
# Vendor Structure Helpers
###############################################################################

def get_profile(vendor: dict) -> dict:
    """
    Return VendorProfile.profile
    """

    vp = ensure_dict(vendor, "VendorProfile")

    return ensure_dict(vp, "profile")


def get_question_answers(vendor: dict) -> list:
    """
    Support aliases.
    """

    aliases = (
        "question_answers",
        "questions_answers",
        "faq",
        "faqs",
    )

    for key in aliases:

        value = vendor.get(key)

        if isinstance(value, list):
            return value

    vendor["question_answers"] = []

    return vendor["question_answers"]


def get_pricing(vendor: dict) -> list:

    aliases = (
        "pricing",
        "prices",
        "price_details",
        "pricing_details",
    )

    for key in aliases:

        value = vendor.get(key)

        if isinstance(value, list):
            return value

    vendor["pricing"] = []

    return vendor["pricing"]


def get_videos(vendor: dict) -> list:

    aliases = (
        "videos",
        "video_gallery",
        "video",
    )

    for key in aliases:

        value = vendor.get(key)

        if isinstance(value, list):
            return value

    vendor["videos"] = []

    return vendor["videos"]


def get_documents(vendor: dict) -> list:

    aliases = (
        "documents",
        "document_gallery",
    )

    for key in aliases:

        value = vendor.get(key)

        if isinstance(value, list):
            return value

    vendor["documents"] = []

    return vendor["documents"]


###############################################################################
# Generic Deduplication
###############################################################################

def deduplicate_dicts(items: list) -> list:
    """
    Remove duplicate dictionaries while preserving order.
    """

    seen = set()

    output = []

    for item in items:

        h = deep_hash(item)

        if h in seen:
            continue

        seen.add(h)

        output.append(item)

    return output


def deduplicate_by(items: list, key_func: Callable) -> list:

    seen = set()

    output = []

    for item in items:

        key = key_func(item)

        if key in seen:
            continue

        seen.add(key)

        output.append(item)

    return output


###############################################################################
# Empty Removal
###############################################################################

def remove_empty(items: list) -> list:

    output = []

    for item in items:

        if item is None:
            continue

        if item == "":
            continue

        if item == []:
            continue

        if item == {}:
            continue

        output.append(item)

    return output


###############################################################################
# Recursive Object Walk
###############################################################################

def walk(obj: Any, callback):

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


###############################################################################
# Recursive Dict Search
###############################################################################

def recursive_find_keys(obj, key_name):

    matches = []

    if isinstance(obj, dict):

        for key, value in obj.items():

            if key == key_name:

                matches.append(value)

            matches.extend(
                recursive_find_keys(
                    value,
                    key_name,
                )
            )

    elif isinstance(obj, list):

        for item in obj:

            matches.extend(
                recursive_find_keys(
                    item,
                    key_name,
                )
            )

    return matches


###############################################################################
# Generic Recursive Field Cleaner
###############################################################################

def clean_matching_fields(
    obj,
    field_names,
    cleaner,
):
    """
    Apply cleaner() to every matching field recursively.
    """

    if isinstance(obj, dict):

        for key, value in list(obj.items()):

            if key in field_names:

                obj[key] = cleaner(value)

            else:

                clean_matching_fields(
                    value,
                    field_names,
                    cleaner,
                )

    elif isinstance(obj, list):

        for item in obj:

            clean_matching_fields(
                item,
                field_names,
                cleaner,
            )

    return obj


###############################################################################
# Safe Remove
###############################################################################

def safe_remove_keys(data, keys):

    if not isinstance(data, dict):
        return

    for key in keys:

        data.pop(key, None)


###############################################################################
# Deep Copy Helper
###############################################################################

def clone(obj):

    return deepcopy(obj)


###############################################################################
# Rule Pipeline
###############################################################################

def apply_pipeline(vendor, rules):

    vendor = clone(vendor)

    for rule in rules:

        vendor = rule(vendor)

    return vendor


###############################################################################
# Exports
###############################################################################

__all__ = [
    "ensure_dict",
    "ensure_list",
    "get_profile",
    "get_question_answers",
    "get_pricing",
    "get_videos",
    "get_documents",
    "deduplicate_dicts",
    "deduplicate_by",
    "remove_empty",
    "walk",
    "recursive_find_keys",
    "clean_matching_fields",
    "safe_remove_keys",
    "clone",
    "apply_pipeline",
]