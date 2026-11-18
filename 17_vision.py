"""Photo verification for the shortlist: gather (existing local + images_sl + Google Maps photos), download, dedupe, vision-check with anchors. -> data/photos_verified.json"""
import json, os, re, io, base64, glob, urllib.request, html, concurrent.futures as cf
from PIL import Image
src=open("05_classify.py").read().split("uni = json.load")[0]; ns={}; exec(src,ns); post,TOK,PROXY=ns["post"],ns["TOK"],ns["PROXY"]
sl=json.load(open("data/shortlist_keys.json"))
def slug(n): return re.sub(r"[^a-z0-9]+","-",n.lower()).strip("-")[:60]
IM_SL=json.load(open("data/images_sl.json")) if os.path.exists("data/images_sl.json") else {}
GM={}
if os.path.exists("data/gmaps_photos.json"):
    for p in json.load(open("data/gmaps_photos.json")): GM[p.get("placeId")]=[(i.get("imageUrl") if isinstance(i,dict) else i) for i in (p.get("imageUrls") or [])]
def fetch(u):
    for hdr in ({"User-Agent":"Mozilla/5.0","Referer":"https://www.google.com/"},{"User-Agent":"Mozilla/5.0 (Macintosh) Chrome/126","Accept":"image/*,*/*"}):
        try: return urllib.request.urlopen(urllib.request.Request(html.unescape(u),headers=hdr),timeout=25).read()
        except Exception: continue
def ahash(im):
    g=im.convert("L").resize((16,16)); px=list(g.getdata()); m=sum(px)/len(px); return "".join("1" if p>m else "0" for p in px)
def hdist(a,b): return sum(x!=y for x,y in zip(a,b))
def b64(path, size=640):
    im=Image.open(path).convert("RGB"); im.thumbnail((size,size)); b=io.BytesIO(); im.save(b,"JPEG",quality=70); return "data:image/jpeg;base64,"+base64.b64encode(b.getvalue()).decode()
def vision(venue, path, anchors):
    content=[{"type":"text","text":f"Venue: {venue['name']}, {venue.get('county') or ''} ({venue.get('setting') or ''}). "+("The first %d image(s) are CONFIRMED photos of this venue for reference. Judge the LAST image: " % len(anchors) if anchors else "Judge this image: ")+"is it plausibly this venue, its grounds, or an event there? Return JSON {is_venue:'yes'|'unsure'|'no', category: one of exterior, grounds_view, ceremony, reception_room, bedroom, bar_lounge, food, couple_portrait, other, quality:1-5, reason: short}. Say 'no' if it is clearly a different building/landscape, a stock image, a logo, a map, a different hotel, or a photographer's portrait with no venue context that contradicts the reference."}]
    for a in anchors: content.append({"type":"image_url","image_url":{"url":b64(a,512),"detail":"low"}})
    content.append({"type":"image_url","image_url":{"url":b64(path,640),"detail":"low"}})
    try:
        d=post(PROXY,{"token":TOK,"key_name":"OPENAI_API_KEY","task_summary":"vision-verify shortlist venue photos","path":"/v1/chat/completions","payload":{"model":"gpt-5.6-sol","response_format":{"type":"json_object"},"messages":[{"role":"user","content":content}]}},{})
        return json.loads(d["choices"][0]["message"]["content"])
    except Exception as e: return {"error":str(e)[:100]}
def work(kv):
    k,v=kv; folder="out/photos/"+slug(v["name"]); os.makedirs(folder,exist_ok=True)
    items=[]  # (path, src)
    for p in sorted(glob.glob(folder+"/[0-9][0-9].jpg")): items.append((p,"earlier"))
    cands=[(o["url"],o["src"]) for o in IM_SL.get(k,[])]+[(u,"google_maps") for u in GM.get(k,[])]
    seen=set(); n=0
    for u,s in cands:
        if u in seen: continue
        seen.add(u); b=fetch(u)
        if not b: continue
        try:
            im=Image.open(io.BytesIO(b)).convert("RGB")
            if im.width<500 or im.height<300: continue
            im.thumbnail((1400,1400)); path=f"{folder}/sl_{n:03d}.jpg"; im.save(path,"JPEG",quality=76,optimize=True); items.append((path,s)); n+=1
        except Exception: continue
        if n>=140: break
    # dedupe by average hash
    kept=[]; hashes=[]
    for p,s in items:
        try: h=ahash(Image.open(p))
        except Exception: continue
        if any(hdist(h,x)<=6 for x in hashes): continue
        hashes.append(h); kept.append((p,s))
    # anchors: 2 venue-site photos (prefer sl_ from venue src, else earlier)
    anchors=[p for p,s in kept if s=="venue"][:2] or [p for p,s in kept][:1]
    out=[]
    def judge(ps):
        p,s=ps; r=vision(v, p, [a for a in anchors if a!=p][:2]); r["path"]=p; r["src"]=s; return r
    with cf.ThreadPoolExecutor(6) as ex: out=list(ex.map(judge, kept))
    return k,out
res={}
with cf.ThreadPoolExecutor(5) as ex:
    for k,o in ex.map(work,sl.items()):
        res[k]=o; json.dump(res,open("data/photos_verified.json","w"))
        ok=sum(1 for x in o if x.get("is_venue")=="yes"); print(f'{sl[k]["name"][:30]:30} checked={len(o):3} yes={ok:3} unsure={sum(1 for x in o if x.get("is_venue")=="unsure"):3} no={sum(1 for x in o if x.get("is_venue")=="no"):3}', flush=True)
