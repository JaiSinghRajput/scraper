"""
Vendor Cleaner Pipeline

This is the central orchestrator that applies
all cleaning rules in correct order.
"""

from __future__ import annotations

from .recursive import clean_json

from cleaner.rules.faq import clean_faq
from cleaner.rules.pricing import clean_pricing
from cleaner.rules.media import clean_media
from cleaner.rules.profile import (
    normalize_names,
    clean_descriptions,
    normalize_lists,
    normalize_social_links,
    normalize_since_working_year,
    remove_special_values,
    recursive_profile_cleanup,
)
from .rules.address import clean_addresses

from .validators import validate_vendor


###############################################################################
# Main Cleaner
###############################################################################

def clean_vendor(vendor: dict) -> dict:
    """
    Full vendor cleaning pipeline.
    """

    if not isinstance(vendor, dict):
        return vendor

    # 1. Recursive structural cleanup first
    vendor = clean_json(vendor)

    # 2. FAQ cleanup
    vendor = clean_faq(vendor)

    # 3. Pricing cleanup
    vendor = clean_pricing(vendor)

    # 4. Media cleanup (videos, documents)
    vendor = clean_media(vendor)

    # 5. Profile cleanup (deep normalization)
    vendor = normalize_names(vendor)
    vendor = clean_descriptions(vendor)
    vendor = normalize_lists(vendor)
    vendor = normalize_social_links(vendor)
    vendor = normalize_since_working_year(vendor)
    vendor = remove_special_values(vendor)
    vendor = recursive_profile_cleanup(vendor)

    # 6. Address cleanup
    vendor = clean_addresses(vendor)

    # 7. Final validation pass (removes bad leftovers)
    vendor = validate_vendor(vendor)

    return vendor


###############################################################################
# Batch Cleaner
###############################################################################

def clean_vendors(vendors: list[dict]) -> list[dict]:
    """
    Clean a list of vendors.
    """

    if not isinstance(vendors, list):
        return []

    cleaned = []

    for vendor in vendors:

        try:

            cleaned.append(clean_vendor(vendor))

        except Exception:
            # Skip corrupted vendor instead of breaking pipeline
            continue

    return cleaned


###############################################################################
# Export
###############################################################################

__all__ = [
    "clean_vendor",
    "clean_vendors",
]