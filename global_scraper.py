import sys
import json
import time
import signal
import argparse
from pathlib import Path

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

# ============================================================
# CONFIG
# ============================================================

TOR_PROXY = "socks5://127.0.0.1:9050"

HEADLESS = True

SAVE_EVERY = 1
DELAY_SECONDS = 2

MAX_RETRIES = 4
PAGE_TIMEOUT = 90000

OUTPUT_FILE = "venue_initial_states.json"
FAILED_FILE = "failed_urls.json"

STATE_CANDIDATES = [
    "__INITIAL_STATE__",
    "__NEXT_DATA__",
    "__NUXT__",
    "__APOLLO_STATE__",
]

# ============================================================
# GLOBALS
# ============================================================

shutdown_requested = False


# ============================================================
# SIGNAL HANDLING
# ============================================================

def handle_shutdown(signum, frame):
    global shutdown_requested
    shutdown_requested = True

    print(
        "\n⚠️ Shutdown requested."
        " Finishing current URL safely..."
    )


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


# ============================================================
# JSON HELPERS
# ============================================================

def load_json_file(path):

    p = Path(path)

    if not p.exists():
        return []

    try:

        raw = p.read_text(
            encoding="utf-8"
        ).strip()

        if not raw:
            return []

        return json.loads(raw)

    except Exception as e:

        backup = p.with_suffix(
            f".broken.{int(time.time())}.json"
        )

        print(
            f"⚠️ Corrupted JSON detected: {path}"
        )

        print(
            f"⚠️ Moving broken file -> {backup}"
        )

        p.rename(backup)

        return []


def atomic_write_json(data, path):

    p = Path(path)

    tmp = p.with_suffix(".tmp")

    tmp.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    tmp.replace(p)


# ============================================================
# INPUT URLS
# ============================================================

def extract_urls(data):

    urls = []

    for item in data:

        if isinstance(item, dict):

            url = item.get("url")

            if url:
                urls.append(url)

    return urls


def load_urls(input_file):

    data = load_json_file(input_file)

    urls = extract_urls(data)

    if not urls:
        raise Exception(
            "No URLs found in input JSON"
        )

    return urls


# ============================================================
# PLAYWRIGHT / TOR
# ============================================================

def launch_browser():

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=HEADLESS,
        proxy={
            "server": TOR_PROXY
        },
    )

    context = browser.new_context(
        viewport={
            "width": 1400,
            "height": 900
        },
        user_agent=(
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
    )

    return playwright, browser, context


# ============================================================
# STATE EXTRACTION
# ============================================================

def extract_state(page):

    script = f"""
    () => {{

        const candidates = {json.dumps(STATE_CANDIDATES)};

        for (const key of candidates) {{

            try {{

                if (window[key]) {{

                    return {{
                        key,
                        data: JSON.stringify(window[key])
                    }};
                }}

            }} catch (e) {{}}
        }}

        return null;
    }}
    """

    result = page.evaluate(script)

    if not result:
        return None, None

    return (
        result["key"],
        json.loads(result["data"])
    )


# ============================================================
# SCRAPE URL
# ============================================================

def scrape_url(context, url):

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        page = None

        try:

            page = context.new_page()

            response = page.goto(
                url,
                wait_until="networkidle",
                timeout=PAGE_TIMEOUT,
            )

            if response:

                status = response.status

                if status == 404:
                    raise Exception(
                        "404 Not Found"
                    )

                if status == 429:
                    raise Exception(
                        "429 Too Many Requests"
                    )

            # Stabilization
            page.wait_for_timeout(3000)

            state_name, state_data = (
                extract_state(page)
            )

            if state_data is None:

                raise Exception(
                    "No state object found"
                )

            return {
                "url": url,
                "state_type": state_name,
                "initial_state": state_data,
                "scraped_at": int(
                    time.time()
                ),
            }

        except PlaywrightTimeoutError:

            last_error = "Timeout"

        except Exception as e:

            last_error = str(e)

        finally:

            if page:
                page.close()

        print(
            f"  ⚠️ Retry "
            f"{attempt}/{MAX_RETRIES} "
            f"for {url} "
            f"-> {last_error}"
        )

        time.sleep(5)

    raise Exception(last_error)


# ============================================================
# RESUME SUPPORT
# ============================================================

def load_existing_output(output_path):

    existing = load_json_file(
        output_path
    )

    completed = set()

    for item in existing:

        if (
            isinstance(item, dict)
            and "url" in item
        ):

            completed.add(item["url"])

    return existing, completed


# ============================================================
# MAIN SCRAPER
# ============================================================

def run_scraper(
    input_file,
    output_file
):

    urls = load_urls(input_file)

    existing_data, completed_urls = (
        load_existing_output(
            output_file
        )
    )

    failed_urls = load_json_file(
        FAILED_FILE
    )

    results = list(existing_data)

    print(
        f"\n📦 Input URLs: {len(urls)}"
    )

    print(
        f"✅ Already completed: "
        f"{len(completed_urls)}"
    )

    print(
        f"❌ Previous failures: "
        f"{len(failed_urls)}\n"
    )

    playwright, browser, context = (
        launch_browser()
    )

    try:

        for idx, url in enumerate(
            urls,
            start=1
        ):

            if shutdown_requested:
                break

            if url in completed_urls:

                print(
                    f"[{idx}/{len(urls)}] "
                    f"⏭️ Skipping completed"
                )

                continue

            print(
                f"[{idx}/{len(urls)}] "
                f"{url}"
            )

            try:

                result = scrape_url(
                    context,
                    url
                )

                results.append(result)

                completed_urls.add(url)

                print(
                    f"  ✅ "
                    f"{result['state_type']} "
                    f"| "
                    f"keys="
                    f"{len(result['initial_state'])}"
                )

                # ========================================
                # CHECKPOINT SAVE
                # ========================================

                if (
                    len(results)
                    % SAVE_EVERY
                    == 0
                ):

                    atomic_write_json(
                        results,
                        output_file
                    )

            except Exception as e:

                print(
                    f"  ❌ FAILED: {e}"
                )

                failed_urls.append({
                    "url": url,
                    "error": str(e),
                    "time": int(
                        time.time()
                    ),
                })

                atomic_write_json(
                    failed_urls,
                    FAILED_FILE
                )

            time.sleep(DELAY_SECONDS)

    finally:

        print(
            "\n💾 Saving final checkpoint..."
        )

        atomic_write_json(
            results,
            output_file
        )

        browser.close()
        playwright.stop()

    print("\n✅ Done")


# ============================================================
# CLI
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Scrape window.__INITIAL_STATE__ "
            "objects from venue URLs"
        )
    )

    parser.add_argument(
        "--input",
        help=(
            "Input JSON file generated "
            "from venue parser"
        )
    )

    parser.add_argument(
        "--output",
        "-o",
        default=OUTPUT_FILE,
        help="Output JSON file"
    )

    return parser.parse_args()


def main():

    args = parse_args()

    run_scraper(
        input_file=args.input,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()