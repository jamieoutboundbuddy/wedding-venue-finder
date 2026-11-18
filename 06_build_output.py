"""Stage 4: rank classified venues, write data/venue_matrix.csv + xlsx tab + swipe page venue-shortlist.html"""
import json, csv, html, re, collections
rows=[json.loads(l) for l in open("data/classified.jsonl")]
import urllib.parse
BENCH=()   # optional: lowercase name fragments of venues you already like; kept and listed first
def root(u):
    d=urllib.parse.urlparse(u).netloc.lower().replace("www.",""); return ".".join(d.split(".")[-2:]) if not d.endswith(".ie") else d
seen=set(); R=[]
rows.sort(key=lambda r:-((r.get("llm") or {}).get("fit_score") or 0))
for r in rows:
    k=root(r["website"]) if r.get("website") else r["key"]
    if k in seen and "dunmoregardens" not in k: continue
    seen.add(k); R.append(r)
def g(r,k): return (r.get("llm") or {}).get(k)
def hard_fail(r):
    l=r.get("llm") or {}; f=[]
    if l.get("error"): return ["site unreadable"]
    if l.get("venue_type") in ("not_a_venue","restaurant","barn") and not l.get("onsite_accommodation"): f.append("not a wedding venue with rooms")
    if l.get("is_wedding_venue") is False: f.append("no weddings on site")
    if l.get("onsite_catering") is False: f.append("no in-house catering")
    if l.get("onsite_accommodation") is False: f.append("no rooms on site")
    if (l.get("max_capacity") or 999) < 90: f.append(f"capacity {l.get('max_capacity')}")
    if (l.get("min_numbers") or 0) > 120: f.append(f"minimum {l.get('min_numbers')}")
    if (l.get("price_per_head_eur") or 0) > 165: f.append(f"€{l.get('price_per_head_eur')}/head published")
    if (r.get("drive_h") or 0) < 3 and r.get("drive_h") != 99: f.append(f"{r.get('drive_h')}h from Dublin")
    return f
import os
EN=json.load(open("data/enrich.json")) if os.path.exists("data/enrich.json") else {}
CO=json.load(open("data/coast.json")) if os.path.exists("data/coast.json") else {}
LK=json.load(open("data/links.json")) if os.path.exists("data/links.json") else {}
RV=json.load(open("data/rooms_verified.json")) if os.path.exists("data/rooms_verified.json") else {}
PV=json.load(open("data/photos_verified.json")) if os.path.exists("data/photos_verified.json") else {}
U=json.load(open("data/universe.json"))
for r in R:
    e=EN.get(r["key"],{}); u=U.get(r["key"],{})
    rv=RV.get(r["key"],{}); r["rooms"]=(rv.get("hotel_rooms") if rv.get("hotel_rooms") else (e.get("rooms") or g(r,"bedrooms_onsite"))); r["rooms_conf"]=rv.get("confidence"); r["rooms_extra"]=rv.get("extra_accommodation"); r["rooms_note"]=rv.get("note"); r["phone"]=e.get("phone") or u.get("phone"); r["email"]=e.get("email") or g(r,"enquiry_email")
    c=CO.get(r["key"],{}); r["coast_km"]=c.get("coast_km"); r["beach_km"]=c.get("beach_km"); r["beach_name"]=c.get("beach_name"); IM=json.load(open("data/images.json")) if os.path.exists("data/images.json") else {}
    IM2=json.load(open("data/images2.json")) if os.path.exists("data/images2.json") else {}
    r["gallery"]=[i for i in (g(r,"hero_images") or []) if i.startswith("http")]+(IM2.get(r["key"]) or [])[:25]+(IM.get(r["key"]) or [])+(e.get("images") or [])+(IM2.get(r["key"]) or [])[25:]
    r["links"]=dict(LK.get(r["key"],{}))
    r["lat"]=u.get("lat"); r["lng"]=u.get("lng")
    if not r["links"].get("google_maps") and r["lat"]: r["links"]["google_maps"]=f"https://www.google.com/maps/search/?api=1&query={r['lat']},{r['lng']}"
    r["fails"]=hard_fail(r); r["fit"]=g(r,"fit_score") or 0
    r["bench"]= any(r["name"].lower().startswith(b) or b in r["name"].lower().split()[0] for b in BENCH)
keep=[r for r in R if not r["fails"] or r["bench"]]
ORDER=list(BENCH)
DEFAULT_NO=[]   # optional: name fragments to pre-mark as no
def bidx(r):
    n=r["name"].lower(); return next((i for i,b in enumerate(ORDER) if b in n), 99)
keep.sort(key=lambda r:(0 if r["bench"] else 1, bidx(r), -r["fit"]))
default_no=[r["name"] for r in keep if any(b in r["name"].lower() for b in DEFAULT_NO)]
jv={}
if os.path.exists("data/votes.tsv"):
    for l in open("data/votes.tsv"):
        if "\t" in l: v,n=l.rstrip("\n").split("\t",1); jv[n]=v
default_votes={**{n:"no" for n in default_no}, **jv}
print("classified", len(R), "| pass hard gates", len([r for r in R if not r["fails"]]), "| fit>=70:", len([r for r in R if not r["fails"] and r["fit"]>=70]))
print(collections.Counter(f for r in R for f in r["fails"]).most_common(8))
# --- CSV in your own shortlist shape
cols=["Venue","County","Drive from Dublin (h)","Type","Setting","Style","Rooms on site","Sea / coast (km)","Nearest named beach (km)","Nearest named beach","Phone","Email","Exclusive use?","All-in package?","Published €/head","Min numbers","Max capacity","Civil ceremony on site?","Fit score","Why","Red flags","Website","Wedding page","Gallery pages","Instagram","Facebook","Google Maps","hitched.ie","Photographer posts","Enquiry email","Google rating","Reviews","Fails a hard gate?"]
with open("data/venue_matrix.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(cols)
    for r in keep+[r for r in R if r["fails"] and not r["bench"] and r["fit"]>=60]:
        w.writerow([r["name"], r.get("county"), r.get("drive_h") if r.get("drive_h")!=99 else "", g(r,"venue_type"), g(r,"setting"), ", ".join(g(r,"style_words") or []),
                    r["rooms"], r["coast_km"], r["beach_km"], r["beach_name"], r["phone"], r["email"], g(r,"exclusive_use_option"), g(r,"all_in_package"), g(r,"price_per_head_eur"), g(r,"min_numbers"), g(r,"max_capacity"),
                    g(r,"civil_ceremony_onsite"), r["fit"], g(r,"fit_reason"), "; ".join(g(r,"red_flags") or []), r["website"], r.get("wedding_page"), " | ".join(r["links"].get("gallery_pages",[])), r["links"].get("instagram"), r["links"].get("facebook"), r["links"].get("google_maps"), r["links"].get("hitched"), " | ".join(p["url"] for p in r["links"].get("posts",[])), r["email"],
                    r.get("rating"), r.get("reviews"), "; ".join(r["fails"])])
# --- swipe page
TYPE={"hotel":"Hotel","country_house":"Country house","castle":"Castle","estate_exclusive":"Private estate","restaurant":"Restaurant with rooms","barn":"Barn venue","other":"Venue","not_a_venue":"Not a wedding venue",None:""}
def chips(r):
    c=[]; unknown=[]
    if r.get("rooms"): c.append(f"{r['rooms']} bedrooms on site" + (" ✓ verified" if r.get("rooms_conf") in ("high","medium") else ""))
    if r.get("rooms_extra"): c.append(f"plus {html.escape(str(r['rooms_extra']))}")
    else: unknown.append("rooms")
    if r.get("coast_km") is not None: c.append(f"Sea {r['coast_km']} km" if r["coast_km"]>=0.1 else "On the sea")
    if r.get("beach_name"): c.append(f"{html.escape(str(r['beach_name']))} {r['beach_km']} km")
    mx=g(r,"max_capacity"); mn=g(r,"min_numbers")
    if mx and mn: c.append(f"{mn} to {mx} guests")
    elif mx: c.append(f"Up to {mx} guests")
    elif mn: c.append(f"Minimum {mn} guests")
    else: unknown.append("guest numbers")
    p=g(r,"price_per_head_eur")
    if p: c.append(f"From about €{int(p)} a head")
    else: unknown.append("price")
    if g(r,"exclusive_use_option") is True: c.append("Exclusive use available")
    if g(r,"all_in_package") is True: c.append("All-inclusive package (venue, meal and drinks in one price)")
    elif g(r,"all_in_package") is None: unknown.append("packages")
    if g(r,"civil_ceremony_onsite") is True: c.append("Ceremony on site")
    if r.get("rating"): c.append(f"Google {r['rating']} ({r.get('reviews') or 0} reviews)")
    return c, unknown
def A(u,t): return f'<a href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(t)}</a>'
def linkrow(r):
    L=r["links"]; items=[A(r["website"],"website")]
    if r.get("wedding_page"): items.append(A(r["wedding_page"],"weddings"))
    for i,gp in enumerate(L.get("gallery_pages",[])[:2]): items.append(A(gp,"gallery" if i==0 else "gallery 2"))
    if L.get("rooms_pages"): items.append(A(L["rooms_pages"][0],"rooms"))
    if L.get("instagram"): items.append(A(L["instagram"],"instagram"))
    if L.get("facebook"): items.append(A(L["facebook"],"facebook"))
    if L.get("google_maps"): items.append(A(L["google_maps"],"google maps"))
    if L.get("hitched"): items.append(A(L["hitched"],"hitched.ie"))
    items.append(f'<a href="#" onclick="showOnMap({html.escape(json.dumps(r["name"]))});return false">📍 show on map</a>')
    return " · ".join(items)
def posts(r):
    P=r["links"].get("posts",[])
    if not P: return ""
    return '<details class="posts"><summary>Real weddings here, from photographers and blogs (' + str(len(P)) + ')</summary><ul>' + "".join(f'<li>{A(p["url"], p["title"] or p["domain"])} <span class="dom">{html.escape(p["domain"])}</span></li>' for p in P) + '</ul></details>'
CAT_ORDER=["exterior","grounds_view","ceremony","reception_room","bar_lounge","bedroom","couple_portrait","food","other"]
CAT_LABEL={"exterior":"Exterior","grounds_view":"Grounds & views","ceremony":"Ceremony","reception_room":"Reception","bar_lounge":"Bar & lounge","bedroom":"Bedrooms","couple_portrait":"Real weddings","food":"Food","other":"Other"}
def verified_imgs(r):
    P=PV.get(r["key"])
    if not P: return None
    good=[p for p in P if p.get("is_venue")=="yes" or (p.get("is_venue")=="unsure" and (p.get("quality") or 0)>=4)]
    # curated order: round-robin across categories, best quality first, confirmed-venue shots before "unsure"
    MIX=["exterior","grounds_view","ceremony","reception_room","bedroom","bar_lounge","couple_portrait","food","other"]
    buckets={c:sorted([p for p in good if p.get("category")==c], key=lambda p:(0 if p.get("is_venue")=="yes" else 1, -(p.get("quality") or 0))) for c in MIX}
    out=[]
    while any(buckets.values()):
        for c in MIX:
            if buckets[c]: out.append(buckets[c].pop(0))
    return out
def card(r):
    VI=verified_imgs(r)
    imgs=[("LOCAL:"+p["path"], p.get("category")) for p in VI][:80] if VI else [(u,None) for u in list(dict.fromkeys(r["gallery"]))[:45]]
    tag = "on your own shortlist" + (" · marked ❌" if any(b in r["name"].lower() for b in DEFAULT_NO) else "") if r["bench"] else ("fails: "+"; ".join(r["fails"]) if r["fails"] else "")
    c,unknown=chips(r)
    drive = f"{r.get('drive_h')}h from Dublin" if r.get('drive_h') not in (None,99) else ""
    meta=" · ".join(x for x in [html.escape(str(r.get('county') or '')), drive, TYPE.get(g(r,'venue_type'),''), html.escape(str(g(r,'setting') or ''))] if x)
    da=f' data-county="{html.escape(str(r.get("county") or ""))}" data-drive="{r.get("drive_h") if r.get("drive_h") not in (None,99) else ""}" data-sea="{r.get("coast_km") if r.get("coast_km") is not None else ""}" data-rooms="{r.get("rooms") or ""}" data-excl="{1 if g(r,"exclusive_use_option") else 0}" data-allin="{1 if g(r,"all_in_package") else 0}" data-type="{g(r,"venue_type") or ""}"'
    return f"""<article class="v" data-fit="{r['fit']}" data-name="{html.escape(r['name'])}"{da}>
<div class="imgs">{''.join(f'<img loading="lazy" src="{html.escape(i)}" onerror="this.remove()" onclick="openLb(this)"{f' data-cat="{c}"' if c else ''}>' for i,c in imgs) or '<div class="noimg">no image found</div>'}</div>
{('<p class="cats">' + ' '.join(f'<button class="cb" onclick="catFilter(this,{json.dumps(c)})">{CAT_LABEL[c]} ({sum(1 for _,x in imgs if x==c)})</button>' for c in CAT_ORDER if any(x==c for _,x in imgs)) + ' <button class="cb on" onclick="catFilter(this,null)">All (' + str(len(imgs)) + ')</button> <span class="vtag">photos checked ✓</span></p>') if VI else ''}
<div class="body"><h2>{html.escape(r['name'])} <span class="fit" title="How well it fits your brief, 0 to 100">fit {r['fit']}</span></h2>
<p class="meta">{meta}</p>
<p class="chips">{''.join(f'<span class="chip">{x}</span>' for x in c)}</p>
{f'<p class="unknown">Not on their website: {", ".join(unknown)}. Ask when you enquire.</p>' if unknown else ''}
<p class="why">{html.escape(g(r,'fit_reason') or '')}</p>
{f'<p class="flags">Watch out: {html.escape("; ".join(g(r,"red_flags") or []))}</p>' if g(r,'red_flags') else ''}
{f'<p class="tag">{html.escape(tag)}</p>' if tag else ''}
<p class="links">{html.escape(str(r.get('phone') or ''))}{' · ' if r.get('phone') and r.get('email') else ''}{f'<a href="mailto:{html.escape(str(r["email"]))}">{html.escape(str(r["email"]))}</a>' if r.get('email') else ''}</p>
<p class="links">{linkrow(r)}</p>
{posts(r)}
<div class="vote"><button onclick="vote(this,'yes')">❤️ like</button><button onclick="vote(this,'maybe')">🤔 maybe</button><button onclick="vote(this,'no')">❌ no</button></div>
</div></article>"""
# --- map data: Ireland outline from Natural Earth, venues as dots
coast=[]
try:
    ne=json.load(open("data/ne_coast.geojson"))
    def lines(c, acc):
        if c and isinstance(c[0][0],(int,float)): acc.append(c)
        else:
            for x in c: lines(x, acc)
    segs=[]
    for f in ne["features"]: lines(f["geometry"]["coordinates"], segs)
    def inside(lon,lat): return 51.3<lat<55.5 and -10.8<lon<-5.35 and not (lat>55.0 and lon>-5.9)
    for seg in segs:
        run=[]
        for lon,lat in seg:
            if inside(lon,lat): run.append((lon,lat))
            else:
                if len(run)>1: coast.append(run)
                run=[]
        if len(run)>1: coast.append(run)
except Exception as e: print("no coast outline", e)
def proj(lon,lat): return round((lon+10.8)*130,1), round((55.5-lat)*130*1.66,1)
svg_coast="".join('<polyline points="'+" ".join(f"{proj(a,b)[0]},{proj(a,b)[1]}" for a,b in seg)+'"/>' for seg in coast)
vjson=json.dumps([{"n":r["name"],"x":proj(r["lng"],r["lat"])[0],"y":proj(r["lng"],r["lat"])[1],"fit":r["fit"],"c":r.get("county") or "","d":r.get("drive_h") if r.get("drive_h")!=99 else None,"rooms":r.get("rooms"),"sea":r.get("coast_km"),"gm":r["links"].get("google_maps"),"b":r["bench"],"lat":r["lat"],"lng":r["lng"],"rooms":r.get("rooms"),"county":r.get("county") or ""} for r in keep if r.get("lat")])
page=f"""<meta charset="utf-8"><title>Venue Swipe</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500&family=Karla:wght@400;500;700&display=swap">
<style>
:root{{--ground:#F5F7F6;--surface:#FFFFFF;--ink:#1B2A2E;--muted:#63757A;--faint:#93A2A6;--accent:#2B5F6B;--flag:#9C5A2A;--rule:#CFD9D6;--track:#DDE4E2}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--ground:#141C1F;--surface:#1D282C;--ink:#E8EDEB;--muted:#9BADB2;--faint:#6C7F85;--accent:#7FB3BE;--flag:#D9975F;--rule:#314247;--track:#26343A}}}}
:root[data-theme="dark"]{{--ground:#141C1F;--surface:#1D282C;--ink:#E8EDEB;--muted:#9BADB2;--faint:#6C7F85;--accent:#7FB3BE;--flag:#D9975F;--rule:#314247;--track:#26343A}}
body{{margin:0;background:var(--ground);color:var(--ink);font-family:Karla,"Helvetica Neue",Arial,sans-serif;line-height:1.5}}
.wrap{{max-width:1000px;margin:0 auto;padding:24px 20px 80px}} h1{{font-family:Fraunces,Georgia,serif;font-weight:500;font-size:34px;margin:0 0 8px;text-wrap:balance}}
.intro{{color:var(--muted);max-width:65ch;margin:0 0 16px}}
.v{{background:var(--surface);border:1px solid var(--rule);border-radius:6px;margin:18px 0;overflow:hidden}} .v.yes{{border-color:var(--accent);border-width:3px}} .v.no{{border-left:6px solid #c0392b;opacity:1}} .v.maybe{{border-color:var(--flag);border-width:3px}}
.imgs{{display:flex;gap:3px;overflow-x:auto;scroll-snap-type:x mandatory;background:var(--track);-webkit-overflow-scrolling:touch}} .imgs img{{flex:0 0 auto;height:320px;width:auto;max-width:92vw;object-fit:contain;display:block;scroll-snap-align:start;background:var(--track)}} .imgs::-webkit-scrollbar{{height:8px}} .imgs::-webkit-scrollbar-thumb{{background:var(--faint);border-radius:4px}} .noimg{{padding:40px;color:var(--faint);text-align:center}}
.body{{padding:14px 18px 18px}} h2{{margin:0 0 4px;font-size:22px;font-family:Fraunces,Georgia,serif;font-weight:500}} .fit{{float:right;background:var(--accent);color:var(--ground);border-radius:14px;padding:2px 10px;font-size:14px;font-variant-numeric:tabular-nums}}
.meta{{color:var(--muted);font-size:14px;margin:4px 0 10px}} .chips{{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 8px}} .chip{{background:var(--track);color:var(--ink);border-radius:4px;padding:3px 9px;font-size:13.5px}} .unknown{{color:var(--faint);font-size:13px;margin:0 0 6px}} .why{{margin:6px 0;max-width:75ch}} .flags{{color:var(--flag);font-size:13px}} .tag{{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--flag);font-weight:700}}
.links a{{color:var(--accent)}} .posts{{margin:6px 0 10px;font-size:14px}} .posts summary{{cursor:pointer;color:var(--accent)}} .posts ul{{margin:6px 0 0;padding-left:18px}} .posts li{{margin:3px 0}} .posts .dom{{color:var(--faint);font-size:12px;margin-left:6px}}
.vote button{{margin-right:8px;padding:8px 14px;border:1px solid var(--rule);border-radius:6px;background:var(--surface);color:var(--ink);cursor:pointer;font-size:15px}} .vote button:focus-visible{{outline:2px solid var(--accent)}}
.imgs img{{cursor:zoom-in}} .cats{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:6px 0 0;padding:0 18px}} .cb{{font-size:12.5px;padding:3px 9px;border:1px solid var(--rule);border-radius:12px;background:var(--surface);color:var(--ink);cursor:pointer}} .cb.on{{background:var(--accent);color:var(--ground);border-color:var(--accent)}} .vtag{{font-size:12px;color:var(--accent);margin-left:auto}} #lb{{position:fixed;inset:0;background:rgba(10,16,18,.94);display:none;align-items:center;justify-content:center;z-index:50}} #lb.on{{display:flex}} #lb img{{max-width:96vw;max-height:90vh;object-fit:contain;box-shadow:0 8px 40px rgba(0,0,0,.5)}} #lb .x,#lb .p,#lb .n{{position:absolute;color:#fff;background:rgba(255,255,255,.12);border:0;font-size:26px;width:48px;height:48px;border-radius:24px;cursor:pointer}} #lb .x{{top:16px;right:16px}} #lb .p{{left:16px;top:50%;margin-top:-24px}} #lb .n{{right:16px;top:50%;margin-top:-24px}} #lb .c{{position:absolute;bottom:14px;left:0;right:0;text-align:center;color:#cfd9d6;font-size:13px}}
.views .vb{{margin-right:4px}} .views .vb.on{{background:var(--accent);color:var(--ground);border-color:var(--accent)}}
.lt{{border-collapse:collapse;width:100%;font-size:14px;background:var(--surface)}} .lt th{{text-align:left;font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding:8px;border-bottom:1px solid var(--ink)}} .lt td{{padding:7px 8px;border-bottom:1px solid var(--rule)}} .lt .r{{text-align:right;font-variant-numeric:tabular-nums}} .lt tr.yes td{{background:color-mix(in srgb,var(--accent) 12%,var(--surface))}} .lt tr.no td{{color:var(--muted)}} .lt tr.maybe td{{background:color-mix(in srgb,var(--flag) 12%,var(--surface))}} .lt a{{color:var(--accent)}}
.mapwrap{{position:relative;background:var(--surface);border:1px solid var(--rule);border-radius:6px}} #svgmap{{display:block;height:min(84vh,900px);width:auto;max-width:100%;margin:0 auto}} .mapwrap{{display:flex;justify-content:center}} #pv{{position:absolute;right:12px;top:12px;width:280px;background:var(--surface);border:1px solid var(--rule);border-radius:6px;box-shadow:0 8px 30px rgba(0,0,0,.18);display:none;overflow:hidden;z-index:3}} #pv img{{width:100%;height:170px;object-fit:cover;display:block;cursor:zoom-in}} #pv .pb{{padding:10px 12px 12px}} #pv h3{{margin:0 0 4px;font-family:Fraunces,Georgia,serif;font-weight:500;font-size:17px}} #pv p{{margin:0 0 6px;font-size:13px;color:var(--muted)}} #pv .btns a,#pv .btns button{{font-size:13px;margin-right:6px;padding:5px 9px;border:1px solid var(--rule);border-radius:5px;background:var(--surface);color:var(--accent);text-decoration:none;cursor:pointer}} #pv .close{{position:absolute;top:6px;right:8px;background:rgba(0,0,0,.45);color:#fff;border:0;border-radius:12px;width:24px;height:24px;cursor:pointer}} .coast polyline{{fill:none;stroke:var(--faint);stroke-width:1.2}} #dots circle{{stroke:var(--surface);stroke-width:1;cursor:pointer;fill:var(--muted)}} #dots circle.yes{{fill:var(--accent)}} #dots circle.maybe{{fill:var(--flag)}} #dots circle.no{{fill:var(--faint);opacity:.35}} #dots circle.b{{stroke:var(--ink);stroke-width:2}} #dots circle.sel{{stroke:#c0392b;stroke-width:4}} #tip{{position:absolute;pointer-events:none;background:var(--ink);color:var(--ground);font-size:13px;padding:6px 9px;border-radius:4px;display:none;max-width:260px}}
.filters{{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;padding:10px 12px;margin:12px 0;background:var(--surface);border:1px solid var(--rule);border-radius:6px;font-size:13.5px}} .filters input[type=text],.filters input:not([type]),.filters input[type=number],.filters select{{padding:5px 8px;border:1px solid var(--rule);border-radius:5px;background:var(--ground);color:var(--ink);font:inherit}} .filters input[type=number]{{width:64px}} .filters label{{display:inline-flex;gap:5px;align-items:center;color:var(--muted)}} .filters button{{padding:5px 10px;border:1px solid var(--rule);border-radius:5px;background:var(--surface);color:var(--ink);cursor:pointer}} #f_count{{color:var(--muted);margin-left:auto}}
.bar{{position:sticky;top:0;background:var(--ground);padding:10px 0;border-bottom:1px solid var(--rule);display:flex;gap:10px;align-items:center;flex-wrap:wrap;z-index:2}} .bar button{{padding:6px 12px;border:1px solid var(--rule);border-radius:6px;background:var(--surface);color:var(--ink);cursor:pointer}}
</style><div class="wrap"><h1>Venue swipe · {len(keep)} venues, 3h+ from Dublin</h1>
<p class="intro">Swipe or scroll sideways through each venue's photos. Ranked by fit to your brief. your own shortlist sits at the top in her order; the ones she crossed off are pre-marked ❌ no (you can change any vote). Votes save in this browser; use Export to copy them out.</p>
<div class="bar"><span class="views"><button class="vb on" onclick="setView('cards')">Cards</button><button class="vb" onclick="setView('list')">List</button><button class="vb" onclick="setView('map')">Map</button></span><b id="count"></b><button onclick="filter('all')">all</button><button onclick="filter('yes')">liked</button><button onclick="hideNo()">liked + maybe</button><button onclick="exportVotes()">export votes</button><button onclick="importVotes()">import votes</button></div>
<div class="filters" id="filters">
<input id="f_q" placeholder="search name" oninput="applyFilters()">
<select id="f_county" onchange="applyFilters()"><option value="">any county</option>{''.join(f'<option>{html.escape(c)}</option>' for c in sorted({r.get("county") for r in keep if r.get("county")}))}</select>
<select id="f_vote" onchange="applyFilters()"><option value="">any vote</option><option value="yes">❤️ liked</option><option value="maybe">🤔 maybe</option><option value="no">❌ no</option><option value="none">not voted</option><option value="yesmaybe">liked or maybe</option></select>
<label>max drive <input id="f_drive" type="number" step="0.5" placeholder="h" oninput="applyFilters()"></label>
<label>sea within <input id="f_sea" type="number" step="0.5" placeholder="km" oninput="applyFilters()"></label>
<label>min rooms <input id="f_rooms" type="number" placeholder="n" oninput="applyFilters()"></label>
<label>min fit <input id="f_fit" type="number" placeholder="0-100" oninput="applyFilters()"></label>
<label><input id="f_excl" type="checkbox" onchange="applyFilters()"> exclusive use</label>
<label><input id="f_allin" type="checkbox" onchange="applyFilters()"> all-in package</label>
<button onclick="resetFilters()">clear</button><span id="f_count"></span>
</div>
<div id="cards">{''.join(card(r) for r in keep)}</div>
<div id="list" hidden><table class="lt"><thead><tr><th>Vote</th><th>Venue</th><th>County</th><th class="r">Drive</th><th class="r">Fit</th><th class="r">Rooms</th><th class="r">Sea km</th><th>Type</th><th>Links</th></tr></thead><tbody>
{''.join(f'<tr data-name="{html.escape(r["name"])}"><td class="vt"></td><td><a href="#" onclick="jump(this);return false">{html.escape(r["name"])}</a></td><td>{html.escape(str(r.get("county") or ""))}</td><td class="r">{r.get("drive_h") if r.get("drive_h")!=99 else ""}</td><td class="r">{r["fit"]}</td><td class="r">{r.get("rooms") or ""}</td><td class="r">{r.get("coast_km") if r.get("coast_km") is not None else ""}</td><td>{TYPE.get(g(r,"venue_type"),"")}</td><td>{A(r["website"],"site")}{" · "+A(r["links"]["google_maps"],"map") if r["links"].get("google_maps") else ""}</td></tr>' for r in keep)}
</tbody></table></div>
<div id="map" hidden><p class="intro">Dot size is fit score, colour is your vote. Click a dot to jump to the venue.</p><div class="mapwrap"><svg id="svgmap" viewBox="0 0 710 910" xmlns="http://www.w3.org/2000/svg"><g class="coast">{svg_coast}</g><g id="dots"></g></svg><div id="tip"></div><div id="pv"><button class="close" onclick="document.getElementById('pv').style.display='none'">×</button><img id="pvimg" onclick="const el=cardOf(pvName);if(el){{const im=el.querySelector('.imgs img');if(im)openLb(im)}}"><div class="pb"><h3 id="pvname"></h3><p id="pvmeta"></p><p id="pvchips"></p><div class="btns"><button onclick="goCard(pvName)">Open card</button><a id="pvmap" target="_blank" rel="noopener">Google Maps</a><button onclick="vote(cardOf(pvName).querySelector('.vote button'),'yes')">❤️</button><button onclick="vote(cardOf(pvName).querySelector('.vote button'),'maybe')">🤔</button><button onclick="vote(cardOf(pvName).querySelector('.vote button'),'no')">❌</button></div></div></div></div></div>
</div><div id="lb" onclick="if(event.target.id=='lb')closeLb()"><button class="x" onclick="closeLb()">×</button><button class="p" onclick="step(-1)">‹</button><img id="lbimg"><button class="n" onclick="step(1)">›</button><div class="c" id="lbc"></div></div><script>
let lbList=[],lbI=0;
function openLb(img){{lbList=[...img.closest('.imgs').querySelectorAll('img')];lbI=lbList.indexOf(img);show()}}
function show(){{const im=lbList[lbI];document.getElementById('lbimg').src=im.src;document.getElementById('lbc').textContent=(lbI+1)+' / '+lbList.length+' · '+im.closest('.v').dataset.name;document.getElementById('lb').classList.add('on')}}
function step(d){{lbI=(lbI+d+lbList.length)%lbList.length;show()}}
function closeLb(){{document.getElementById('lb').classList.remove('on')}}
document.addEventListener('keydown',e=>{{if(!document.getElementById('lb').classList.contains('on'))return;if(e.key=='Escape')closeLb();if(e.key=='ArrowRight')step(1);if(e.key=='ArrowLeft')step(-1)}});
const K='venue-votes-v1';let votes={{}};try{{votes=JSON.parse(localStorage.getItem(K)||'{{}}')}}catch(e){{}}
const DEFAULT_VOTES={json.dumps(default_votes)}; Object.entries(DEFAULT_VOTES).forEach(([n,v])=>{{if(!(n in votes))votes[n]=v}}); try{{localStorage.setItem(K,JSON.stringify(votes))}}catch(e){{}}
function paint(){{document.querySelectorAll('.v').forEach(a=>{{a.classList.remove('yes','no','maybe');const v=votes[a.dataset.name];if(v)a.classList.add(v)}});
 const c=Object.values(votes);document.getElementById('count').textContent=`❤️ ${{c.filter(x=>x=='yes').length}} · 🤔 ${{c.filter(x=>x=='maybe').length}} · ❌ ${{c.filter(x=>x=='no').length}}`}}
function vote(b,v){{const a=b.closest('.v');votes[a.dataset.name]=v;try{{localStorage.setItem(K,JSON.stringify(votes))}}catch(e){{}};paint()}}
function filter(f){{document.getElementById('f_vote').value=f=='all'?'':f;applyFilters()}}
function hideNo(){{document.getElementById('f_vote').value='yesmaybe';applyFilters()}}
function importVotes(){{const t=prompt('Paste an export (one "vote<TAB>name" per line):');if(!t)return;let n=0;t.split(String.fromCharCode(10)).forEach(l=>{{const m=l.match(/^(yes|maybe|no)\t(.+)$/);if(m){{votes[m[2].trim()]=m[1];n++}}}});try{{localStorage.setItem(K,JSON.stringify(votes))}}catch(e){{}};paint();alert('imported '+n+' votes')}}
function exportVotes(){{const t=Object.entries(votes).map(([n,v])=>v+'\\t'+n).join('\\n');navigator.clipboard.writeText(t);alert('copied '+Object.keys(votes).length+' votes')}}
const V={vjson};
function setView(v){{['cards','list','map'].forEach(x=>{{document.getElementById(x).hidden=(x!=v)}});document.querySelectorAll('.vb').forEach(b=>b.classList.toggle('on',b.textContent.toLowerCase()==v));try{{localStorage.setItem('venue-view',v)}}catch(e){{}};if(v=='map')drawMap();if(v=='list')paintList()}}
function jump(a){{setView('cards');const n=a.closest('tr').dataset.name;const el=[...document.querySelectorAll('.v')].find(x=>x.dataset.name==n);if(el){{el.scrollIntoView({{behavior:'smooth',block:'start'}})}}}}
function paintList(){{document.querySelectorAll('#list tr[data-name]').forEach(tr=>{{const v=votes[tr.dataset.name]||'';tr.className=v;tr.querySelector('.vt').textContent=v=='yes'?'❤️':v=='maybe'?'🤔':v=='no'?'❌':''}})}}
function drawMap(){{const g=document.getElementById('dots');g.innerHTML='';const tip=document.getElementById('tip');V.forEach(v=>{{const c=document.createElementNS('http://www.w3.org/2000/svg','circle');c.setAttribute('cx',v.x);c.setAttribute('cy',v.y);c.setAttribute('r',3+v.fit/12);c.setAttribute('class',(votes[v.n]||'')+(v.b?' b':''));c.dataset.n=v.n;c.onclick=()=>preview(v);c.onmousemove=e=>{{const r=document.querySelector('.mapwrap').getBoundingClientRect();tip.style.display='block';tip.style.left=(e.clientX-r.left+12)+'px';tip.style.top=(e.clientY-r.top+12)+'px';tip.innerHTML='<b>'+v.n+'</b><br>'+v.c+(v.d?' · '+v.d+'h from Dublin':'')+'<br>fit '+v.fit+(v.rooms?' · '+v.rooms+' rooms':'')+(v.sea!=null?' · sea '+v.sea+' km':'')}};c.onmouseleave=()=>tip.style.display='none';g.appendChild(c)}})}}
let pvName='';
function catFilter(b,c){{const art=b.closest('.v');art.querySelectorAll('.cb').forEach(x=>x.classList.remove('on'));b.classList.add('on');art.querySelectorAll('.imgs img').forEach(im=>im.style.display=(!c||im.dataset.cat==c)?'':'none')}}
const FK='venue-filters-v1';
function fval(id){{const e=document.getElementById(id);return e.type=='checkbox'?e.checked:e.value}}
function readF(){{return {{q:fval('f_q').toLowerCase(),county:fval('f_county'),vote:fval('f_vote'),drive:parseFloat(fval('f_drive')),sea:parseFloat(fval('f_sea')),rooms:parseFloat(fval('f_rooms')),fit:parseFloat(fval('f_fit')),excl:fval('f_excl'),allin:fval('f_allin')}}}}
function passes(el,f){{const d=el.dataset;const v=votes[d.name]||'';
 if(f.q&&!d.name.toLowerCase().includes(f.q))return false;
 if(f.county&&d.county!=f.county)return false;
 if(f.vote=='none'?v!='':f.vote=='yesmaybe'?!(v=='yes'||v=='maybe'):f.vote&&v!=f.vote)return false;
 if(!isNaN(f.drive)&&d.drive!==''&&parseFloat(d.drive)>f.drive)return false;
 if(!isNaN(f.sea)&&(d.sea===''||parseFloat(d.sea)>f.sea))return false;
 if(!isNaN(f.rooms)&&(d.rooms===''||parseFloat(d.rooms)<f.rooms))return false;
 if(!isNaN(f.fit)&&parseFloat(d.fit)<f.fit)return false;
 if(f.excl&&d.excl!='1')return false; if(f.allin&&d.allin!='1')return false; return true}}
let visible=new Set();
function applyFilters(){{const f=readF();visible=new Set();document.querySelectorAll('.v').forEach(el=>{{const ok=passes(el,f);el.style.display=ok?'':'none';if(ok)visible.add(el.dataset.name)}});
 document.querySelectorAll('#list tr[data-name]').forEach(tr=>tr.style.display=visible.has(tr.dataset.name)?'':'none');
 document.getElementById('f_count').textContent=visible.size+' of '+document.querySelectorAll('.v').length+' venues';
 try{{localStorage.setItem(FK,JSON.stringify({{q:fval('f_q'),county:fval('f_county'),vote:fval('f_vote'),drive:fval('f_drive'),sea:fval('f_sea'),rooms:fval('f_rooms'),fit:fval('f_fit'),excl:fval('f_excl'),allin:fval('f_allin')}}))}}catch(e){{}}
 if(typeof syncMap=='function')syncMap()}}
function resetFilters(){{['f_q','f_county','f_vote','f_drive','f_sea','f_rooms','f_fit'].forEach(i=>document.getElementById(i).value='');['f_excl','f_allin'].forEach(i=>document.getElementById(i).checked=false);applyFilters()}}
function restoreFilters(){{try{{const f=JSON.parse(localStorage.getItem(FK)||'null');if(!f)return;['q','county','vote','drive','sea','rooms','fit'].forEach(k=>document.getElementById('f_'+k).value=f[k]||'');document.getElementById('f_excl').checked=!!f.excl;document.getElementById('f_allin').checked=!!f.allin}}catch(e){{}}}}
function syncMap(){{document.querySelectorAll('#dots circle').forEach(c=>c.style.display=visible.has(c.dataset.n)?'':'none')}}
function showOnMap(n){{setView('map');const v=V.find(x=>x.n==n);if(!v)return;preview(v);document.querySelectorAll('#dots circle').forEach(c=>c.classList.toggle('sel',c.dataset.n==n));window.scrollTo({{top:0,behavior:'smooth'}})}}
function cardOf(n){{return [...document.querySelectorAll('.v')].find(x=>x.dataset.name==n)}}
function goCard(n){{setView('cards');const el=cardOf(n);if(el)el.scrollIntoView({{behavior:'smooth',block:'start'}})}}
function preview(v){{pvName=v.n;const el=cardOf(v.n);const im=el&&el.querySelector('.imgs img');document.getElementById('pvimg').src=im?im.src:'';document.getElementById('pvimg').style.display=im?'block':'none';document.getElementById('pvname').textContent=v.n;document.getElementById('pvmeta').textContent=v.c+(v.d?' · '+v.d+'h from Dublin':'')+' · fit '+v.fit;document.getElementById('pvchips').textContent=el?[...el.querySelectorAll('.chip')].map(x=>x.textContent).join(' · '):'';const m=document.getElementById('pvmap');if(v.gm){{m.href=v.gm;m.style.display=''}}else m.style.display='none';document.getElementById('pv').style.display='block'}}
const oldPaint=paint;paint=function(){{oldPaint();paintList();applyFilters();if(!document.getElementById('map').hidden)drawMap()}};
restoreFilters();paint();applyFilters();let sv='cards';try{{sv=localStorage.getItem('venue-view')||'cards'}}catch(e){{}};setView(sv);</script>"""
open("out/venue-shortlist.html","w").write(page)
# embed downscaled images so the published artifact can show them (CSP blocks remote images)
import base64, io, urllib.request, concurrent.futures as cf
from PIL import Image
urls=list(dict.fromkeys(re.findall(r'<img loading="lazy" src="([^"]+)"', page)))
def fetch(u):
    if u.startswith("LOCAL:"):
        try:
            im=Image.open(u[6:]).convert("RGB"); im.thumbnail((360,360)); o=io.BytesIO(); im.save(o,"JPEG",quality=48,optimize=True); return "data:image/jpeg;base64,"+base64.b64encode(o.getvalue()).decode()
        except Exception: return None
    b=None
    for hdr in ({"User-Agent":"Mozilla/5.0"},{"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/126 Safari/537.36","Referer":"https://www.google.com/","Accept":"image/*,*/*"}):
        try: b=urllib.request.urlopen(urllib.request.Request(html.unescape(u), headers=hdr), timeout=25).read(); break
        except Exception: continue
    if not b: return None
    try:
        im=Image.open(io.BytesIO(b)).convert("RGB"); im.thumbnail((360,360)); o=io.BytesIO(); im.save(o,"JPEG",quality=48,optimize=True); return "data:image/jpeg;base64,"+base64.b64encode(o.getvalue()).decode()
    except Exception: return None
with cf.ThreadPoolExecutor(24) as ex: data=dict(zip(urls, ex.map(fetch, urls)))
def repl(m):
    d=data.get(m.group(1)); return f'<img src="{d}">' if d else ''
emb=re.sub(r'<img loading="lazy" src="([^"]+)"[^>]*>', repl, page)
def cap(m):
    ims=re.findall(r'<img src="[^"]+">', m.group(0))[:8]; return '<div class="imgs">'+''.join(ims)+'</div>'
emb=re.sub(r'<div class="imgs">.*?</div>', cap, emb, flags=re.S)
emb=emb.replace('<div class="imgs"></div>','<div class="imgs"><div class="noimg">no image found</div></div>')
# FULL version: download every photo once into out/photos/<venue>/ (max 1400px) and reference local files, so nothing is hotlink-blocked
import hashlib
os.makedirs("out/photos", exist_ok=True)
def slug(n): return re.sub(r"[^a-z0-9]+","-",n.lower()).strip("-")[:60]
def save_local(args):
    u, folder, idx = args
    if u.startswith("LOCAL:"): return u, u[6:]
    path=f"out/photos/{folder}/{idx:02d}.jpg"
    if os.path.exists(path): return u, path
    b=None
    for hdr in ({"User-Agent":"Mozilla/5.0","Referer":"https://www.google.com/"},{"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/126 Safari/537.36","Accept":"image/*,*/*"}):
        try: b=urllib.request.urlopen(urllib.request.Request(html.unescape(u), headers=hdr), timeout=25).read(); break
        except Exception: continue
    if not b: return u, None
    try:
        im=Image.open(io.BytesIO(b)).convert("RGB")
        if im.width<400: return u, None
        im.thumbnail((1400,1400)); os.makedirs(f"out/photos/{folder}", exist_ok=True); im.save(path,"JPEG",quality=76,optimize=True); return u, path
    except Exception: return u, None
jobs=[]
for m in re.finditer(r'<article class="v" data-fit="\d+" data-name="([^"]+)"[^>]*>(.*?)</article>', page, re.S):
    folder=slug(html.unescape(m.group(1)))
    for idx,u in enumerate(re.findall(r'<img loading="lazy" src="([^"]+)"', m.group(2))): jobs.append((u, folder, idx))
with cf.ThreadPoolExecutor(24) as ex: local=dict(ex.map(save_local, jobs))
def repl_local(m):
    p=local.get(m.group(1)); return f'<img loading="lazy" src="{p[4:]}" onclick="openLb(this)">' if p else ''
full=re.sub(r'<img loading="lazy" src="([^"]+)"[^>]*>', repl_local, page)
full=full.replace('<div class="imgs"></div>','<div class="imgs"><div class="noimg">no image found</div></div>')
LEAF_HEAD='<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"><script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script><style>.zil{display:grid;grid-template-columns:1fr 330px;gap:12px;height:86vh;position:relative}#lmap{height:100%;border:1px solid var(--rule);border-radius:6px;background:var(--track)}#side{overflow-y:auto;border:1px solid var(--rule);border-radius:6px;background:var(--surface)}#side .sh{padding:10px 12px;font-size:13px;color:var(--muted);border-bottom:1px solid var(--rule);position:sticky;top:0;background:var(--surface)}#side .si{display:grid;grid-template-columns:78px 1fr;gap:10px;padding:8px 12px;border-bottom:1px solid var(--rule);cursor:pointer;align-items:center}#side .si:hover{background:var(--track)}#side .si img{width:78px;height:58px;object-fit:cover;border-radius:4px;display:block}#side .si b{font-size:14px;display:block;line-height:1.25}#side .si span{font-size:12px;color:var(--muted)}#side .si.yes{border-left:4px solid var(--accent)}#side .si.maybe{border-left:4px solid var(--flag)}#side .si.no{border-left:4px solid #c0392b}.leaflet-tooltip{font-family:Karla,sans-serif}@media(max-width:800px){.zil{grid-template-columns:1fr;height:auto}#lmap{height:60vh}#side{max-height:40vh}}</style>'
LEAF_MAP='<div id="map" hidden><div class="zil"><div id="lmap"></div><div id="side"><div class="sh" id="sh"></div><div id="sidelist"></div></div>PVPANEL</div></div>'
pv_m=re.search(r'<div id="pv">.*?</div></div></div>', full, re.S)
pv_html=pv_m.group(0)[:-len("</div>")] if pv_m else ""  # keep #pv, drop the closing of .mapwrap
full=re.sub(r'<div id="map" hidden>.*?</div></div></div>', LEAF_MAP.replace("PVPANEL", pv_html), full, count=1, flags=re.S)
full=full.replace('<style>', LEAF_HEAD+'<style>',1)
LEAF_JS=r"""
let LM=null,MK={};
function mcol(n){const vt=votes[n];return vt=='yes'?'#2B5F6B':vt=='maybe'?'#C08A5C':vt=='no'?'#c0392b':'#63757A'}
function drawMap(){if(!LM){LM=L.map('lmap',{zoomControl:true}).setView([53.3,-8.6],7);L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap'}).addTo(LM);V.forEach(v=>{if(v.lat==null)return;const m=L.circleMarker([v.lat,v.lng],{radius:6+v.fit/14,weight:v.b?3:1.5,color:'#1B2A2E',fillOpacity:.85,fillColor:mcol(v.n)}).addTo(LM);m.bindTooltip(v.n+' · fit '+v.fit);m.on('click',()=>preview(v));MK[v.n]=m});LM.on('moveend',sideList)}
 restyle();setTimeout(()=>{LM.invalidateSize();sideList()},60)}
function restyle(){Object.entries(MK).forEach(([n,m])=>{m.setStyle({fillColor:mcol(n),fillOpacity:votes[n]=='no'?.45:.85});const show=visible.has(n);if(show&&!LM.hasLayer(m))m.addTo(LM);if(!show&&LM.hasLayer(m))LM.removeLayer(m)})}
function syncMap(){if(LM){restyle();sideList()}}
function thumb(n){const el=cardOf(n);const im=el&&el.querySelector('.imgs img');return im?im.src:''}
function sideList(){if(!LM)return;const b=LM.getBounds();const inv=V.filter(v=>v.lat!=null&&visible.has(v.n)&&b.contains([v.lat,v.lng])).sort((a,c)=>c.fit-a.fit);document.getElementById('sh').textContent=inv.length+' venues in view · zoom or drag the map';document.getElementById('sidelist').innerHTML=inv.map(v=>`<div class="si ${votes[v.n]||''}" onclick='flyTo(${JSON.stringify(v.n)})'><img src="${thumb(v.n)}" onerror="this.style.visibility='hidden'"><div><b>${v.n}</b><span>${v.county}${v.d?' · '+v.d+'h from Dublin':''}${v.rooms?' · '+v.rooms+' rooms':''} · fit ${v.fit}</span></div></div>`).join('')}
function flyTo(n){const v=V.find(x=>x.n==n);if(!v)return;LM.setView([v.lat,v.lng],Math.max(LM.getZoom(),12));preview(v)}
function showOnMap(n){setView('map');setTimeout(()=>{const v=V.find(x=>x.n==n);if(v&&v.lat!=null){LM.setView([v.lat,v.lng],13);preview(v)}},120);window.scrollTo({top:0,behavior:'smooth'})}
const oldPaint2=paint;paint=function(){oldPaint2();if(LM){restyle();sideList()}};
"""
# replace the SVG drawMap/showOnMap in the full version with the Leaflet ones (append after; later definitions win)
full=full.replace('paint();let sv=', LEAF_JS+'\npaint();let sv=')
open("out/venue-shortlist-full.html","w").write(full)
print("full version: photos saved", sum(1 for v in local.values() if v), "of", len(jobs), "into out/photos/")
def cap5(m):
    ims=re.findall(r'<img src="[^"]+">', m.group(0))[:5]; return '<div class="imgs">'+''.join(ims)+'</div>'
web=re.sub(r'<div class="imgs">.*?</div>', cap5, emb, flags=re.S).replace("Venue Swipe</title>","Venue Swipe</title>")
open("out/venue-shortlist.html","w").write(web)
print("web MB", round(len(web)/1e6,2))
print("embedded MB", round(len(emb)/1e6,2), "images", sum(1 for v in data.values() if v), "of", len(urls))
print("wrote venue-shortlist.html with", len(keep), "cards; csv rows", len(keep))
