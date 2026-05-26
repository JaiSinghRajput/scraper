import sys
import json
import time
import signal
import argparse
import random
import re

from pathlib import Path

from stem import Signal
from stem.control import Controller

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from playwright_stealth import Stealth

# ============================================================
# CONFIG
# ============================================================

TOR_PROXY = "socks5://127.0.0.1:9050"

TOR_CONTROL_PORT = 9051

HEADLESS = False

SAVE_EVERY = 1
DELAY_SECONDS = 5

MAX_RETRIES = 5
PAGE_TIMEOUT = 120000

OUTPUT_FILE = "venue_initial_states.json"
FAILED_FILE = "failed_urls.json"

STATE_CANDIDATES = [
    "__INITIAL_STATE__",
    "__NEXT_DATA__",
    "__NUXT__",
    "__APOLLO_STATE__",
    "__PRELOADED_STATE__",
]

USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
]

VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
]

# ============================================================
# DEBUG DIRECTORIES
# ============================================================

DEBUG_DIR = Path("debug")

HTML_DIR = DEBUG_DIR / "html"
SCREENSHOT_DIR = DEBUG_DIR / "screenshots"
SCRIPT_DIR = DEBUG_DIR / "scripts"
NETWORK_DIR = DEBUG_DIR / "network"
STATE_DIR = DEBUG_DIR / "states"
CONSOLE_DIR = DEBUG_DIR / "console"
FAILURE_DIR = DEBUG_DIR / "failures"

for d in [
    HTML_DIR,
    SCREENSHOT_DIR,
    SCRIPT_DIR,
    NETWORK_DIR,
    STATE_DIR,
    CONSOLE_DIR,
    FAILURE_DIR,
]:
    d.mkdir(
        parents=True,
        exist_ok=True,
    )

# ============================================================
# GLOBALS
# ============================================================

shutdown_requested = False
playwright_instance = None
browser_instance = None

# ============================================================
# SIGNAL HANDLING
# ============================================================


def handle_shutdown(signum, frame):

    global shutdown_requested
    global browser_instance
    global playwright_instance

    shutdown_requested = True

    print("\n⚠️ Shutdown requested...")

    try:

        if browser_instance:
            browser_instance.close()

    except Exception:
        pass

    try:

        if playwright_instance:
            playwright_instance.stop()

    except Exception:
        pass

    print("✅ Clean shutdown complete")

    sys.exit(0)


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

# ============================================================
# HELPERS
# ============================================================


def safe_filename(url):

    name = re.sub(
        r"[^a-zA-Z0-9]",
        "_",
        url,
    )

    return name[:180]


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

    except Exception:

        return []


def renew_tor_ip():

    try:

        with Controller.from_port(
            port=9051
        ) as controller:

            controller.authenticate(
                password="mypassword123"
            )

            controller.signal(
                Signal.NEWNYM
            )

        print("🔄 Requested new Tor IP")

        time.sleep(15)

    except Exception as e:

        print(
            f"⚠️ Tor rotation failed: {e}"
        )

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
# PLAYWRIGHT
# ============================================================


def launch_browser():

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=HEADLESS,
        proxy={
            "server": TOR_PROXY
        },
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ],
    )

    return playwright, browser


# ============================================================
# CONTEXT
# ============================================================


def create_context(browser):

    context = browser.new_context(
        viewport=random.choice(
            VIEWPORTS
        ),
        user_agent=random.choice(
            USER_AGENTS
        ),
        locale="en-US",
        timezone_id="Asia/Kolkata",
        java_script_enabled=True,
    )

    return context


# ============================================================
# DEBUG SAVE HELPERS
# ============================================================


def save_scripts(page, slug):

    scripts = page.locator("script")

    all_scripts = []

    count = scripts.count()

    for i in range(count):

        try:

            txt = scripts.nth(i).inner_text()

            if txt.strip():

                all_scripts.append({
                    "index": i,
                    "content": txt,
                })

        except Exception:
            pass

    (
        SCRIPT_DIR / f"{slug}.json"
    ).write_text(
        json.dumps(
            all_scripts,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


# ============================================================
# STATE EXTRACTION
# ============================================================


def extract_state(page):

    found = {}

    for candidate in STATE_CANDIDATES:

        try:

            data = page.evaluate(
                f"() => window.{candidate}"
            )

            if data:

                found[candidate] = data

        except Exception:
            pass

    return found


# ============================================================
# HUMAN BEHAVIOR
# ============================================================


def simulate_human(page):

    try:

        page.mouse.move(
            random.randint(100, 700),
            random.randint(100, 700),
        )

        page.wait_for_timeout(
            random.randint(1000, 3000)
        )

        page.mouse.wheel(
            0,
            random.randint(300, 1200)
        )

        page.wait_for_timeout(
            random.randint(1000, 3000)
        )

    except Exception:
        pass


# ============================================================
# CURRENT IP CHECK
# ============================================================


def print_current_ip(context):

    page = context.new_page()

    try:

        page.goto(
            "https://api.ipify.org?format=json",
            timeout=30000,
        )

        body = page.text_content("body")

        print(
            f"🌍 Current IP: {body}"
        )

    except Exception as e:

        print(
            f"⚠️ Could not fetch IP: {e}"
        )

    finally:

        page.close()


# ============================================================
# SCRAPE URL
# ============================================================


def scrape_url(browser, url):

    last_error = None

    slug = safe_filename(url)

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        context = None
        page = None

        network_logs = []
        console_logs = []

        try:

            # ============================================
            # NEW TOR IP
            # ============================================

            renew_tor_ip()

            # ============================================
            # NEW CONTEXT
            # ============================================

            context = create_context(
                browser
            )

            print_current_ip(
                context
            )

            page = context.new_page()

            # ============================================
            # STEALTH
            # ============================================

            page = context.new_page()
            stealth = Stealth()
            stealth.apply_stealth_sync(page)

            # ============================================
            # NETWORK LOGGING
            # ============================================

            def handle_response(response):

                try:

                    ct = response.headers.get(
                        "content-type",
                        ""
                    )

                    if (
                        "json" in ct
                        or "/api/" in response.url
                        or "graphql" in response.url
                    ):

                        try:
                            body = response.text()

                        except Exception:
                            body = ""

                        network_logs.append({
                            "url": response.url,
                            "status": response.status,
                            "content_type": ct,
                            "body": body[:50000],
                        })

                except Exception:
                    pass

            page.on(
                "response",
                handle_response
            )

            # ============================================
            # CONSOLE LOGGING
            # ============================================

            page.on(
                "console",
                lambda msg: console_logs.append({
                    "type": msg.type,
                    "text": msg.text,
                })
            )

            page.on(
                "pageerror",
                lambda err: console_logs.append({
                    "type": "pageerror",
                    "text": str(err),
                })
            )

            # ============================================
            # OPEN PAGE
            # ============================================

            print(
                f"🌐 Opening: {url}"
            )

            response = page.goto(
                url,
                wait_until="networkidle",
                timeout=PAGE_TIMEOUT,
            )

            if response:

                print(
                    f"📡 Status: {response.status}"
                )

            # ============================================
            # HUMAN SIMULATION
            # ============================================

            simulate_human(page)

            page.wait_for_timeout(
                random.randint(5000, 9000)
            )

            # ============================================
            # SAVE HTML
            # ============================================

            html = page.content()

            (
                HTML_DIR / f"{slug}.html"
            ).write_text(
                html,
                encoding="utf-8",
            )

            # ============================================
            # SCREENSHOT
            # ============================================

            page.screenshot(
                path=str(
                    SCREENSHOT_DIR / f"{slug}.png"
                ),
                full_page=True,
            )

            # ============================================
            # SAVE SCRIPTS
            # ============================================

            save_scripts(
                page,
                slug,
            )

            # ============================================
            # SAVE NETWORK
            # ============================================

            (
                NETWORK_DIR / f"{slug}.json"
            ).write_text(
                json.dumps(
                    network_logs,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            # ============================================
            # SAVE CONSOLE
            # ============================================

            (
                CONSOLE_DIR / f"{slug}.json"
            ).write_text(
                json.dumps(
                    console_logs,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            # ============================================
            # EXTRACT STATE
            # ============================================

            states = extract_state(page)

            (
                STATE_DIR / f"{slug}.json"
            ).write_text(
                json.dumps(
                    states,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            # ============================================
            # CLOUDFLARE DETECTION
            # ============================================

            if (
                "cloudflare"
                in html.lower()
                or "attention required"
                in html.lower()
            ):

                raise Exception(
                    "Cloudflare block detected"
                )

            print(
                f"✅ Success | "
                f"States found: "
                f"{list(states.keys())}"
            )

            return {
                "url": url,
                "states": states,
                "scraped_at": int(
                    time.time()
                ),
            }

        except PlaywrightTimeoutError:

            last_error = "Timeout"

        except Exception as e:

            last_error = str(e)

        finally:

            try:

                if page:
                    page.close()

            except Exception:
                pass

            try:

                if context:
                    context.close()

            except Exception:
                pass

        # ============================================
        # FAILURE LOG
        # ============================================

        failure_dump = {
            "url": url,
            "error": last_error,
            "attempt": attempt,
            "time": int(time.time()),
        }

        (
            FAILURE_DIR / f"{slug}.json"
        ).write_text(
            json.dumps(
                failure_dump,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print(
            f"⚠️ Retry "
            f"{attempt}/{MAX_RETRIES} "
            f"-> {last_error}"
        )

        time.sleep(
            random.randint(5, 15)
        )

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
# MAIN
# ============================================================


def run_scraper(
    input_file,
    output_file,
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

    playwright, browser = launch_browser()

    try:

        for idx, url in enumerate(
            urls,
            start=1,
        ):

            if shutdown_requested:
                break

            if url in completed_urls:

                print(
                    f"[{idx}] ⏭️ Skipping"
                )

                continue

            print(
                f"\n[{idx}/{len(urls)}]"
            )

            try:

                result = scrape_url(
                    browser,
                    url,
                )

                results.append(result)

                completed_urls.add(url)

                atomic_write_json(
                    results,
                    output_file,
                )

            except Exception as e:

                print(
                    f"❌ FAILED: {e}"
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
                    FAILED_FILE,
                )

            time.sleep(
                random.randint(3, 10)
            )

    finally:

        print(
            "\n💾 Saving..."
        )

        atomic_write_json(
            results,
            output_file,
        )

        browser.close()

        playwright.stop()

    print("\n✅ DONE")


# ============================================================
# CLI
# ============================================================


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Advanced stealth scraper"
        )
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Input JSON file",
    )

    parser.add_argument(
        "--output",
        "-o",
        default=OUTPUT_FILE,
        help="Output file",
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