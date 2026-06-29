"""
Media Business Rules

Responsible for:

- Video normalization
- YouTube validation
- Document normalization
- Image normalization

This module ONLY handles media objects.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from ..normalizers import (
    normalize_document_name,
    normalize_url,
)

from .common import (
    deduplicate_by,
    get_documents,
    get_videos,
)

###############################################################################
# Supported Domains
###############################################################################

YOUTUBE_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

###############################################################################
# URL Helpers
###############################################################################

def clean_url(url):
    """
    Normalize URL.
    """

    if not url:
        return None

    url = normalize_url(str(url))

    if not url:
        return None

    return url


def is_youtube_url(url):
    """
    Return True if URL belongs to YouTube.
    """

    if not url:
        return False

    try:

        domain = urlparse(url).netloc.lower()

    except Exception:

        return False

    return domain in YOUTUBE_DOMAINS


def extract_youtube_id(url):
    """
    Extract YouTube video ID.
    """

    if not is_youtube_url(url):
        return None

    parsed = urlparse(url)

    if parsed.netloc.endswith("youtu.be"):

        video_id = parsed.path.strip("/")

        return video_id or None

    if parsed.path == "/watch":

        query = parse_qs(parsed.query)

        values = query.get("v")

        if values:

            return values[0]

    if parsed.path.startswith("/shorts/"):

        return parsed.path.split("/")[-1]

    if parsed.path.startswith("/embed/"):

        return parsed.path.split("/")[-1]

    return None


def canonical_youtube_url(video_id):
    """
    Convert every YouTube URL into one format.
    """

    if not video_id:
        return None

    return f"https://www.youtube.com/watch?v={video_id}"


###############################################################################
# Video Normalization
###############################################################################

VIDEO_URL_KEYS = (
    "video_url",
    "url",
    "link",
    "video",
)


VIDEO_TITLE_KEYS = (
    "title",
    "name",
    "label",
)


def _extract_video_url(video):

    for key in VIDEO_URL_KEYS:

        value = video.get(key)

        if value:

            return value

    return None


def _extract_video_title(video):

    for key in VIDEO_TITLE_KEYS:

        value = video.get(key)

        if isinstance(value, str):

            if value.strip():

                return value.strip()

    return ""


def _normalize_video(video):
    """
    Normalize a single video object.

    Returns None if invalid.
    """

    if not isinstance(video, dict):
        return None

    url = clean_url(
        _extract_video_url(video)
    )

    if not url:
        return None

    if not is_youtube_url(url):
        return None

    video_id = extract_youtube_id(url)

    if not video_id:
        return None

    new_video = dict(video)

    new_video["video_url"] = canonical_youtube_url(video_id)

    title = _extract_video_title(video)

    if title:

        new_video["title"] = title

    #
    # Remove aliases
    #

    for key in VIDEO_URL_KEYS:

        if key != "video_url":

            new_video.pop(key, None)

    for key in VIDEO_TITLE_KEYS:

        if key != "title":

            new_video.pop(key, None)

    return new_video


###############################################################################
# Normalize Videos
###############################################################################

def normalize_videos(vendor):
    """
    Normalize all video objects.
    """

    videos = get_videos(vendor)

    cleaned = []

    for video in videos:

        video = _normalize_video(video)

        if video is None:
            continue

        cleaned.append(video)

    videos.clear()

    videos.extend(cleaned)

    return vendor

###############################################################################
# Document Normalization
###############################################################################

DOCUMENT_NAME_KEYS = (
    "document_name",
    "name",
    "title",
)

DOCUMENT_URL_KEYS = (
    "document_url",
    "url",
    "file",
    "link",
)


def _extract_document_name(doc):

    for key in DOCUMENT_NAME_KEYS:

        value = doc.get(key)

        if isinstance(value, str) and value.strip():

            return value.strip()

    return ""


def _extract_document_url(doc):

    for key in DOCUMENT_URL_KEYS:

        value = doc.get(key)

        if value:

            return value

    return None


def _normalize_document(doc):

    if not isinstance(doc, dict):
        return None

    url = clean_url(
        _extract_document_url(doc)
    )

    if not url:
        return None

    name = normalize_document_name(
        _extract_document_name(doc)
    )

    new_doc = dict(doc)

    new_doc["document_url"] = url

    if name:
        new_doc["document_name"] = name

    #
    # Remove aliases
    #

    for key in DOCUMENT_URL_KEYS:

        if key != "document_url":

            new_doc.pop(key, None)

    for key in DOCUMENT_NAME_KEYS:

        if key != "document_name":

            new_doc.pop(key, None)

    return new_doc


###############################################################################
# Normalize Documents
###############################################################################

def normalize_documents(vendor):

    documents = get_documents(vendor)

    cleaned = []

    for doc in documents:

        doc = _normalize_document(doc)

        if doc is None:
            continue

        cleaned.append(doc)

    documents.clear()
    documents.extend(cleaned)

    return vendor


###############################################################################
# Remove Duplicate Videos
###############################################################################

def deduplicate_videos(vendor):

    videos = get_videos(vendor)

    videos[:] = deduplicate_by(
        videos,
        lambda x: x.get("video_url", "").strip().lower(),
    )

    return vendor


###############################################################################
# Remove Duplicate Documents
###############################################################################

def deduplicate_documents(vendor):

    documents = get_documents(vendor)

    documents[:] = deduplicate_by(
        documents,
        lambda x: (
            x.get("document_name", "").strip().lower(),
            x.get("document_url", "").strip().lower(),
        ),
    )

    return vendor


###############################################################################
# Remove Empty Videos
###############################################################################

def remove_empty_videos(vendor):

    videos = get_videos(vendor)

    videos[:] = [

        video

        for video in videos

        if video.get("video_url")

    ]

    return vendor


###############################################################################
# Remove Empty Documents
###############################################################################

def remove_empty_documents(vendor):

    documents = get_documents(vendor)

    documents[:] = [

        doc

        for doc in documents

        if doc.get("document_url")

    ]

    return vendor


###############################################################################
# Sort Media
###############################################################################

def sort_media(vendor):

    get_videos(vendor).sort(
        key=lambda x: (
            x.get("title", "").lower(),
            x.get("video_url", "").lower(),
        )
    )

    get_documents(vendor).sort(
        key=lambda x: (
            x.get("document_name", "").lower(),
            x.get("document_url", "").lower(),
        )
    )

    return vendor


###############################################################################
# Final Media Pipeline
###############################################################################

def clean_media(vendor):
    """
    Complete media cleaning pipeline.
    """

    vendor = normalize_videos(vendor)

    vendor = normalize_documents(vendor)

    vendor = deduplicate_videos(vendor)

    vendor = deduplicate_documents(vendor)

    vendor = remove_empty_videos(vendor)

    vendor = remove_empty_documents(vendor)

    vendor = sort_media(vendor)

    return vendor


###############################################################################
# Exports
###############################################################################

__all__ = [
    "normalize_videos",
    "normalize_documents",
    "deduplicate_videos",
    "deduplicate_documents",
    "remove_empty_videos",
    "remove_empty_documents",
    "sort_media",
    "clean_media",
]