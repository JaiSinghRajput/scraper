import sys
import json
import time
import signal
import argparse
import random
import re
import subprocess

from pathlib import Path

from stem import Signal
from stem.control import Controller

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

# ============================================================
# CONFIG
# ============================================================

TOR_PROXY = "socks5://127.0.0.1:9050"

TOR_CONTROL_PORT = 9051
TOR_PASSWORD = "mypassword123"

HEADLESS = False

MAX_RETRIES = 5
PAGE_TIMEOUT = 120000

OUTPUT_FILE = "scraped_data.json"
FAILED_FILE = "failed_urls.json"

DATA_DIR = Path("data")
BACKUP_DIR = Path("backup")

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

BACKUP_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

STATE_CANDIDATES = [
    "__INITIAL_STATE__",
    "__NEXT_DATA__",
    "__NUXT__",
    "__APOLLO_STATE__",
    "__PRELOADED_STATE__",
]

USER_AGENTS = [
    (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64; rv:126.0) "
        "Gecko/20100101 Firefox/126.0"
    ),
    (
        "Mozilla/5.0 "
        "(X11; Linux x86_64; rv:126.0) "
        "Gecko/20100101 Firefox/126.0"
    ),
]

VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
]

# ============================================================
# GLOBALS
# ============================================================

shutdown_requested = False
playwright_instance = None
browser_context = None

# ============================================================
# SIGNAL HANDLING
# ============================================================


def handle_shutdown(signum, frame):

    global shutdown_requested
    global browser_context
    global playwright_instance

    shutdown_requested = True

    print("\n⚠️ Shutdown requested...")

    try:

        if browser_context:
            browser_context.close()

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


def backup_output_file(path):

    p = Path(path)

    if not p.exists():
        return

    ts = int(time.time())

    backup_path = (
        BACKUP_DIR
        / f"{p.stem}_{ts}.json"
    )

    backup_path.write_text(
        p.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

def reset_browser_profile():

    profile_path = Path(
        "./browser_profile"
    )

    try:

        if profile_path.exists():

            import shutil

            shutil.rmtree(
                profile_path
            )

            print(
                "🧹 browser_profile reset"
            )

    except Exception as e:

        print(
            f"⚠️ Failed to reset "
            f"browser_profile: {e}"
        )

def restart_tor_service():

    try:

        print("🔄 Restarting Tor service...")

        result = subprocess.run(
            [
                "sudo",
                "systemctl",
                "restart",
                "tor"
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:

            print(
                "✅ Tor service restarted"
            )

        else:

            print(
                f"⚠️ Tor restart failed: "
                f"{result.stderr}"
            )

        print(
            "⏳ Waiting for Tor bootstrap..."
        )

        time.sleep(15)

    except Exception as e:

        print(
            f"⚠️ Failed to restart Tor: {e}"
        )
# ============================================================
# TOR
# ============================================================


def renew_tor_ip():

    try:

        with Controller.from_port(
            port=TOR_CONTROL_PORT
        ) as controller:

            controller.authenticate(
                password=TOR_PASSWORD
            )

            controller.signal(
                Signal.NEWNYM
            )

        print("🔄 New Tor IP requested")

        time.sleep(15)

    except Exception as e:

        print(
            f"⚠️ Tor rotation failed: {e}"
        )


# ============================================================
# URLS
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
# BROWSER
# ============================================================


def launch_browser():

    playwright = sync_playwright().start()

    context = playwright.firefox.launch_persistent_context(
        user_data_dir="./browser_profile",

        headless=HEADLESS,

        proxy={
            "server": TOR_PROXY
        },

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

    return playwright, context


# ============================================================
# HUMAN BEHAVIOR
# ============================================================


def simulate_human(page):

    try:

        page.wait_for_timeout(
            random.randint(3000, 5000)
        )

        page.mouse.move(
            random.randint(100, 500),
            random.randint(100, 500),
        )

        page.wait_for_timeout(
            random.randint(1000, 3000)
        )

        page.mouse.wheel(
            0,
            random.randint(300, 1000)
        )

        page.wait_for_timeout(
            random.randint(2000, 4000)
        )

    except Exception:
        pass


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

def find_vendor_profile(obj):

    if isinstance(obj, dict):

        if "vendorProfile" in obj:

            return obj["vendorProfile"]

        for value in obj.values():

            result = find_vendor_profile(
                value
            )

            if result is not None:

                return result

    elif isinstance(obj, list):

        for item in obj:

            result = find_vendor_profile(
                item
            )

            if result is not None:

                return result

    return None
# ============================================================
# SCRAPE
# ============================================================


def scrape_url(playwright, context, url):

    slug = safe_filename(url)

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        page = None

        try:

            renew_tor_ip()

            page = context.new_page()

            page.add_init_script("""
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

window.chrome = {
    runtime: {}
};

Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
});

Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});
""")

            print(f"🌐 {url}")

            response = page.goto(url,wait_until="domcontentloaded",timeout=PAGE_TIMEOUT,)
            status_code = None
            if response:
                status_code = response.status

                print(
                    f"📡 Status: {status_code}"
                )
            # ====================================================
            # RESET PROFILE ON BAD STATUS
            # ====================================================

            if status_code != 200:

                try:

                    context.close()

                except Exception:
                    pass

                reset_browser_profile()
                restart_tor_service()

                context = playwright.firefox.launch_persistent_context(
                    user_data_dir="./browser_profile",

                    headless=HEADLESS,

                    proxy={
                        "server": TOR_PROXY
                    },

                    viewport=random.choice(
                        VIEWPORTS
                    ),

                    user_agent=random.choice(
                        USER_AGENTS
                    ),

                    locale="en-US",

                    timezone_id="Asia/Kolkata",

                    java_script_enabled=True,

                    firefox_user_prefs={
                        "media.peerconnection.enabled": False,
                    },
                )

                raise Exception(
                    f"Bad status code: {status_code}"
                )

            simulate_human(page)

            page.wait_for_timeout(
                random.randint(5000, 8000)
            )

            html = page.content()

            # ====================================================
            # SAVE HTML
            # ====================================================

            (
                DATA_DIR / f"{slug}.html"
            ).write_text(
                html,
                encoding="utf-8",
            )

            states = extract_state(page)

            vendor_profile = None

            for _, state_data in states.items():

                vendor_profile = find_vendor_profile(
                    state_data
                )

                if vendor_profile:

                    break

            html_lower = html.lower()

            blocked_markers = [
                "sorry, you have been blocked",
                "attention required!",
                "cf-error-code",
                "cf-browser-verification",
            ]

            is_blocked = any(
                marker in html_lower
                for marker in blocked_markers
            )

            if is_blocked and not vendor_profile:
                restart_tor_service()
                reset_browser_profile()
                
                raise Exception(
                    "Cloudflare block detected"
                )

            if not vendor_profile:

                raise Exception(
                    "vendorProfile not found"
                )

            print("✅ vendorProfile found")

            return {
                "url": url,
                "vendorProfile": vendor_profile,
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

        print(
            f"⚠️ Retry "
            f"{attempt}/{MAX_RETRIES} "
            f"-> {last_error}"
        )

        time.sleep(
            random.randint(8, 15)
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

    backup_output_file(
        output_file
    )

    print(
        f"\n📦 Total URLs: {len(urls)}"
    )

    playwright, context = launch_browser()

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
                            playwright,
                            context,
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
                random.randint(5, 10)
            )

    finally:

        print(
            "\n💾 Saving..."
        )

        atomic_write_json(
            results,
            output_file,
        )

        context.close()

        playwright.stop()

    print("\n✅ DONE")


# ============================================================
# CLI
# ============================================================


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Tor Firefox scraper"
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
        help="Output JSON file",
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