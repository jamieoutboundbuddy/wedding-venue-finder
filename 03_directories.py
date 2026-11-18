"""Stage 1C: hitched.ie + weddingsonline.ie county listings via Firecrawl (1 credit/page). Writes data/directory_venues.jsonl"""
import json, os, re, urllib.request, concurrent.futures as cf
KEY = [l.split("=",1)[1].strip() for l in open(".env") if l.startswith("FIRECRAWL_API_KEY=")][0]
COUNTIES = ["kerry","cork","clare","limerick","galway","mayo","sligo","leitrim","donegal","waterford","fermanagh","derry","antrim","tyrone","down"]
def scrape(url):
    body = json.dumps({"url": url, "formats": ["markdown","links"], "onlyMainContent": True}).encode()
    req = urllib.request.Request("https://api.firecrawl.dev/v1/scrape", body, {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=90))
        return d.get("data", {}) if d.get("success") else {}
    except Exception as e:
        return {"error": str(e)}
def hitched(county):
    out=[]; 
    for page in range(1,6):
        url = f"https://www.hitched.ie/wedding-venues/{county}.htm" + (f"?page={page}" if page>1 else "")
        d = scrape(url); md = d.get("markdown","")
        found = re.findall(r"## \[([^\]]+)\]\((https://www\.hitched\.ie/wedding-venues/[^)]+\.htm)\)\s*\n\s*\n?([^\n]*)", md)
        if not found: break
        for name, link, loc in found:
            m = re.search(re.escape(link)+r".*?(\d{2,4})\s*\n\s*\n?\s*Guests", md, re.S)
            out.append({"src":"hitched","county":county,"name":name.strip(),"url":link,"location":loc.strip(),"guests":m.group(1) if m else None})
        if "Next" not in md and page>=1 and len(found)<30: break
    return out
def weddingsonline(county):
    out=[]
    for page in range(1,8):
        url = f"https://www.weddingsonline.ie/venues/{county}" + (f"?page={page}" if page>1 else "")
        d = scrape(url); links = d.get("links",[]); md = d.get("markdown","")
        vl = sorted({l for l in links if re.match(r"https://www\.weddingsonline\.ie/venue/[^/?#]+/?$", l)})
        if not vl: break
        for l in vl:
            slug = l.rstrip("/").split("/")[-1]
            out.append({"src":"weddingsonline","county":county,"name":slug.replace("-"," ").title(),"url":l})
        if f"page={page+1}" not in " ".join(links): break
    return out
rows=[]
with cf.ThreadPoolExecutor(6) as ex:
    for r in ex.map(lambda c:(hitched(c)+weddingsonline(c)), COUNTIES): rows+=r
seen=set(); uniq=[]
for r in rows:
    if r["url"] in seen: continue
    seen.add(r["url"]); uniq.append(r)
with open("data/directory_venues.jsonl","w") as f:
    for r in uniq: f.write(json.dumps(r)+"\n")
from collections import Counter
print(len(uniq), Counter((r["src"],r["county"]) for r in uniq))
