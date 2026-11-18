# Wedding venue finder

Finds every wedding venue in a country, reads each venue's website with AI, scores it against your brief, and builds a swipe page with photos, a map, filters and yes / maybe / no votes.

Built for a search across Ireland. It found 2,530 places, read 321 websites and produced a scored shortlist of 168. The results are in `sample-ireland/`.

## What you need

You run this yourself, with your own accounts. Nothing is hosted.

| Service | Used for | Sign up |
|---|---|---|
| Apify | Google Maps listings and photos | apify.com |
| Serper | Google search results | serper.dev |
| Firecrawl | Reading venue websites | firecrawl.dev |
| OpenAI | Scoring each venue against your brief | platform.openai.com |

Our budget for the whole Ireland search was $30. Yours depends on country size.

You also need Python 3 with `pillow` and `openpyxl` (`pip install pillow openpyxl`).

## Easiest way to run it

Open this folder in Claude Code or Codex and paste:

> Read README.md and every script in this folder. I want to find wedding venues in [country / region], at least [N] hours' drive from [city]. My brief is in brief.txt. Adapt the country-specific parts listed in the README, fill the gaps it lists, then run the stages in order. Tell me the cost before each paid step and stop for my yes.

## Run it by hand

1. Copy `.env.example` to `.env` and add your keys.
2. Write your own `brief.txt`. The AI scores every venue against it.
3. Change the country-specific parts (see below).
4. Run the stages in order.

| Stage | Script | What it does |
|---|---|---|
| 1a | `01_apify_gmaps.sh` | Starts Google Maps searches for venues |
| 1b | `02_serper.py` | Google searches by county |
| 1c | `03_directories.py` | Wedding directory listings (hitched.ie, weddingsonline.ie) |
| 2 | `04_merge_geo.py` | Merges everything, removes duplicates, adds drive time |
| 3 | `05_classify.py` | Reads each website and scores it against your brief |
| 3b | `07_rescue.py` | Second try for venues whose wedding page was missed |
| 4 | `08_enrich.py`, `10_coast.py`, `12_emails.py`, `13_links.py` | Rooms, phone, email, distance to the sea, Instagram and gallery links |
| 5 | `11_images.py`, `14_more_images.py`, `15_shortlist_images.py` | Photos |
| 6 | `16_rooms.py`, `17_vision.py` | Double-checks room counts and that each photo really is the venue |
| 7 | `06_build_output.py` | Builds the spreadsheet and the swipe page in `out/` |

## Country-specific parts to change

- `01_apify_gmaps.sh`: the location and country code at the bottom.
- `02_serper.py`: the county list and `gl` country code.
- `03_directories.py`: Irish directories. Swap for your country's, or skip.
- `04_merge_geo.py`: `DUB` is the city drive times are measured from.
- `05_classify.py`: the minimum drive time (default 2.75 hours).
- `06_build_output.py`: `hard_fail()` holds the pass / fail rules: capacity, price per head, drive time. `BENCH` is an optional list of venues you already like.
- `10_coast.py`: needs a coastline file and a beaches file for your country.

## Known gaps

These scripts are the real ones we ran, cleaned of private settings. A few steps between them were done by hand and are not scripted. They have not been re-run end to end since the clean-up.

- After stage 1a, download each Apify run's results to `data/gmaps_<runid>.json`.
- After stage 1b, reduce `data/serper_raw.jsonl` to a list of venue domains in `data/serper_domains.json`.
- Before stage 3, filter `data/universe.json` to the candidates worth reading and save as `data/shortlist_input.json`.
- Before stage 6, save the venues you voted yes or maybe as `data/shortlist_keys.json`, and download Google Maps photos to `data/gmaps_photos.json`.
- `10_coast.py` expects `data/ne_coast.geojson` (Natural Earth coastline) and `data/beaches.json` (OpenStreetMap beaches).

Claude Code or Codex can write each of these in a minute from the scripts either side.

## Sample data

`sample-ireland/ireland_venues.xlsx` has the Ireland results: every place found, the 321 AI-read candidates, the final scored list, the directory listings and the raw Google Maps rows.
