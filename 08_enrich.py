"""Enrich matrix venues: photographer images (Serper images), rooms count (search snippets + rooms page -> LLM), phone, email (contact page), nearest beach (OSM)."""
import json, re, math, csv, os, urllib.request, urllib.parse, concurrent.futures as cf
src = open("05_classify.py").read().split("uni = json.load")[0]; ns={}; exec(src, ns)
scrape, KEYS, post, TOK, PROXY = ns["scrape"], ns["KEYS"], ns["post"], ns["TOK"], ns["PROXY"]
SERP=KEYS["SERPER_API_KEY"]
uni=json.load(open("data/universe.json")); cls={json.loads(l)["key"]:json.loads(l) for l in open("data/classified.jsonl")}
names=[r["Venue"] for r in csv.DictReader(open("data/venue_matrix.csv"))]
targets=[r for r in cls.values() if r["name"] in names]
beaches=[(e.get("lat") or e["center"]["lat"], e.get("lon") or e["center"]["lon"], e.get("tags",{}).get("name")) for e in json.load(open("data/beaches.json"))["elements"]]
def hav(a,b,c,d):
    p=math.pi/180; x=math.sin((c-a)*p/2)**2+math.cos(a*p)*math.cos(c*p)*math.sin((d-b)*p/2)**2; return 12742*math.asin(math.sqrt(x))
def serper(path,q,num=10):
    try: return post(f"https://google.serper.dev/{path}", {"q":q,"gl":"ie","num":num}, {"X-API-KEY":SERP}, 30)
    except Exception: return {}
def llm_rooms(name, snippets):
    try:
        d=post(PROXY,{"token":TOK,"key_name":"OPENAI_API_KEY","task_summary":"extract bedroom count/phone/email for wedding venue search","path":"/v1/chat/completions",
          "payload":{"model":"gpt-5.6-sol","response_format":{"type":"json_object"},"messages":[{"role":"system","content":"From the text about a hotel/venue return JSON {bedrooms:int|null, phone:string|null, email:string|null, rooms_note:string}. bedrooms = number of guest bedrooms on site. Only use what the text states."},{"role":"user","content":f"VENUE: {name}\n\n{snippets[:9000]}"}]}},{})
        return json.loads(d["choices"][0]["message"]["content"])
    except Exception as e: return {"error":str(e)[:100]}
def work(r):
    k=r["key"]; u=uni.get(k,{}); l=r["llm"]; out={"key":k}
    # beach
    if u.get("lat"):
        b=min(beaches,key=lambda x:hav(u["lat"],u["lng"],x[0],x[1])); out["beach_km"]=round(hav(u["lat"],u["lng"],b[0],b[1]),1); out["beach_name"]=b[2]
    # images
    imgs=[]
    for q in (f'{r["name"]} wedding', f'{r["name"]} wedding photographer'):
        for i in serper("images",q,10).get("images",[]) or []:
            if i.get("imageUrl") and (i.get("imageWidth") or 0)>=500 and i["imageUrl"] not in imgs: imgs.append(i["imageUrl"])
    out["images"]=imgs[:14]
    # phone/email/rooms
    phone=u.get("phone"); email=l.get("enquiry_email"); rooms=l.get("bedrooms_onsite")
    text=""
    if not rooms or not email or not phone:
        w=serper("search",f'{r["name"]} hotel number of bedrooms',8)
        text += "\n".join(f'{o.get("title")}: {o.get("snippet")}' for o in w.get("organic",[]))
        kg=w.get("knowledgeGraph",{}) or {}; phone = phone or kg.get("phone")
        home=scrape(r["website"]); links=home.get("links",[]) or []
        dom=urllib.parse.urlparse(r["website"]).netloc.replace("www.","")
        pages=[x for x in links if urllib.parse.urlparse(x).netloc.replace("www.","")==dom and re.search(r"contact|accommodation|rooms|bedrooms|stay",x,re.I)]
        pages=sorted(set(pages),key=lambda x:(0 if "contact" in x.lower() else 1,len(x)))[:2]
        for p in pages: text+="\n\n--- "+p+" ---\n"+(scrape(p).get("markdown","") or "")[:5000]
        text+="\n\n--- home ---\n"+(home.get("markdown","") or "")[:4000]
        found=re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+",text); found=[e for e in found if not re.search(r"png|jpg|example|sentry|wixpress",e)]
        email = email or (found[0] if found else None)
        x=llm_rooms(r["name"],text)
        rooms = rooms or x.get("bedrooms"); phone = phone or x.get("phone"); email = email or x.get("email"); out["rooms_note"]=x.get("rooms_note")
    out.update({"rooms":rooms,"phone":phone,"email":email}); return out
res={}
with cf.ThreadPoolExecutor(16) as ex:
    for o in ex.map(work,targets): res[o["key"]]=o
json.dump(res,open("data/enrich.json","w"),indent=1)
print("enriched",len(res),"rooms",sum(1 for o in res.values() if o.get("rooms")),"phone",sum(1 for o in res.values() if o.get("phone")),"email",sum(1 for o in res.values() if o.get("email")),"imgs",sum(len(o["images"]) for o in res.values()))
