"""Stage 3: Firecrawl each candidate's site (home + wedding page), classify with GPT-5.6 Sol via the OpenAI API.
Input data/universe.json  -> appends to data/classified.jsonl (resumable). Usage: python3 05_classify.py [min_drive_h] [limit]"""
import json, os, re, sys, time, urllib.request, urllib.parse, concurrent.futures as cf
KEYS = dict(l.strip().split("=",1) for l in open(".env") if "=" in l and not l.startswith("#"))
FC = KEYS["FIRECRAWL_API_KEY"]
TOK = None
BRIEF = open("brief.txt").read().strip()
PROXY = "https://api.openai.com/v1/chat/completions"
MIN_H = float(sys.argv[1]) if len(sys.argv)>1 else 2.75
LIMIT = int(sys.argv[2]) if len(sys.argv)>2 else 10**6

def post(url, body, headers, timeout=120):
    if isinstance(body, dict) and "payload" in body and "key_name" in body:   # an OpenAI call
        body = dict(body["payload"]); body["model"] = KEYS.get("OPENAI_MODEL") or body["model"]
        headers = {"Authorization": f"Bearer {KEYS['OPENAI_API_KEY']}", **headers}
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type":"application/json", **headers})
    return json.load(urllib.request.urlopen(req, timeout=timeout))
def scrape(url):
    try:
        d = post("https://api.firecrawl.dev/v1/scrape", {"url": url, "formats": ["markdown","links"], "onlyMainContent": True, "timeout": 40000}, {"Authorization": f"Bearer {FC}"})
        return d.get("data") or {}
    except Exception as e:
        return {"error": str(e)[:200]}
def llm(prompt):
    for attempt in range(3):
        try:
            d = post(PROXY, {"token": TOK, "key_name": "OPENAI_API_KEY", "task_summary": "classify wedding venue websites",
                             "path": "/v1/chat/completions", "payload": {"model": "gpt-5.6-sol", "response_format": {"type": "json_object"},
                             "messages": [{"role":"system","content": SYS}, {"role":"user","content": prompt}]}}, {})
            return json.loads(d["choices"][0]["message"]["content"]), d.get("usage",{})
        except Exception as e:
            err = str(e); time.sleep(2*(attempt+1))
    return {"error": err}, {}
SYS = """You classify wedding venue websites for a couple. Their brief:
""" + BRIEF + """
Return strict JSON with these keys:
is_wedding_venue (bool), venue_type (one of: hotel, country_house, castle, estate_exclusive, restaurant, barn, other, not_a_venue),
onsite_catering (bool|null), onsite_accommodation (bool|null), bedrooms_onsite (int|null), exclusive_use_option (bool|null),
all_in_package (bool|null: do they sell an all-inclusive wedding package covering food+drink+venue),
price_per_head_eur (number|null: lowest published package price per head; convert GBP at 1.17), price_note (string),
min_numbers (int|null), max_capacity (int|null), civil_ceremony_onsite (bool|null), coastal_or_sea_view (bool|null),
setting (short phrase: e.g. 'clifftop coastal', 'lakeside estate', 'town hotel'), style_words (3-6 adjectives for the look),
wedding_page_url (string|null), enquiry_email (string|null), hero_images (up to 4 absolute image URLs that best show the venue),
fit_score (0-100 for this couple: coastal/scenic, all-in, 100 guests, onsite rooms, not dated, not a huge conference hotel),
fit_reason (one sentence), red_flags (list of short strings). Use null when the site does not say. Never invent prices."""

uni = json.load(open("data/shortlist_input.json"))
done = set()
if os.path.exists("data/classified.jsonl"):
    for l in open("data/classified.jsonl"): done.add(json.loads(l)["key"])
todo = [(k,v) for k,v in uni.items() if k not in done and v.get("website") and (v.get("drive_h_from_dublin") or v.get("drive_h_fallback") or 0) >= MIN_H][:LIMIT]
print("to classify", len(todo), "already done", len(done), flush=True)

def work(kv):
    k, v = kv; site = v["website"]
    home = scrape(site); md = home.get("markdown","") or ""; links = home.get("links",[]) or []
    wl = [l for l in links if re.search(r"wedding|celebrat|marry", l, re.I) and urllib.parse.urlparse(l).netloc.replace("www.","") == (v.get("domain") or "")]
    wl = sorted(set(wl), key=lambda l: (0 if re.search(r"/wedding", l, re.I) else 1, len(l)))
    wed = scrape(wl[0]) if wl else {}
    wmd = wed.get("markdown","") or ""
    imgs = re.findall(r"!\[[^\]]*\]\((https?://[^)\s]+)\)", md + "\n" + wmd)[:25]
    text = f"VENUE: {v['name']}\nCOUNTY: {v.get('county')}\nGOOGLE CATEGORY: {v.get('category')}\nSITE: {site}\nWEDDING PAGE: {wl[0] if wl else None}\nIMAGES FOUND: {imgs}\n\n--- HOMEPAGE ---\n{md[:6000]}\n\n--- WEDDING PAGE ---\n{wmd[:9000]}"
    if len(md) < 200 and len(wmd) < 200:
        out = {"error": "no site text", "scrape_error": home.get("error")}; usage = {}
    else:
        out, usage = llm(text)
    return {"key": k, "name": v["name"], "county": v.get("county"), "website": site, "drive_h": v.get("drive_h_from_dublin") or v.get("drive_h_fallback"),
            "wedding_page": wl[0] if wl else None, "src": v.get("src"), "rating": v.get("rating"), "reviews": v.get("reviews"),
            "llm": out, "tokens": usage.get("total_tokens")}
n=0; tok=0
with open("data/classified.jsonl","a") as f, cf.ThreadPoolExecutor(20) as ex:
    for r in ex.map(work, todo):
        f.write(json.dumps(r)+"\n"); f.flush(); n+=1; tok += r.get("tokens") or 0
        if n % 25 == 0: print(n, "done, tokens", tok, flush=True)
print("finished", n, "tokens", tok)
