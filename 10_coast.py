"""Per-venue Overpass query: nearest OSM coastline node and nearest tagged beach within 8km. Writes data/coast.json"""
import json, math, time, csv, urllib.request, urllib.parse
u=json.load(open("data/universe.json")); cls={json.loads(l)["key"]:json.loads(l) for l in open("data/classified.jsonl")}
names={r["Venue"] for r in csv.DictReader(open("data/venue_matrix.csv"))}
targets=[(k,u[k]) for k,r in cls.items() if r["name"] in names and u.get(k,{}).get("lat")]
def hav(a,b,c,d):
    p=math.pi/180; x=math.sin((c-a)*p/2)**2+math.cos(a*p)*math.cos(c*p)*math.sin((d-b)*p/2)**2; return 12742*math.asin(math.sqrt(x))
import concurrent.futures as cf, os
out=json.load(open("data/coast.json")) if os.path.exists("data/coast.json") else {}
targets=[t for t in targets if t[0] not in out]
def one(kv):
    k,v=kv
    q=f'[out:json][timeout:40];(way["natural"="coastline"](around:8000,{v["lat"]},{v["lng"]});nwr["natural"="beach"](around:8000,{v["lat"]},{v["lng"]}););out geom tags;'
    for attempt in range(3):
        try:
            d=json.load(urllib.request.urlopen(urllib.request.Request("https://maps.mail.ru/osm/tools/overpass/api/interpreter",urllib.parse.urlencode({"data":q}).encode()),timeout=60)); break
        except Exception as e: d={"elements":[]}; time.sleep(5)
    coast=None; beach=None
    for e in d["elements"]:
        t=e.get("tags",{})
        pts=e.get("geometry") or ([{"lat":e["lat"],"lon":e["lon"]}] if "lat" in e else [])
        if not pts and "bounds" in e: b=e["bounds"]; pts=[{"lat":(b["minlat"]+b["maxlat"])/2,"lon":(b["minlon"]+b["maxlon"])/2}]
        dmin=min((hav(v["lat"],v["lng"],p["lat"],p["lon"]) for p in pts), default=None)
        if dmin is None: continue
        if t.get("natural")=="coastline": coast=dmin if coast is None else min(coast,dmin)
        elif t.get("natural")=="beach" and (beach is None or dmin<beach[0]): beach=(dmin,t.get("name"))
    return k,{"coast_km": round(coast,1) if coast is not None else None, "beach_km": round(beach[0],1) if beach else None, "beach_name": beach[1] if beach else None}
with cf.ThreadPoolExecutor(6) as ex:
    for i,(k,o) in enumerate(ex.map(one,targets),1):
        out[k]=o
        if i%5==0: json.dump(out,open("data/coast.json","w"),indent=1); print(i,"of",len(targets),flush=True)
json.dump(out,open("data/coast.json","w"),indent=1)
print("done",len(out),"coast<1km",sum(1 for o in out.values() if (o["coast_km"] or 99)<1),"no coast within 8km",sum(1 for o in out.values() if o["coast_km"] is None))
