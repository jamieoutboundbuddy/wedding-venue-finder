"""Bedroom verification for the shortlist: venue accommodation pages + TripAdvisor/Booking/Wikipedia snippets -> reconcile with LLM. -> data/rooms_verified.json"""
import json, re, concurrent.futures as cf, urllib.parse
src=open("05_classify.py").read().split("uni = json.load")[0]; ns={}; exec(src,ns); scrape,KEYS,post,TOK,PROXY,FC=ns["scrape"],ns["KEYS"],ns["post"],ns["TOK"],ns["PROXY"],ns["FC"]
SERP=KEYS["SERPER_API_KEY"]; sl=json.load(open("data/shortlist_keys.json")); LK=json.load(open("data/links.json"))
def dom(u): return urllib.parse.urlparse(u).netloc.lower().replace("www.","")
def serp(q):
    try: return post("https://google.serper.dev/search",{"q":q,"gl":"ie","num":10},{"X-API-KEY":SERP},30)
    except Exception: return {}
def work(kv):
    k,v=kv; n=v["name"]; d=dom(v["website"]); ev=[]
    for p in (LK.get(k,{}).get("rooms_pages") or [])[:2]:
        md=scrape(p).get("markdown","") or ""
        for m in re.finditer(r"[^.\n]{0,120}\b(\d{1,3})\s*(?:guest\s*)?(?:bed)?rooms?\b[^.\n]{0,120}", md, re.I): ev.append(("venue site: "+p, m.group(0).strip()))
    for q in (f"{n} number of rooms", f"site:tripadvisor.ie {n}", f"site:booking.com {n}", f"{n} hotel bedrooms", f"{n} wikipedia"):
        r=serp(q); kg=r.get("knowledgeGraph") or {}
        if kg: ev.append(("google knowledge panel", json.dumps({x:kg.get(x) for x in ("title","type","description","attributes") if kg.get(x)})[:400]))
        for o in r.get("organic",[])[:6]:
            t=(o.get("title") or "")+" — "+(o.get("snippet") or "")
            if re.search(r"\b\d{1,3}\s*(bed)?rooms?\b|\bsuites?\b|\bbedrooms\b", t, re.I): ev.append((dom(o["link"]), t[:300]))
    evtext="\n".join(f"- [{s}] {t}" for s,t in ev[:40])
    try:
        dd=post(PROXY,{"token":TOK,"key_name":"OPENAI_API_KEY","task_summary":"verify bedroom count for shortlisted wedding venues","path":"/v1/chat/completions","payload":{"model":"gpt-5.6-sol","response_format":{"type":"json_object"},"messages":[{"role":"system","content":"You reconcile evidence about how many guest bedrooms a hotel/venue has ON SITE. Return JSON {hotel_rooms:int|null, extra_accommodation:string|null (e.g. '24 lodges, 38 villas' or 'self-catering cottages'), confidence:'high'|'medium'|'low', best_source:string, note:string}. hotel_rooms = bedrooms in the main hotel/house bookable per night, not beds, not villas. Prefer the venue's own site and TripAdvisor 'Number of rooms'. If sources disagree, pick the most recent official figure and say so. Never guess."},{"role":"user","content":f"VENUE: {n} ({v.get('county')})\nEVIDENCE:\n{evtext or '(none found)'}"}]}},{})
        out=json.loads(dd["choices"][0]["message"]["content"])
    except Exception as e: out={"error":str(e)[:120]}
    out["evidence_count"]=len(ev); return k,out
res={}
with cf.ThreadPoolExecutor(8) as ex:
    for k,o in ex.map(work,sl.items()): res[k]=o
json.dump(res,open("data/rooms_verified.json","w"),indent=1)
for k,o in res.items(): print(f'{sl[k]["name"][:34]:34} rooms={o.get("hotel_rooms")!s:>5} conf={o.get("confidence")!s:7} extra={str(o.get("extra_accommodation") or "")[:40]:40} | {str(o.get("best_source") or "")[:30]}')
