from __future__ import annotations
"""
Final Cleaning Script (CLI)

This script:
- Loads raw vendor JSON
- Runs full cleaning pipeline
- Writes cleaned output
- Prints basic stats
"""


import json
import sys
from pathlib import Path
from datetime import datetime

from cleaner.vendor_cleaner import clean_vendors


###############################################################################
# Stats Tracker
###############################################################################

class Stats:
    def __init__(self):

        self.total = 0
        self.cleaned = 0
        self.failed = 0

    def log_success(self):
        self.cleaned += 1

    def log_fail(self):
        self.failed += 1


###############################################################################
# Load JSON
###############################################################################

def load_json(file_path: str):

    path = Path(file_path)

    if not path.exists():

        raise FileNotFoundError(f"File not found: {file_path}")

    with open(path, "r", encoding="utf-8") as f:

        return json.load(f)


###############################################################################
# Save JSON
###############################################################################

def save_json(data, file_path: str):

    path = Path(file_path)

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:

        json.dump(data, f, ensure_ascii=False, indent=2)


###############################################################################
# Main Runner
###############################################################################

def run(input_file: str, output_file: str):

    stats = Stats()

    print("\n==============================")
    print("  VENDOR CLEANER STARTED")
    print("==============================\n")

    print(f"Input : {input_file}")
    print(f"Output: {output_file}\n")

    data = load_json(input_file)

    if isinstance(data, dict):

        # single vendor case
        data = [data]

    if not isinstance(data, list):

        raise ValueError("Input JSON must be list or dict")

    stats.total = len(data)

    print(f"Total vendors: {stats.total}\n")

    cleaned = []

    for vendor in data:

        try:

            cleaned_vendor = clean_vendors([vendor])[0]

            cleaned.append(cleaned_vendor)

            stats.log_success()

        except Exception:

            stats.log_fail()

            continue

    save_json(cleaned, output_file)

    print("\n==============================")
    print("  CLEANING COMPLETE")
    print("==============================")

    print(f"Total   : {stats.total}")
    print(f"Cleaned : {stats.cleaned}")
    print(f"Failed  : {stats.failed}")
    print(f"Success : {round(stats.cleaned / max(stats.total,1) * 100, 2)}%")

    print(f"\nSaved to: {output_file}\n")

    print("Done at:", datetime.now().isoformat())


###############################################################################
# CLI Entry
###############################################################################

if __name__ == "__main__":

    if len(sys.argv) < 3:

        print("\nUsage:")
        print("python final_clean.py <input.json> <output.json>\n")

        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    run(input_file, output_file)