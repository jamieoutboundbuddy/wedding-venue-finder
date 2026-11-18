"""More photos: scrape each venue's gallery + wedding pages and its top photographer posts, harvest image URLs. -> data/images2.json"""
import json, re, csv, urllib.parse, concurrent.futures as cf
src=open("05_classify.py").read().split("uni = json.load")[0]; ns={}; exec(src,ns); scrape=ns["scrape"]
cls={json.loads(l)["key"]:json.loads(l) for l in open("data/classified.jsonl")}; LK=json.load(open("data/links.json"))
names={r["Venue"] for r in csv.DictReader(open("data/venue_matrix.csv"))}
targets=[r for r in cls.values() if r["name"] in names]
IMG=re.compile(r"https?://[^\s\"'()<>]+?\.(?:jpe?g|png|webp)(?:\?[^\s\"'()<>]*)?", re.I)
SKIP=re.compile(r"logo|icon|badge|award|sprite|avatar|favicon|banner-ad|placeholder|thumb_|-\d{2,3}x\d{2,3}\.|w=\d{2,3}\b|/wp-content/plugins|gravatar|emoji|svg", re.I)
def harvest(url):
    d=scrape(url); md=d.get("markdown","") or ""; out=[]
    for u in IMG.findall(md)+[l for l in (d.get("links",[]) or []) if IMG.match(l)]:
        if not SKIP.search(u) and u not in out: out.append(u)
    return out
def work(r):
    L=LK.get(r["key"],{}); pages=(L.get("gallery_pages",[])[:3]+L.get("wedding_pages",[])[:2]+[p["url"] for p in L.get("posts",[])[:4]])
    seen=[]; 
    for p in dict.fromkeys(pages):
        for u in harvest(p):
            if u not in seen: seen.append(u)
        if len(seen)>=60: break
    return r["key"], seen[:60]
res={}
with cf.ThreadPoolExecutor(16) as ex:
    for k,v in ex.map(work,targets): res[k]=v
json.dump(res,open("data/images2.json","w"))
import statistics; print("venues",len(res),"median new urls",statistics.median(len(v) for v in res.values()),"zero",sum(1 for v in res.values() if not v))
