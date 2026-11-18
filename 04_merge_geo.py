"""Stage 2: merge Google Maps + hitched + serper, geocode gaps (Nominatim), drive time from Dublin (OSRM). -> data/universe.json"""
import json, re, glob, time, urllib.request, urllib.parse, os
DUB = (-6.2603, 53.3498)
def norm(s): return re.sub(r"[^a-z0-9]+"," ",(s or "").lower()).replace(" the "," ").strip()
def dom(u):
    if not u: return None
    d = urllib.parse.urlparse(u if u.startswith("http") else "http://"+u).netloc.lower().replace("www.","")
    return d or None
venues = {}
# --- Google Maps
for f in glob.glob("data/gmaps_*.json"):
    for p in json.load(open(f)):
        key = p.get("placeId") or p["title"]
        loc = p.get("location") or {}
        venues[key] = {"name": p["title"], "category": p.get("categoryName"), "cats": p.get("categories"),
                       "address": p.get("address"), "city": p.get("city"), "county": p.get("state"), "postcode": p.get("postalCode"),
                       "lat": loc.get("lat"), "lng": loc.get("lng"), "website": p.get("website"), "domain": dom(p.get("website")),
                       "phone": p.get("phone"), "rating": p.get("totalScore"), "reviews": p.get("reviewsCount"),
                       "gmaps_url": p.get("url"), "closed": p.get("permanentlyClosed") or p.get("temporarilyClosed"),
                       "hotel_stars": p.get("hotelStars"), "src": ["gmaps"]}
by_name = {norm(v["name"]): k for k,v in venues.items()}
by_dom = {v["domain"]: k for k,v in venues.items() if v["domain"]}
# --- hitched
for l in open("data/directory_venues.jsonl"):
    r = json.loads(l); n = norm(r["name"])
    k = by_name.get(n) or next((k for nn,k in by_name.items() if n and (n in nn or nn in n) and len(n)>8), None)
    if k: venues[k]["src"].append("hitched"); venues[k]["hitched_url"]=r["url"]; venues[k]["hitched_guests"]=r.get("guests")
    else:
        venues["hitched:"+r["url"]] = {"name": r["name"], "address": r["location"], "county": r["county"].title(), "hitched_url": r["url"],
                                       "hitched_guests": r.get("guests"), "src": ["hitched"]}
        by_name[n] = "hitched:"+r["url"]
# --- serper venue domains
for r in json.load(open("data/serper_domains.json")):
    k = by_dom.get(r["domain"])
    if k: venues[k]["src"].append("serper"); continue
    t = re.split(r"\s*[|\-–:]\s*", r["title"] or "")[0].strip()
    n = norm(t)
    k = by_name.get(n) if n else None
    if k: venues[k]["src"].append("serper"); venues[k].setdefault("website", r["url"]); venues[k].setdefault("domain", r["domain"])
    else: venues["serper:"+r["domain"]] = {"name": t or r["domain"], "website": r["url"], "domain": r["domain"], "serper_hits": r["hits"], "src": ["serper"]}
print("merged venues", len(venues), "with coords", sum(1 for v in venues.values() if v.get("lat")))
# --- geocode gaps via Nominatim (1 req/s), only for hitched (have address); serper-only get geocoded by name+Ireland
cache_f = "data/geocode_cache.json"; cache = json.load(open(cache_f)) if os.path.exists(cache_f) else {}
def geocode(q):
    if q in cache: return cache[q]
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": q, "format": "json", "limit": 1, "countrycodes": "ie,gb"})
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "wedding-venue-search/1.0 (put-your-email-here)"}), timeout=20))
        cache[q] = (float(d[0]["lat"]), float(d[0]["lon"])) if d else None
    except Exception: cache[q] = None
    time.sleep(1.05); json.dump(cache, open(cache_f,"w")); return cache[q]
for k,v in []:  # geocoding skipped for speed
    if v.get("lat"): continue
    q = f'{v["name"]}, {v.get("address") or ""}, {v.get("county") or ""}, Ireland'.replace(", ,", ",")
    g = geocode(q) or (geocode(f'{v["name"]}, Ireland') if v.get("src")==["serper"] else None)
    if g: v["lat"], v["lng"] = g; v["geocoded"] = True
print("after geocode with coords", sum(1 for v in venues.values() if v.get("lat")))
# --- OSRM drive time from Dublin, batches of 90
items = [(k,v) for k,v in venues.items() if v.get("lat")]
for i in range(0, len(items), 90):
    chunk = items[i:i+90]
    coords = ";".join([f"{DUB[0]},{DUB[1]}"] + [f'{v["lng"]},{v["lat"]}' for _,v in chunk])
    url = f"https://router.project-osrm.org/table/v1/driving/{coords}?sources=0&annotations=duration"
    for attempt in range(3):
        try:
            d = json.load(urllib.request.urlopen(url, timeout=60)); break
        except Exception as e: d = {"code": str(e)}; time.sleep(3)
    durs = d.get("durations", [[None]*(len(chunk)+1)])[0][1:] if d.get("code")=="Ok" else [None]*len(chunk)
    for (k,v), s in zip(chunk, durs): v["drive_h_from_dublin"] = round(s/3600, 2) if s else None
    time.sleep(1)
json.dump(venues, open("data/universe.json","w"), indent=1)
import collections
b = collections.Counter("3h+" if (v.get("drive_h_from_dublin") or 0) >= 3 else "2.5-3h" if (v.get("drive_h_from_dublin") or 0) >= 2.5 else "under 2.5h" if v.get("drive_h_from_dublin") else "no drive time" for v in venues.values())
print(b)
