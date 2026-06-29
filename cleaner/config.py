"""
Global configuration for the final cleaner.

All reusable constants should live here.
"""

from datetime import datetime

CURRENT_YEAR = datetime.now().year

###########################################################################
# Generic Junk Values
###########################################################################

JUNK_VALUES = {
    "",
    ".",
    "..",
    "...",
    "-",
    "--",
    "---",
    ",",
    ",,",
    ":",
    "::",
    ";",
    "|",
    "na",
    "n/a",
    "none",
    "null",
    "nil",
    "undefined",
    "not available",
    "not applicable",
}

###########################################################################
# FAQ Questions that should become profile.since_working_year
###########################################################################

SINCE_WORKING_QUESTIONS = {
    "experience",
    "working since",
    "working from",
    "since working",
    "working year",
    "started in",
    "established in",
    "years of experience",
    "practicing makeup since",
    "practicing since",
    "makeup since",
    "business since",
}

###########################################################################
# URLs
###########################################################################

ALLOWED_VIDEO_DOMAINS = (
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
)

###########################################################################
# Regex
###########################################################################

YEAR_REGEX = r"(19|20)\s*,?\s*(\d{2})"

PHONE_REGEX = (
    r"(?<!\d)"
    r"(?:\+91[\-\s]?)?"
    r"(?:0[\-\s]?)?"
    r"[6-9]\d{9}"
    r"(?!\d)"
)

EMAIL_REGEX = (
    r"\b[A-Za-z0-9._%+-]+"
    r"@[A-Za-z0-9.-]+"
    r"\.[A-Za-z]{2,}\b"
)

URL_REGEX = (
    r"https?://[^\s]+|"
    r"www\.[^\s]+"
)

HTML_REGEX = r"<[^>]+>"

CONTROL_CHAR_REGEX = (
    r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]"
)

SPECIAL_ONLY_REGEX = r"^[^A-Za-z0-9]+$"

MULTIPLE_SPACE_REGEX = r"\s+"

###########################################################################
# Price prefixes
###########################################################################

PRICE_PREFIXES = (
    "₹",
    "rs",
    "rs.",
    "inr",
)

###########################################################################
# Fields where URLs are allowed
###########################################################################

URL_ALLOWED_FIELDS = {
    "youtube",
    "youtube_url",
    "youtube_link",
    "video_url",
    "videoLink",
}

###########################################################################
# Fields that may contain phone numbers
###########################################################################

PHONE_ALLOWED_FIELDS = {
    "phone",
    "phones",
    "mobile",
    "contact_number",
    "contact_numbers",
}

###########################################################################
# Fields that may contain emails
###########################################################################

EMAIL_ALLOWED_FIELDS = {
    "email",
    "emails",
    "login_email",
}

###########################################################################
# Coordinate limits
###########################################################################

MIN_LAT = -90.0
MAX_LAT = 90.0

MIN_LON = -180.0
MAX_LON = 180.0

###########################################################################
# Recursive cleanup
###########################################################################

REMOVE_EMPTY_LISTS = True
REMOVE_EMPTY_OBJECTS = True
REMOVE_NULL_VALUES = True
REMOVE_EMPTY_STRINGS = True

###########################################################################
# Statistics keys
###########################################################################

STAT_KEYS = [
    "vendors_processed",
    "faq_removed",
    "urls_removed",
    "videos_removed",
    "duplicate_faq_removed",
    "duplicate_prices_removed",
    "duplicate_addresses_removed",
    "duplicate_videos_removed",
    "phones_removed",
    "emails_removed",
    "empty_fields_removed",
    "prices_normalized",
    "percentages_normalized",
    "years_extracted",
]   