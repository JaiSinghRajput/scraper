"""
FAQ Business Rules

Responsible for

- Extracting since_working_year
- FAQ normalization
- FAQ deduplication
- FAQ validation

This module ONLY handles FAQ data.
"""

from __future__ import annotations

from collections import defaultdict

from ..normalizers import (
    extract_year,
    is_since_working_question,
    normalize_answer,
    normalize_question,
    remove_question_prefix,
)

from .common import (
    deduplicate_by,
    get_profile,
    get_question_answers,
)

###############################################################################
# Internal Helpers
###############################################################################

FAQ_ALIASES = (
    "question_answers",
    "questions_answers",
    "faq",
    "faqs",
)


def _clean_item(item):
    """
    Normalize one FAQ item.
    """

    if not isinstance(item, dict):
        return None

    question = normalize_question(
        item.get("question", "")
    )

    answer = normalize_answer(
        item.get("answer", "")
    )

    answer = remove_question_prefix(
        question,
        answer,
    )

    if not question:
        return None

    if not answer:
        return None

    return {
        "question": question,
        "answer": answer,
    }


###############################################################################
# Since Working Extraction
###############################################################################

def extract_since_working_year(vendor):
    """
    Extract

        Working Since
        Experience
        Started In
        Established In

    into

        VendorProfile.profile.since_working_year

    Removes the FAQ afterwards.
    """

    faq = get_question_answers(vendor)

    profile = get_profile(vendor)

    remaining = []

    years = []

    for item in faq:

        cleaned = _clean_item(item)

        if cleaned is None:
            continue

        question = cleaned["question"]

        answer = cleaned["answer"]

        if not is_since_working_question(question):

            remaining.append(cleaned)

            continue

        year = extract_year(answer)

        if year is None:
            year = extract_year(question)

        if year:

            years.append(year)

    if years:

        profile["since_working_year"] = min(years)

    vendor["question_answers"] = remaining

    return vendor


###############################################################################
# Normalize FAQ
###############################################################################

def normalize_faq(vendor):
    """
    Normalize every FAQ.
    """

    faq = get_question_answers(vendor)

    cleaned = []

    for item in faq:

        item = _clean_item(item)

        if item is None:
            continue

        cleaned.append(item)

    vendor["question_answers"] = cleaned

    return vendor


###############################################################################
# Remove Blank FAQ
###############################################################################

def remove_blank_faq(vendor):

    faq = get_question_answers(vendor)

    cleaned = []

    for item in faq:

        question = item.get("question", "").strip()

        answer = item.get("answer", "").strip()

        if not question:
            continue

        if not answer:
            continue

        if question.lower() == answer.lower():
            continue

        cleaned.append(item)

    vendor["question_answers"] = cleaned

    return vendor
###############################################################################
# Merge FAQs Having Same Question
###############################################################################

def merge_same_question_faq(vendor):
    """
    Merge FAQs with the same question.

    Example

    Products Used -> MAC

    Products Used -> Huda

    becomes

    Products Used -> MAC, Huda
    """

    faq = get_question_answers(vendor)

    grouped = defaultdict(list)

    for item in faq:

        question = item["question"]

        answer = item["answer"]

        grouped[question].append(answer)

    merged = []

    for question, answers in grouped.items():

        seen = set()

        unique = []

        for answer in answers:

            key = answer.lower().strip()

            if key in seen:
                continue

            seen.add(key)

            unique.append(answer)

        merged.append(
            {
                "question": question,
                "answer": ", ".join(unique),
            }
        )

    vendor["question_answers"] = merged

    return vendor


###############################################################################
# Remove Duplicate FAQ
###############################################################################

def deduplicate_faq(vendor):
    """
    Remove exact duplicate FAQs.
    """

    faq = get_question_answers(vendor)

    faq = deduplicate_by(
        faq,
        lambda x: (
            x.get("question", "").lower().strip(),
            x.get("answer", "").lower().strip(),
        ),
    )

    vendor["question_answers"] = faq

    return vendor


###############################################################################
# Remove Duplicate Answers
###############################################################################

def deduplicate_answers(vendor):
    """
    Remove duplicate values inside merged answers.

    Example

    MAC, MAC, Huda

    ↓

    MAC, Huda
    """

    faq = get_question_answers(vendor)

    cleaned = []

    for item in faq:

        values = []

        seen = set()

        for part in item["answer"].split(","):

            part = part.strip()

            if not part:
                continue

            key = part.lower()

            if key in seen:
                continue

            seen.add(key)

            values.append(part)

        item["answer"] = ", ".join(values)

        cleaned.append(item)

    vendor["question_answers"] = cleaned

    return vendor


###############################################################################
# Sort FAQ
###############################################################################

def sort_faq(vendor):
    """
    Stable ordering for deterministic output.
    """

    faq = get_question_answers(vendor)

    faq = sorted(
        faq,
        key=lambda x: (
            x.get("question", "").lower(),
            x.get("answer", "").lower(),
        ),
    )

    vendor["question_answers"] = faq

    return vendor


###############################################################################
# Remove Empty Question Answers After Merge
###############################################################################

def remove_empty_answers(vendor):

    faq = get_question_answers(vendor)

    cleaned = []

    for item in faq:

        q = item.get("question", "").strip()

        a = item.get("answer", "").strip()

        if not q:
            continue

        if not a:
            continue

        cleaned.append(item)

    vendor["question_answers"] = cleaned

    return vendor


###############################################################################
# FAQ Cleaning Pipeline
###############################################################################

def clean_faq(vendor):
    """
    Complete FAQ cleaning pipeline.
    """

    vendor = extract_since_working_year(vendor)

    vendor = normalize_faq(vendor)

    vendor = remove_blank_faq(vendor)

    vendor = merge_same_question_faq(vendor)

    vendor = deduplicate_answers(vendor)

    vendor = deduplicate_faq(vendor)

    vendor = remove_empty_answers(vendor)

    vendor = sort_faq(vendor)

    return vendor


###############################################################################
# Exports
###############################################################################

__all__ = [
    "extract_since_working_year",
    "normalize_faq",
    "remove_blank_faq",
    "merge_same_question_faq",
    "deduplicate_answers",
    "deduplicate_faq",
    "remove_empty_answers",
    "sort_faq",
    "clean_faq",
]