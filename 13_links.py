"""Per venue: own gallery pages (Firecrawl map), Instagram/Facebook, Google Maps, hitched, photographer/blog posts (Serper). -> data/links.json"""
import json, re, csv, urllib.parse, concurrent.futures as cf
src=open("05_classify.py").read().split("uni = json.load")[0]; ns={}; exec(src,ns); scrape,KEYS,post,FC=ns["scrape"],ns["KEYS"],ns["post"],ns["FC"]
SERP=KEYS["SERPER_API_KEY"]
uni=json.load(open("data/universe.json")); cls={json.loads(l)["key"]:json.loads(l) for l in open("data/classified.jsonl")}
names={r["Venue"] for r in csv.DictReader(open("data/venue_matrix.csv"))}
targets=[r for r in cls.values() if r["name"] in names]
DIRS=re.compile(r"hitched|weddingsonline|weddingdates|bridebook|tripadvisor|booking\.com|expedia|hotels\.com|trivago|yelp|google|wikipedia|facebook|instagram|youtube|pinterest|tiktok|linkedin|x\.com|twitter|reddit|onefabday|weddingjournal|confetti|mrs2be|irelands-blue-book|discoverireland|ireland\.com|failteireland|independent|irishtimes|rte\.ie|thejournal|guidesforbrides|easyweddings|forbetterforworse|theknot|zola|weddingpages|littlewed|fivestar|celticcastles|irishhistorichouses|blue-book|whatsonwhere|eventbrite|apple\.com|amazon", re.I)
def dom(u): 
    try: return urllib.parse.urlparse(u).netloc.lower().replace("www.","")
    except Exception: return ""
def serper(q, page=1):
    try: return post("https://google.serper.dev/search",{"q":q,"gl":"ie","num":10,"page":page},{"X-API-KEY":SERP},30)
    except Exception: return {}
def sitemap(url):
    try: d=post("https://api.firecrawl.dev/v1/map",{"url":url,"limit":300},{"Authorization":f"Bearer {FC}"},60); return d.get("links",[]) or []
    except Exception: return []
def work(r):
    k=r["key"]; u=uni.get(k,{}); site=r["website"]; d=dom(site); out={"key":k}
    # own pages
    links=sitemap(site)
    def pick(pat, n): return sorted({l for l in links if dom(l)==d and re.search(pat,l,re.I)}, key=len)[:n]
    out["gallery_pages"]=pick(r"gallery|galleries|photos|photo-gallery|image", 4)
    out["wedding_pages"]=pick(r"wedding", 4)
    out["rooms_pages"]=pick(r"accommodation|bedrooms|rooms|stay|suites", 3)
    # socials from homepage links
    home=scrape(site); hl=home.get("links",[]) or []
    ig=[l for l in hl if "instagram.com/" in l and not re.search(r"/p/|/reel|/explore|/share",l)]
    fb=[l for l in hl if "facebook.com/" in l and not re.search(r"/sharer|/share|/photo|/posts|/dialog",l)]
    if not ig:
        s=serper(f'"{r["name"]}" instagram')
        ig=[o["link"] for o in s.get("organic",[]) if "instagram.com/" in o["link"] and not re.search(r"/p/|/reel|/explore",o["link"])]
    out["instagram"]=ig[0].split("?")[0] if ig else None; out["facebook"]=fb[0].split("?")[0] if fb else None
    out["google_maps"]=u.get("gmaps_url"); out["hitched"]=u.get("hitched_url")
    # photographer / blog posts
    posts=[]; seen=set()
    for q,pg in ((f'"{r["name"]}" wedding',1),(f'"{r["name"]}" wedding',2),(f'"{r["name"]}" wedding photographer',1),(f'"{r["name"]}" real wedding',1)):
        for o in serper(q,pg).get("organic",[]):
            l=o["link"]; dd=dom(l)
            if not dd or dd==d or DIRS.search(dd) or l in seen: continue
            t=(o.get("title") or "")+" "+(o.get("snippet") or "")
            if not re.search(r"wedding", t, re.I): continue
            seen.add(l); posts.append({"title":(o.get("title") or "").strip()[:90],"url":l,"domain":dd})
        if len(posts)>=10: break
    out["posts"]=posts[:10]; return out
res={}
with cf.ThreadPoolExecutor(16) as ex:
    for o in ex.map(work,targets): res[o["key"]]=o
json.dump(res,open("data/links.json","w"),indent=1)
print("venues",len(res),"with gallery",sum(1 for o in res.values() if o["gallery_pages"]),"instagram",sum(1 for o in res.values() if o["instagram"]),"facebook",sum(1 for o in res.values() if o["facebook"]),"posts total",sum(len(o["posts"]) for o in res.values()),"venues with 0 posts",sum(1 for o in res.values() if not o["posts"]))
