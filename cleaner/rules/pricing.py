"""
Pricing Business Rules

Responsible for:

- Price normalization
- Price validation
- Price range normalization
- Pricing object cleanup

No vendor-specific logic outside pricing belongs here.
"""

from __future__ import annotations

from collections import defaultdict

from ..normalizers import (
    normalize_monetary_value,
    normalize_question,
)

from .common import (
    deduplicate_by,
    get_pricing,
)

###############################################################################
# Supported Pricing Keys
###############################################################################

PRICE_VALUE_KEYS = (
    "answer",
    "price",
    "value",
    "amount",
)

QUESTION_KEYS = (
    "question",
    "label",
    "title",
)

###############################################################################
# Helpers
###############################################################################

def _get_price(item):
    """
    Extract price from supported keys.
    """

    for key in PRICE_VALUE_KEYS:

        value = item.get(key)

        if value not in (None, ""):
            return value

    return None


def _get_question(item):
    """
    Extract pricing question.
    """

    for key in QUESTION_KEYS:

        value = item.get(key)

        if isinstance(value, str) and value.strip():
            return value

    return ""


def _normalize_item(item):
    """
    Normalize one pricing item.

    Returns None if invalid.
    """

    if not isinstance(item, dict):
        return None

    question = normalize_question(
        _get_question(item)
    )

    price = normalize_monetary_value(
        _get_price(item)
    )

    if price is None:
        return None

    new_item = dict(item)

    new_item["question"] = question
    new_item["answer"] = price

    #
    # Remove duplicate aliases
    #

    for key in PRICE_VALUE_KEYS:

        if key != "answer":
            new_item.pop(key, None)

    for key in QUESTION_KEYS:

        if key != "question":
            new_item.pop(key, None)

    return new_item


###############################################################################
# Normalize Pricing
###############################################################################

def normalize_pricing(vendor):
    """
    Normalize every pricing object.
    """

    pricing = get_pricing(vendor)

    cleaned = []

    for item in pricing:

        item = _normalize_item(item)

        if item is None:
            continue

        cleaned.append(item)

    pricing.clear()
    pricing.extend(cleaned)

    return vendor


###############################################################################
# Remove Blank Pricing
###############################################################################

def remove_blank_pricing(vendor):
    """
    Remove pricing entries without
    question or answer.
    """

    pricing = get_pricing(vendor)

    cleaned = []

    for item in pricing:

        question = item.get(
            "question",
            "",
        ).strip()

        answer = item.get(
            "answer",
            "",
        ).strip()

        if not answer:
            continue

        if question == answer:
            continue

        cleaned.append(item)

    pricing.clear()
    pricing.extend(cleaned)

    return vendor


###############################################################################
# Normalize Question Labels
###############################################################################

QUESTION_REMAP = {

    "starting price": "Starting Price",

    "price": "Starting Price",

    "starting from": "Starting Price",

    "per plate": "Per Plate",

    "vegetarian": "Vegetarian",

    "non vegetarian": "Non Vegetarian",

    "bridal package": "Bridal Package",

    "party makeup": "Party Makeup",

}


def normalize_price_questions(vendor):

    pricing = get_pricing(vendor)

    for item in pricing:

        q = item.get(
            "question",
            "",
        ).lower()

        if q in QUESTION_REMAP:

            item["question"] = QUESTION_REMAP[q]

    return vendor

###############################################################################
# Merge Pricing Having Same Question
###############################################################################

def merge_same_question_pricing(vendor):
    """
    Merge duplicate pricing questions.

    Example

    Starting Price -> ₹45,000
    Starting Price -> ₹45,000

    becomes

    Starting Price -> ₹45,000
    """

    pricing = get_pricing(vendor)

    grouped = defaultdict(list)

    for item in pricing:

        question = item.get("question", "")

        grouped[question].append(item)

    merged = []

    for question, items in grouped.items():

        seen = set()

        prices = []

        template = dict(items[0])

        for item in items:

            price = item.get("answer", "").strip()

            if not price:
                continue

            if price in seen:
                continue

            seen.add(price)

            prices.append(price)

        if not prices:
            continue

        if len(prices) == 1:

            template["answer"] = prices[0]

        else:

            template["answer"] = " / ".join(prices)

            template["answer_list"] = prices

        merged.append(template)

    pricing.clear()
    pricing.extend(merged)

    return vendor


###############################################################################
# Remove Duplicate Pricing
###############################################################################

def deduplicate_pricing(vendor):
    """
    Remove exact duplicate pricing objects.
    """

    pricing = get_pricing(vendor)

    pricing[:] = deduplicate_by(
        pricing,
        lambda x: (
            x.get("question", "").lower().strip(),
            x.get("answer", "").lower().strip(),
        ),
    )

    return vendor


###############################################################################
# Remove Invalid Pricing
###############################################################################

INVALID_VALUES = {
    "",
    "-",
    "--",
    "n/a",
    "na",
    "null",
    "none",
    "nil",
    "not available",
}


def remove_invalid_pricing(vendor):

    pricing = get_pricing(vendor)

    cleaned = []

    for item in pricing:

        answer = item.get("answer", "")

        if answer is None:
            continue

        value = str(answer).lower().strip()

        if value in INVALID_VALUES:
            continue

        cleaned.append(item)

    pricing.clear()
    pricing.extend(cleaned)

    return vendor


###############################################################################
# Remove Duplicate Prices Inside answer_list
###############################################################################

def deduplicate_price_lists(vendor):

    pricing = get_pricing(vendor)

    for item in pricing:

        values = item.get("answer_list")

        if not isinstance(values, list):
            continue

        unique = []

        seen = set()

        for value in values:

            if value in seen:
                continue

            seen.add(value)

            unique.append(value)

        item["answer_list"] = unique

    return vendor


###############################################################################
# Sort Pricing
###############################################################################

def sort_pricing(vendor):
    """
    Stable ordering.
    """

    pricing = get_pricing(vendor)

    pricing.sort(
        key=lambda x: (
            x.get("question", "").lower(),
            x.get("answer", "").lower(),
        )
    )

    return vendor


###############################################################################
# Remove Empty Pricing Objects
###############################################################################

def remove_empty_pricing(vendor):

    pricing = get_pricing(vendor)

    pricing[:] = [

        item

        for item in pricing

        if item.get("answer")

    ]

    return vendor


###############################################################################
# Final Pricing Pipeline
###############################################################################

def clean_pricing(vendor):
    """
    Complete pricing cleaning pipeline.
    """

    vendor = normalize_pricing(vendor)

    vendor = remove_blank_pricing(vendor)

    vendor = normalize_price_questions(vendor)

    vendor = merge_same_question_pricing(vendor)

    vendor = deduplicate_price_lists(vendor)

    vendor = deduplicate_pricing(vendor)

    vendor = remove_invalid_pricing(vendor)

    vendor = remove_empty_pricing(vendor)

    vendor = sort_pricing(vendor)

    return vendor


###############################################################################
# Exports
###############################################################################

__all__ = [
    "normalize_pricing",
    "remove_blank_pricing",
    "normalize_price_questions",
    "merge_same_question_pricing",
    "deduplicate_pricing",
    "deduplicate_price_lists",
    "remove_invalid_pricing",
    "remove_empty_pricing",
    "sort_pricing",
    "clean_pricing",
]