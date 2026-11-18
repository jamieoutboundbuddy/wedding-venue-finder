"""More photos per venue: 4 Serper image queries each, keep width>=400, dedupe. Writes data/images.json {key:[urls]}"""
import json, csv, os, concurrent.futures as cf, urllib.request
KEYS=dict(l.strip().split("=",1) for l in open(".env") if "=" in l and not l.startswith("#"))
SERP=KEYS["SERPER_API_KEY"]
cls={json.loads(l)["key"]:json.loads(l) for l in open("data/classified.jsonl")}
names={r["Venue"] for r in csv.DictReader(open("data/venue_matrix.csv"))}
targets=[r for r in cls.values() if r["name"] in names]
def q(query):
    try:
        req=urllib.request.Request("https://google.serper.dev/images", json.dumps({"q":query,"gl":"ie","num":20}).encode(), {"X-API-KEY":SERP,"Content-Type":"application/json"})
        return json.load(urllib.request.urlopen(req,timeout=30)).get("images",[]) or []
    except Exception: return []
def work(r):
    n=r["name"]; out=[]
    for query in (f"{n} wedding", f"{n} wedding photography", f"{n} hotel", f"{n} {r.get('county') or ''} exterior grounds"):
        for i in q(query):
            u=i.get("imageUrl")
            if u and (i.get("imageWidth") or 0)>=400 and u not in out and not u.lower().endswith(".svg"): out.append(u)
    return r["key"], out
res={}
with cf.ThreadPoolExecutor(12) as ex:
    for k,v in ex.map(work,targets): res[k]=v
json.dump(res,open("data/images.json","w"))
import statistics; print("venues",len(res),"median imgs",statistics.median(len(v) for v in res.values()),"min",min(len(v) for v in res.values()))
