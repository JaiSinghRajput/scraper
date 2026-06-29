uv run json_to_csv.py \
  --detail_json final_data_raw/venues/rajasthan/jaipur/raw_jaipur_venues.json \
  --listing_json final_data_raw/venues/rajasthan/jaipur/wedding_venues_jaipur_cards.json \
  --output_csv final_udaipur.csv \
  --vendor_state 83 \
  --vendor_city 86


  KVM2 
  nohup env PYTHONUNBUFFERED=1 xvfb-run -a uv run global_scraper.py --input wedding_venues_gujarat_cards.json --output scraped_data_gujarat.json > scraper.log 2>&1 & 

 KVM4
 nohup env   WAYLAND_DISPLAY=wayland-1   XDG_SESSION_TYPE=wayland   PYTHONUNBUFFERED=1   uv run global_scraper_new.py   --input bridal_wear_vendors_all_cards.json  --output scraped_bridal_wear_all.json   > scraper.log 2>&1 &
