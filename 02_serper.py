"""Stage 1B: Serper sweep. ~15 far counties x query templates. Writes data/serper_raw.jsonl (every organic hit)."""
import json, os, time, concurrent.futures as cf, urllib.request
KEY = [l.split("=",1)[1].strip() for l in open(".env") if l.startswith("SERPER_API_KEY=")][0]
COUNTIES = ["Kerry","Cork","West Cork","Clare","Limerick","Galway","Connemara","Mayo","Sligo","Leitrim","Donegal","Waterford",
            "Fermanagh","Derry","Antrim","Tyrone","Down"]
TEMPLATES = ["wedding venue {c}", "wedding venues {c} Ireland", "{c} wedding hotel packages", "country house wedding {c}",
             "exclusive use wedding venue {c}", "castle wedding {c}", "coastal wedding venue {c}", "best wedding venues {c}"]
GENERIC = ["best wedding venues Ireland", "Ireland wedding venues by the sea", "exclusive use wedding venues Ireland",
           "country house wedding venues Ireland", "wedding venues west of Ireland", "wedding venues Wild Atlantic Way",
           "Ireland's Blue Book wedding venues", "boutique hotel wedding Ireland", "wedding venues with accommodation Ireland",
           "all inclusive wedding packages Ireland", "wedding venues Ireland 100 guests", "destination wedding Ireland venues"]
queries = [t.format(c=c) for c in COUNTIES for t in TEMPLATES] + GENERIC
def hit(q):
    for page in (1,2):
        body = json.dumps({"q": q, "gl": "ie", "hl": "en", "num": 20, "page": page}).encode()
        req = urllib.request.Request("https://google.serper.dev/search", body, {"X-API-KEY": KEY, "Content-Type": "application/json"})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as e:
            yield {"q": q, "page": page, "error": str(e)}; continue
        for o in d.get("organic", []):
            yield {"q": q, "page": page, "title": o.get("title"), "link": o.get("link"), "snippet": o.get("snippet"), "pos": o.get("position")}
        for p in d.get("places", []) or []:
            yield {"q": q, "page": page, "place": p}
os.makedirs("data", exist_ok=True)
n=0
with open("data/serper_raw.jsonl","w") as f, cf.ThreadPoolExecutor(10) as ex:
    for rows in ex.map(lambda q: list(hit(q)), queries):
        for r in rows: f.write(json.dumps(r)+"\n"); n+=1
print("queries", len(queries), "rows", n)
