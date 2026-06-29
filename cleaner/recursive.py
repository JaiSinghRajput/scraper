"""
Field-aware recursive cleaner.

This module recursively traverses any JSON object while keeping
track of the current field name.

It automatically applies field-specific normalizers.

Example

price        -> normalize_price()
discount     -> normalize_percentage()
question     -> normalize_question()
answer       -> normalize_answer()
phone        -> normalize_phone()

No vendor-specific logic belongs here.
"""

from __future__ import annotations

from copy import deepcopy

from .normalizers import (
    normalize_answer,
    normalize_city,
    normalize_commas,
    normalize_document_name,
    normalize_email,
    normalize_latitude,
    normalize_locality,
    normalize_longitude,
    normalize_name,
    normalize_percentage,
    normalize_phone,
    normalize_price,
    normalize_question,
    normalize_url,
)

from .utils import (
    clean_text,
    deduplicate_list,
    is_blank,
    is_special_character_only,
)

###############################################################################
# Field Dispatch Table
###############################################################################

FIELD_NORMALIZERS = {

    # ------------------------------------------------------------------
    # Vendor
    # ------------------------------------------------------------------

    "name": normalize_name,
    "vendor_name": normalize_name,
    "business_name": normalize_name,

    "city": normalize_city,
    "locality": normalize_locality,
    "locality_name": normalize_locality,

    # ------------------------------------------------------------------
    # FAQ
    # ------------------------------------------------------------------

    "question": normalize_question,
    "answer": normalize_answer,

    # ------------------------------------------------------------------
    # Pricing
    # ------------------------------------------------------------------

    "price": normalize_price,
    "starting_price": normalize_price,
    "minimum_price": normalize_price,
    "maximum_price": normalize_price,

    "discount": normalize_percentage,
    "discount_percentage": normalize_percentage,

    # ------------------------------------------------------------------
    # Contact
    # ------------------------------------------------------------------

    "phone": normalize_phone,
    "mobile": normalize_phone,
    "contact_number": normalize_phone,

    "email": normalize_email,
    "login_email": normalize_email,

    # ------------------------------------------------------------------
    # Coordinates
    # ------------------------------------------------------------------

    "lat": normalize_latitude,
    "latitude": normalize_latitude,

    "lng": normalize_longitude,
    "long": normalize_longitude,
    "longitude": normalize_longitude,

    # ------------------------------------------------------------------
    # URLs
    # ------------------------------------------------------------------

    "url": normalize_url,
    "video_url": normalize_url,
    "youtube_url": normalize_url,

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    "document_name": normalize_document_name,
}

###############################################################################
# Recursive Entry Point
###############################################################################

def recursive_clean(data):
    """
    Public entry point.
    """

    return clean_node(
        key=None,
        value=deepcopy(data),
        parent=None,
    )


###############################################################################
# Recursive Dispatcher
###############################################################################

def clean_node(
    key,
    value,
    parent,
):
    """
    Dispatch recursively depending on value type.
    """

    if value is None:
        return None

    if isinstance(value, dict):
        return clean_dict(value)

    if isinstance(value, list):
        return clean_list(key, value)

    if isinstance(value, str):
        return clean_string(key, value)

    return clean_primitive(key, value)


###############################################################################
# Primitive Values
###############################################################################

def clean_primitive(key, value):

    normalizer = FIELD_NORMALIZERS.get(key)

    if normalizer is not None:

        try:
            return normalizer(value)

        except Exception:
            return value

    return value


###############################################################################
# String Values
###############################################################################

def clean_string(key, value):

    value = clean_text(value)

    if is_blank(value):
        return None

    if is_special_character_only(value):
        return None

    normalizer = FIELD_NORMALIZERS.get(key)

    if normalizer:

        try:

            value = normalizer(value)

        except Exception:

            pass

    if isinstance(value, str):

        value = normalize_commas(value)

    if is_blank(value):
        return None

    return value

###############################################################################
# Dictionary Cleaning
###############################################################################

def clean_dict(data: dict):
    """
    Recursively clean a dictionary.

    - cleans every child
    - removes empty values
    - removes empty dict/list
    """

    cleaned = {}

    for key, value in data.items():

        value = clean_node(
            key=key,
            value=value,
            parent=data,
        )

        if should_remove(key, value):
            continue

        cleaned[key] = value

    return cleaned


###############################################################################
# List Cleaning
###############################################################################

def clean_list(parent_key, values):
    """
    Recursively clean a list.

    - clean every item
    - flatten nested lists
    - remove duplicates
    - remove blanks
    """

    cleaned = []

    for value in values:

        value = clean_node(
            key=parent_key,
            value=value,
            parent=values,
        )

        if should_remove(parent_key, value):
            continue

        # flatten nested lists
        if isinstance(value, list):
            cleaned.extend(value)
        else:
            cleaned.append(value)

    cleaned = deduplicate_list(cleaned)

    cleaned = [
        item
        for item in cleaned
        if not should_remove(parent_key, item)
    ]

    return cleaned


###############################################################################
# Remove Rules
###############################################################################

def should_remove(key, value):
    """
    Decide whether a value should be removed.

    Keep this function generic.
    """

    if value is None:
        return True

    if isinstance(value, str):

        if value.strip() == "":
            return True

        if is_blank(value):
            return True

        if is_special_character_only(value):
            return True

    elif isinstance(value, list):

        if len(value) == 0:
            return True

    elif isinstance(value, dict):

        if len(value) == 0:
            return True

    return False


###############################################################################
# Deep Cleanup Pass
###############################################################################

def deep_cleanup(obj):
    """
    Second recursive cleanup pass.

    Removes empty values left after normalization.
    """

    if obj is None:
        return None

    if isinstance(obj, dict):

        result = {}

        for key, value in obj.items():

            value = deep_cleanup(value)

            if should_remove(key, value):
                continue

            result[key] = value

        return result

    elif isinstance(obj, list):

        result = []

        for item in obj:

            item = deep_cleanup(item)

            if should_remove(None, item):
                continue

            result.append(item)

        return deduplicate_list(result)

    elif isinstance(obj, str):

        obj = clean_text(obj)

        if is_blank(obj):
            return None

        if is_special_character_only(obj):
            return None

        return obj

    return obj


###############################################################################
# Dictionary Deduplication
###############################################################################

def deduplicate_dict_list(items):
    """
    Remove duplicate dictionaries while preserving order.
    """

    if not isinstance(items, list):
        return items

    return deduplicate_list(items)


###############################################################################
# Collapse Empty Objects
###############################################################################

def collapse_empty(obj):
    """
    Collapse recursively.

    {} -> None
    [] -> None
    """

    obj = deep_cleanup(obj)

    if isinstance(obj, dict):

        if len(obj) == 0:
            return None

    elif isinstance(obj, list):

        if len(obj) == 0:
            return None

    return obj


###############################################################################
# Final Recursive Pass
###############################################################################

def finalize(obj):
    """
    Final pass executed before saving JSON.

    Pipeline:

        recursive_clean()

        ↓

        deep_cleanup()

        ↓

        collapse_empty()

    """

    obj = recursive_clean(obj)

    obj = deep_cleanup(obj)

    obj = collapse_empty(obj)

    return obj


###############################################################################
# Statistics
###############################################################################

STATS = {
    "dicts": 0,
    "lists": 0,
    "strings": 0,
    "removed": 0,
    "normalized": 0,
}


def reset_stats():
    global STATS

    STATS = {
        "dicts": 0,
        "lists": 0,
        "strings": 0,
        "removed": 0,
        "normalized": 0,
    }


def get_stats():
    return dict(STATS)


###############################################################################
# Hook Registration
###############################################################################

PRE_HOOKS = []

POST_HOOKS = []


def register_pre_hook(func):
    """
    Called before a node is cleaned.

    Signature:

        func(key, value)

    """

    PRE_HOOKS.append(func)


def register_post_hook(func):
    """
    Called after a node is cleaned.

    Signature:

        func(key, value)

    """

    POST_HOOKS.append(func)


###############################################################################
# Execute Hooks
###############################################################################

def run_pre_hooks(key, value):

    for hook in PRE_HOOKS:

        try:
            value = hook(key, value)
        except Exception:
            pass

    return value


def run_post_hooks(key, value):

    for hook in POST_HOOKS:

        try:
            value = hook(key, value)
        except Exception:
            pass

    return value


###############################################################################
# Custom Field Handler Registration
###############################################################################

CUSTOM_FIELD_HANDLERS = {}


def register_field(field_name, cleaner):
    """
    Register additional field normalizer.

    Example

    register_field(
        "gst",
        normalize_percentage
    )
    """

    CUSTOM_FIELD_HANDLERS[field_name] = cleaner


###############################################################################
# Override Dispatcher
###############################################################################

def clean_value(key, value):
    """
    Clean a primitive value.

    Uses:

    CUSTOM_FIELD_HANDLERS

    then

    FIELD_NORMALIZERS
    """

    value = run_pre_hooks(key, value)

    cleaner = CUSTOM_FIELD_HANDLERS.get(key)

    if cleaner is None:
        cleaner = FIELD_NORMALIZERS.get(key)

    if cleaner:

        try:

            value = cleaner(value)

            STATS["normalized"] += 1

        except Exception:

            pass

    value = run_post_hooks(key, value)

    return value


###############################################################################
# Patch Existing Clean Functions
###############################################################################

#
# Replace the body inside clean_string()
#
# after clean_text(...)
#
# with
#
# value = clean_value(key, value)
#
# instead of directly using FIELD_NORMALIZERS.
#
# Likewise replace clean_primitive().
#
# This keeps the file extensible.
#


###############################################################################
# Convenience Wrapper
###############################################################################

def clean_json(data):
    """
    Public API.

    Example

    cleaned = clean_json(data)
    """

    reset_stats()

    result = finalize(data)

    return result


###############################################################################
# Exports
###############################################################################

__all__ = [
    "clean_json",
    "recursive_clean",
    "finalize",
    "clean_node",
    "clean_dict",
    "clean_list",
    "register_field",
    "register_pre_hook",
    "register_post_hook",
    "get_stats",
    "reset_stats",
]