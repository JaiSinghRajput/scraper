# Vendor Data Scraper & Processor

This project provides a comprehensive scraping and data processing pipeline designed to extract vendor details from listing websites. Due to structural differences in the data, the process is divided into two distinct pipelines based on the category of vendors.

## 🗂️ Data Storage & Tracking

- **Raw Data Directory:** All scraped cards and detailed data are saved within the `final_data_raw` folder.
- **Processed Data Tracking:** Check the [Google Spreadsheet](https://docs.google.com/spreadsheets/d/1v-m7glQC2AOjG6YMBTVw-E9oYGoB66aYp2tiW5Vruhc/edit?gid=1386834576#gid=1386834576) for the status of processed and uploaded data.

---

## 🚀 Pipeline A: Wedding Venues

This pipeline is specifically tailored for the **Wedding Venues** category.

### 1. Scraping Listing Page Data

Everything related to scraping initial listing pages is located inside the `wmg` directory. 

- This folder contains category-specific subfolders.
- A typical folder contains a script named `url_scraper.py`.
- **Function:** Takes a category link as input, handles pagination, and scrapes basic listing cards' data into a single JSON file.

### 2. Scraping Detailed Profile Pages

Once you have the JSON file with the listing cards, use the global scraper scripts to extract comprehensive data from each vendor's detailed profile page.

**Example (In KVM2 Environment):**
```bash
nohup env PYTHONUNBUFFERED=1 xvfb-run -a uv run global_scraper.py \
  --input wedding_venues_gujarat_cards.json \
  --output scraped_data_gujarat.json > scraper.log 2>&1 &
```

### 3. Converting JSON Data to CSV

After collecting the detailed JSON data, use `json_to_csv.py` to merge and convert the JSON files into a structured CSV format.

```bash
uv run json_to_csv.py \
  --detail_json final_data_raw/venues/rajasthan/jaipur/raw_jaipur_venues.json \
  --listing_json final_data_raw/venues/rajasthan/jaipur/wedding_venues_jaipur_cards.json \
  --output_csv final_udaipur.csv \
  --vendor_state 83 \
  --vendor_city 86
```

### 4. Further Processing (City Filler for Entire States)

If you scraped data for an **entire state**, further processing is required to map the cities correctly.

1. **Generate State Cities File:** Use `cityjson.py` to generate a `cities.json` specifically for that state.
2. **Match Cities:** Run `city_filler.py` using the final CSV from Step 3 and the generated state `cities.json`.
3. **Output:** It will produce two files:
   - A matched file (your final, ready-to-import data).
   - An unmatched file for manual review.

---

## 🚀 Pipeline B: Other Categories (e.g., Bridal Wear, Makeup, etc.)

For all other categories, the process skips the state/city specific scraping and instead scrapes all listings directly. It follows a distinct cleaning and formatting pipeline.

### 1. Scraping Detailed Data
Similar to Pipeline A, but we use scripts like `global_scraper_new.py` for all listings across the category.
```bash
nohup env WAYLAND_DISPLAY=wayland-1 XDG_SESSION_TYPE=wayland PYTHONUNBUFFERED=1 uv run global_scraper_new.py \
  --input bridal_wear_vendors_all_cards.json \
  --output scraped_bridal_wear_all.json > scraper.log 2>&1 &
```

### 2. Data Formatting
Pass the detailed listing JSON through `formator.py`. This script performs initial operations and standardizes the structure, producing an intermediate output JSON file.

### 3. Vendor Data Cleaning
Pass the formatted JSON from the previous step to `clean_vendor_data.py`. This step cleans up fields (like parsing "Practicing Since" years, fixing percentage strings, etc.) and generates a cleaned output file.

### 4. Price Cleaning
Pass the cleaned vendor data to `clean_price.py`. This standardizes the price formatting (e.g., converting Indian comma separators) and outputs the **final comprehensive clean JSON file**.

### 5. Final Conversion to CSV
Convert the final clean JSON into a CSV file using `json2csv.py`. 
*Note: This script requires both the global `cities.json` and `states.json` files as inputs to properly map the location data.*

---

## 🛠️ Environment

This project utilizes `uv` as the Python package manager and runner. Make sure your environment is properly set up before executing the scripts.
