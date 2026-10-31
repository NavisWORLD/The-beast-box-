"""Fetch step (network). Resolves Meta 'List of articles every Wikipedia should have' (1,000 core, then Expanded)
Wikidata items to Simple English Wikipedia titles, then saves each article's plain-text lead at its current revision id."""
import json,re,time,urllib.request,urllib.parse,sys
UA={"User-Agent":"BeastBoxBank/1.0 (NavisWORLD/The-beast-box-; knowledge bank build)"}
def get(url,params):
    u=url+"?"+urllib.parse.urlencode(params)
    for i in range(5):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60))
        except Exception as e: time.sleep(3*(i+1))
    raise SystemExit("fail "+u)
R=sys.argv[1]
order=["meta1000.txt"]+["exp_%s.txt"%p for p in ["Geography","Physical_sciences","Biology_and_health_sciences","Technology","History","Arts","Society_and_social_sciences","Mathematics","Philosophy_and_religion","People"]]
qs=[];seen=set()
for f in order:
    for q in re.findall(r'Q[0-9]+',open(f"{R}/{f}").read()):
        if q not in seen: seen.add(q); qs.append((q,f))
print("qids",len(qs))
titles=[]
for i in range(0,len(qs),50):
    chunk=qs[i:i+50]
    d=get("https://www.wikidata.org/w/api.php",dict(action="wbgetentities",ids="|".join(q for q,_ in chunk),props="sitelinks",sitefilter="simplewiki",format="json"))
    for q,f in chunk:
        sl=d.get("entities",{}).get(q,{}).get("sitelinks",{}).get("simplewiki")
        if sl and ":" not in sl["title"]: titles.append((q,f,sl["title"]))
print("simple titles",len(titles))
out=open(f"{R}/simplewiki_leads.jsonl","w")
for i in range(0,len(titles),20):
    chunk=titles[i:i+20]
    d=get("https://simple.wikipedia.org/w/api.php",dict(action="query",prop="extracts|revisions|pageprops",exintro=1,explaintext=1,exlimit=20,rvprop="ids|timestamp",titles="|".join(t for _,_,t in chunk),format="json",formatversion=2,redirects=1))
    pages={p["title"]:p for p in d["query"]["pages"]}
    norm={n["from"]:n["to"] for n in d["query"].get("normalized",[])+d["query"].get("redirects",[])}
    for q,f,t in chunk:
        tt=norm.get(t,t); tt=norm.get(tt,tt); p=pages.get(tt)
        if not p or "missing" in p: continue
        out.write(json.dumps(dict(qid=q,list=f,title=p["title"],pageid=p["pageid"],revid=p["revisions"][0]["revid"],rev_ts=p["revisions"][0]["timestamp"],disambig="disambiguation" in p.get("pageprops",{}),extract=p.get("extract","")),ensure_ascii=False)+"\n")
    time.sleep(0.2)
out.close()
