"""Extra email pass for venues with no email: wedding/contact/enquiry pages + Serper snippets. Updates data/enrich.json"""
import json, re, csv, urllib.parse, urllib.request, concurrent.futures as cf
src=open("05_classify.py").read().split("uni = json.load")[0]; ns={}; exec(src,ns); scrape,KEYS,post=ns["scrape"],ns["KEYS"],ns["post"]
SERP=KEYS["SERPER_API_KEY"]
cls={json.loads(l)["key"]:json.loads(l) for l in open("data/classified.jsonl")}; en=json.load(open("data/enrich.json"))
names={r["Venue"] for r in csv.DictReader(open("data/venue_matrix.csv"))}
EMAIL=re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
BAD=re.compile(r"png|jpg|jpeg|gif|webp|example|sentry|wixpress|\.js$|godaddy|squarespace|shopify|noreply|no-reply|@\d",re.I)
targets=[r for r in cls.values() if r["name"] in names and not (en.get(r["key"],{}).get("email"))]
print("venues without email", len(targets), flush=True)
def dom(u): return urllib.parse.urlparse(u).netloc.lower().replace("www.","")
def work(r):
    d=dom(r["website"]); found=[]
    def grab(text):
        for e in EMAIL.findall(text or ""):
            e=e.strip(".").lower()
            if not BAD.search(e) and e not in found: found.append(e)
    pages=[p for p in [r.get("wedding_page"), r["website"].rstrip("/")+"/contact", r["website"].rstrip("/")+"/contact-us", r["website"].rstrip("/")+"/weddings/enquiry"] if p]
    home=scrape(r["website"]); grab(home.get("markdown","")); grab(" ".join(home.get("links",[]) or []))
    for l in (home.get("links",[]) or []):
        if dom(l)==d and re.search(r"contact|enquir|wedding",l,re.I) and l not in pages: pages.append(l)
    for p in pages[:5]:
        if found: break
        s=scrape(p); grab(s.get("markdown","")); grab(" ".join(s.get("links",[]) or []))
    if not found:
        for q in (f'"{d}" weddings email', f'"@{d}"'):
            try: res=post("https://google.serper.dev/search",{"q":q,"gl":"ie","num":10},{"X-API-KEY":SERP},30)
            except Exception: continue
            for o in res.get("organic",[]): grab((o.get("snippet") or "")+" "+(o.get("title") or ""))
            if found: break
    same=[e for e in found if e.endswith("@"+d) or d.split(".")[0] in e]
    pref=sorted(same or found, key=lambda e:(0 if re.search(r"wedding|event|celebrat",e) else 1 if e.startswith(("info","reception","reservations","enquir","hello","sales")) else 2))
    return r["key"], (pref[0] if pref else None), found[:5]
n=0
with cf.ThreadPoolExecutor(16) as ex:
    for k,e,allf in ex.map(work,targets):
        if e: en.setdefault(k,{})["email"]=e; en[k]["email_candidates"]=allf; n+=1
ov=json.load(open("data/overrides.json"))
for k,r in cls.items():
    if r["name"] in ov: en.setdefault(k,{}).update(ov[r["name"]])
json.dump(en,open("data/enrich.json","w"),indent=1)
print("emails found", n, "of", len(targets), "| total with email now", sum(1 for k,r in cls.items() if r["name"] in names and en.get(k,{}).get("email")))
