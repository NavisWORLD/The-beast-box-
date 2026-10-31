"""Pins the inputs (run once after fetch_wiki.py). Deterministic: same raw files -> same bytes.
Writes sources/simplewiki-leads.jsonl (first one or two lead sentences, word for word, with page revision id)
and sources/gsm8k.jsonl (question + final answer, word for word, with file line number). No random."""
import json,re,sys,hashlib
from pathlib import Path
RAW=Path(sys.argv[1]);OUT=Path(__file__).resolve().parents[1]/"sources"
GSM_COMMIT="3101c7d5072418e28b9008a6636bde82a006892c"
ABBR=re.compile(r"(?:\b(?:c|ca|St|Mr|Mrs|Dr|Jr|Sr|No|vs|etc|e\.g|i\.e|approx|Mt|Ft|Gen|Lt|Col|Inc|Co|Ltd|U\.S|U\.K|D\.C|B\.C|A\.D|a\.m|p\.m)|\b[A-Z])\.$")
def sentences(text):
    t=re.sub(r"\s+"," ",text.split("\n")[0]).strip(); out=[];cur=""
    for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])",t):
        cur=(cur+" "+part).strip() if cur else part
        if ABBR.search(cur): continue
        out.append(cur);cur=""
    if cur:out.append(cur)
    return out
JUNK=re.compile(r"\(\s*\)|\(\s*[;,:]|:\s*,|\[|\]|\{|\}|\s,|  |\.\.|;\s*\)")
BLOCK=re.compile(r"\b(sex|sexual|sexually|porn\w*|rape\w*|erotic\w*|prostitut\w*|nude|nudity|masturbat\w*|suicide|torture\w*|genital\w*|penis|vagina|incest|pedophil\w*)\b",re.I)
stats={"leads_read":0,"no_text_or_disambiguation":0,"lead_markup_artifacts":0,"blocked_topic_words":0,"too_short_or_long":0,"calls_ai_or_llm":0,"dup_title":0}
rows=[];seen=set()
for l in open(RAW/"simplewiki_leads.jsonl"):
    try:r=json.loads(l)
    except Exception:continue
    stats["leads_read"]+=1
    if r["disambig"] or not r["extract"].strip():stats["no_text_or_disambiguation"]+=1;continue
    s=sentences(r["extract"])
    if not s:stats["no_text_or_disambiguation"]+=1;continue
    text=s[0]
    if len(s)>1 and len(text)+1+len(s[1])<=320:text=text+" "+s[1]
    if JUNK.search(text):stats["lead_markup_artifacts"]+=1;continue
    if BLOCK.search(text+" "+r["title"]):stats["blocked_topic_words"]+=1;continue
    if not(40<=len(text)<=400) or not text.endswith((".", "!", "?")):stats["too_short_or_long"]+=1;continue
    if re.search(r"\bAI\b|\bLLM\b",text):stats["calls_ai_or_llm"]+=1;continue
    if r["title"].lower() in seen:stats["dup_title"]+=1;continue
    seen.add(r["title"].lower())
    rows.append(dict(qid=r["qid"],list=r["list"].replace(".txt",""),title=r["title"],revid=r["revid"],rev_ts=r["rev_ts"],text=text))
    if len(rows)>=2600:break
OUT.mkdir(exist_ok=True)
(OUT/"simplewiki-leads.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in rows))
def gsm(split,n):
    out=[]
    for i,l in enumerate(open(RAW/f"gsm8k_{split}.jsonl"),1):
        r=json.loads(l);fin=r["answer"].split("####")[-1].strip()
        if not re.fullmatch(r"-?[0-9][0-9,]*(\.[0-9]+)?",fin) or len(r["question"])>360:continue
        out.append(dict(split=split,line=i,question=r["question"].strip(),answer=fin,key=hashlib.sha256(r["question"].encode()).hexdigest()))
    out.sort(key=lambda x:x["key"]);return [{k:v for k,v in x.items() if k!="key"} for x in out[:n]]
g=gsm("train",620)+gsm("test",80)
(OUT/"gsm8k.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in g))
(OUT/"prepare-stats.json").write_text(json.dumps(dict(stats,kept_leads=len(rows),gsm8k_rows=len(g),gsm8k_commit=GSM_COMMIT),indent=1,sort_keys=True)+"\n")
print(stats,len(rows),len(g))
