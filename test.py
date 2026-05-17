import requests
from bs4 import BeautifulSoup
import json
import re


# =========================================================
# CONFIG
# =========================================================

PROFILE_URL = "https://www.wedmegood.com/profile/WeddingGo-Company-25130184"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


# =========================================================
# BUILD ALBUMS URL
# =========================================================

ALBUMS_URL = PROFILE_URL.rstrip("/") + "/albums"

print("Albums URL:")
print(ALBUMS_URL)


# =========================================================
# REQUEST
# =========================================================

response = requests.get(
    ALBUMS_URL,
    headers=HEADERS,
    timeout=30
)

print("\nStatus:", response.status_code)

html = response.text

print("HTML Length:", len(html))


# =========================================================
# PARSE
# =========================================================

soup = BeautifulSoup(html, "html.parser")


# =========================================================
# EXTRACT VIDEOS
# =========================================================

videos = []


# =========================================================
# METHOD 1
# Extract youtube IDs directly from HTML
# =========================================================

youtube_ids = re.findall(
    r'youtube_\d+_([A-Za-z0-9_-]{5,})\.jpg',
    html
)

youtube_ids = list(set(youtube_ids))


# =========================================================
# METHOD 2
# Extract titles from video blocks
# =========================================================

video_blocks = soup.select(".VideoItem")

print("\nVideo blocks found:", len(video_blocks))


title_map = {}

for block in video_blocks:

    title = None

    title_tag = block.select_one(".video-detail")

    if title_tag:
        title = title_tag.get_text(" ", strip=True)

    style = block.get("style", "")

    yt_match = re.search(
        r'youtube_\d+_([A-Za-z0-9_-]+)\.',
        style
    )

    if yt_match:

        youtube_id = yt_match.group(1)

        title_map[youtube_id] = title


# =========================================================
# BUILD FINAL VIDEOS
# =========================================================

for youtube_id in youtube_ids:

    video = {
        "youtube_id": youtube_id,
        "youtube_url": f"https://www.youtube.com/watch?v={youtube_id}",
        "title": title_map.get(youtube_id)
    }

    videos.append(video)


# =========================================================
# OUTPUT
# =========================================================

print("\n===================================")
print(f"VIDEOS FOUND: {len(videos)}")
print("===================================\n")

print(json.dumps(
    videos,
    indent=4,
    ensure_ascii=False
))