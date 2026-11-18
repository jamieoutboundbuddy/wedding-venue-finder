"""Deeper photo harvest for the shortlist: all gallery/wedding/rooms pages + up to 10 photographer posts. -> data/images_sl.json {key:[{url,src}]}"""
import json, re, concurrent.futures as cf, urllib.parse
src=open("05_classify.py").read().split("uni = json.load")[0]; ns={}; exec(src,ns); scrape,FC,post=ns["scrape"],ns["FC"],ns["post"]
sl=json.load(open("data/shortlist_keys.json")); LK=json.load(open("data/links.json"))
IMG=re.compile(r"https?://[^\s\"'()<>]+?\.(?:jpe?g|png|webp)(?:\?[^\s\"'()<>]*)?", re.I)
SKIP=re.compile(r"logo|icon|badge|award|sprite|avatar|favicon|placeholder|thumb_|-\d{2,3}x\d{2,3}\.|/wp-content/plugins|gravatar|emoji|svg|map|pixel", re.I)
def dom(u): return urllib.parse.urlparse(u).netloc.lower().replace("www.","")
def harvest(url):
    d=scrape(url); md=d.get("markdown","") or ""
    return [u for u in dict.fromkeys(IMG.findall(md)+[l for l in (d.get("links",[]) or []) if IMG.match(l)]) if not SKIP.search(u)]
def sitemap(url):
    try: return post("https://api.firecrawl.dev/v1/map",{"url":url,"limit":500},{"Authorization":f"Bearer {FC}"},60).get("links",[]) or []
    except Exception: return []
def work(kv):
    k,v=kv; d=dom(v["website"]); L=LK.get(k,{}); out=[]
    links=sitemap(v["website"])
    own=[l for l in links if dom(l)==d and re.search(r"gallery|galleries|photo|wedding|accommodation|bedroom|rooms|suite|stay|about|estate|garden|grounds|dining|restaurant|bar", l, re.I)]
    own=sorted(set(own), key=lambda l:(0 if re.search(r"gallery|photo",l,re.I) else 1 if "wedding" in l.lower() else 2, len(l)))[:12]
    for p in [v["website"]]+own:
        for u in harvest(p):
            if u not in [o["url"] for o in out]: out.append({"url":u,"src":"venue"})
    for p in L.get("posts",[])[:10]:
        for u in harvest(p["url"]):
            if u not in [o["url"] for o in out]: out.append({"url":u,"src":"post:"+p["domain"]})
    return k,out
res={}
with cf.ThreadPoolExecutor(8) as ex:
    for k,o in ex.map(work,sl.items()): res[k]=o
json.dump(res,open("data/images_sl.json","w"))
print({sl[k]["name"][:22]:(sum(1 for o in v if o["src"]=="venue"),sum(1 for o in v if o["src"]!="venue")) for k,v in res.items()})
