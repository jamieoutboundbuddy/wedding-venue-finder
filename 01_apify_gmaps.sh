#!/bin/bash
# Stage 1A: Google Maps universe of Irish wedding venues (compass/crawler-google-places, ~$0.002-0.004/place)
source .env
run() {
  local loc="$1" cc="$2" tag="$3"
  curl -s -X POST "https://api.apify.com/v2/acts/compass~crawler-google-places/runs?token=$APIFY_TOKEN" \
    -H 'Content-Type: application/json' -d "{
      \"searchStringsArray\": [\"wedding venue\", \"wedding hotel\", \"country house hotel\", \"castle hotel wedding\", \"exclusive hire wedding venue\"],
      \"locationQuery\": \"$loc\", \"countryCode\": \"$cc\", \"language\": \"en\",
      \"maxCrawledPlacesPerSearch\": 400, \"scrapePlaceDetailPage\": false, \"maxReviews\": 0, \"maxImages\": 0
    }" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print('$tag', d['id'], d['status'])" | tee -a data/apify_runs.txt
}
run "Ireland" "ie" "IE"
run "Northern Ireland, United Kingdom" "gb" "NI"
