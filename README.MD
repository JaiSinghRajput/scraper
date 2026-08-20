# wedding venues processing
uv run json_to_csv.py \
  --detail_json final_data_raw/venues/rajasthan/jaipur/raw_jaipur_venues.json \
  --listing_json final_data_raw/venues/rajasthan/jaipur/wedding_venues_jaipur_cards.json \
  --output_csv final_udaipur.csv \
  --vendor_state 83 \
  --vendor_city 86

# for scraping detail page of any category URL 
  i.e(https://www.wedmegood.com/profile/Rungg-27382)

- in KVM2 
nohup env PYTHONUNBUFFERED=1 x vfb-run -a uv run global_scraper.py --input wedding_venues_gujarat_cards.json --output scraped_data_gujarat.json > scraper.log 2>&1 & 

- in KVM4
nohup env   WAYLAND_DISPLAY=wayland-1   XDG_SESSION_TYPE=wayland   PYTHONUNBUFFERED=1   uv run global_scraper_new.py   --input bridal_wear_vendors_all_cards.json  --output scraped_bridal_wear_all.json   > scraper.log 2>&1 &

# All Scraped cards and Data is available in Final_data_raw folder
- sheet for the processed Data and uploaded to site - https://docs.google.com/spreadsheets/d/1v-m7glQC2AOjG6YMBTVw-E9oYGoB66aYp2tiW5Vruhc/edit?gid=1386834576#gid=1386834576


# to scrap listing Page Data :
everything is inside the wmg folder

their are some categories folders inside the folder
which covers all type of listing cards Data
a typical folder must contains url_scraper.py
that takes a category link as an input and scrapes all the listing cards data from it with pagination
in a single json file

and then uses the global_scraper.py to scrape detail page data of all the listing cards
and then uses the json_to_csv.py to convert the json data to csv data
