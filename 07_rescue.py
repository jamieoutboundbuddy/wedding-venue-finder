"""Rescue pass: venues classified 'no weddings' or unreadable where no wedding page was found. Find the wedding page via Serper site: search, rescrape, reclassify."""
import json, re, os, urllib.request, urllib.parse, concurrent.futures as cf, importlib.util
spec = importlib.util.spec_from_file_location("c", "05_classify.py")
src = open("05_classify.py").read().split("uni = json.load")[0]   # reuse helpers/prompt without running main
ns = {}; exec(src, ns)
scrape, llm, KEYS = ns["scrape"], ns["llm"], ns["KEYS"]
SERP = KEYS["SERPER_API_KEY"]
rows=[json.loads(l) for l in open("data/classified.jsonl")]
def dom(u): return urllib.parse.urlparse(u).netloc.replace("www.","")
targets=[r for r in rows if not r.get("wedding_page") and ((r["llm"].get("is_wedding_venue") is False) or r["llm"].get("error") or r["llm"].get("onsite_catering") is False)]
print("rescue targets", len(targets), flush=True)
def find_wedding_page(r):
    d = dom(r["website"])
    for q in (f"site:{d} weddings", f"{r['name']} weddings"):
        body=json.dumps({"q":q,"gl":"ie","num":10}).encode()
        try:
            res=json.load(urllib.request.urlopen(urllib.request.Request("https://google.serper.dev/search", body, {"X-API-KEY":SERP,"Content-Type":"application/json"}), timeout=30))
        except Exception: continue
        for o in res.get("organic",[]):
            if dom(o["link"])==d and re.search(r"wedding|celebrat", o["link"]+o.get("title",""), re.I): return o["link"]
    return None
def work(r):
    wp = find_wedding_page(r)
    if not wp: r["rescue"]="no wedding page found"; return r
    wed = scrape(wp); wmd = wed.get("markdown","") or ""
    if len(wmd) < 200: r["rescue"]="wedding page unreadable"; r["wedding_page"]=wp; return r
    imgs = re.findall(r"!\[[^\]]*\]\((https?://[^)\s]+)\)", wmd)[:25]
    text = f"VENUE: {r['name']}\nCOUNTY: {r.get('county')}\nSITE: {r['website']}\nWEDDING PAGE: {wp}\nIMAGES FOUND: {imgs}\n\n--- WEDDING PAGE ---\n{wmd[:12000]}"
    out, usage = llm(text)
    r["llm"]=out; r["wedding_page"]=wp; r["rescue"]="reclassified"; r["tokens"]=usage.get("total_tokens"); return r
done={}
with cf.ThreadPoolExecutor(20) as ex:
    for r in ex.map(work, targets): done[r["key"]]=r
import collections; print(collections.Counter(r.get("rescue") for r in done.values()))
with open("data/classified.jsonl","w") as f:
    for r in rows: f.write(json.dumps(done.get(r["key"], r))+"\n")
print("rewritten", len(rows))
