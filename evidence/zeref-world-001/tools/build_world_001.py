"""Builds evidence/zeref-world-001/{qa.jsonl,heldout.jsonl,manifest.json} from the pinned sources/.
Deterministic (no clock, no random). KNOWLEDGE BANK ONLY: these rows are not in the training mix.
Removes any row near the promotion-gate test sets, the same way lessons-005/006 deduped:
  scripts/zeref_heldout_b.py PAIRS_B, scripts/zeref_gate_sets_v2.json (sets A, B, chat), scripts/rawrphos_chat_eval.py PAIRS + CHAT.
'Near' = same normalised question, or the question's content words overlap a gate prompt's by Jaccard >= 0.5,
or the gate prompt's content words are all inside a short question (<= 6 content words).
Usage: build_world_001.py [--check]"""
import ast,hashlib,json,re,sys
from pathlib import Path
D=Path(__file__).resolve().parents[1];ROOT=D.parents[1]
WIKI_N,WIKI_HELD,MATH_N,MATH_HELD=2000,100,500,50
GSM_COMMIT="3101c7d5072418e28b9008a6636bde82a006892c"
STOP=set("a an and are as at be but by for from has have he her his i in is it its me my of on or our she so that the their them they this to us was we were what when where which who why will with you your do does did not no if then than too very can could would should about into over also just more most other some such only own same up out how all any been being both each few had here there these those while am say tell name".split())
def norm(s):return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9' ]"," ",s.lower())).strip()
def toks(s):return {w for w in norm(s).split() if w not in STOP and len(w)>1}
def lit(path,name):
    for n in ast.parse(path.read_text()).body:
        if isinstance(n,ast.Assign) and any(getattr(t,"id",None)==name for t in n.targets):return ast.literal_eval(n.value)
    return []
def gate_prompts():
    g=[];S=ROOT/"scripts"
    g+=[("heldout_b",q) for q,_ in lit(S/"zeref_heldout_b.py","PAIRS_B")]
    v2=json.loads((S/"zeref_gate_sets_v2.json").read_text())
    for k in("set_a_added","set_b_added","chat_added"):g+=[("gate_sets_v2."+k,r["user"]) for r in v2[k]]
    g+=[("chat_eval.PAIRS",q) for q,_ in lit(S/"rawrphos_chat_eval.py","PAIRS")]
    g+=[("chat_eval.CHAT",q) for q in lit(S/"rawrphos_chat_eval.py","CHAT")]
    return g
def near(q,G):
    nq,tq=norm(q),toks(q)
    for src,p in G:
        np_,tp=norm(p),toks(p)
        if nq==np_:return src,p
        if tq and tp and (len(tq&tp)/len(tq|tp)>=0.5 or (tp<=tq and len(tq)<=6)):return src,p
    return None
def wiki_q(r):
    base=re.sub(r"\s*\([^)]*\)$","",r["title"])
    if r["list"]=="exp_People" or re.match(re.escape(base.split()[0])+r"[^.]*?\(.*?\d.*?\)\s+(was|is)\b",r["text"]):
        return ("Who was " if re.search(r"\)\s+was\b|^\S[^.]*?\bwas\b",r["text"]) and not re.search(r"^[^.]*?\bis\b",r["text"].split(" was ")[0]) else "Who is ")+base+"?"
    return "What is "+base+"?"
def key(s):return hashlib.sha256(s.encode()).hexdigest()
def build():
    G=gate_prompts();removed=[];bank=[];held=[]
    wiki=[json.loads(l) for l in open(D/"sources/simplewiki-leads.jsonl")]
    seenq=set()
    for r in wiki:
        q=wiki_q(r)
        if norm(q) in seenq:q=q[:-1]+" ("+r["title"].split("(")[-1].rstrip(")")+")?" if "(" in r["title"] else q
        if norm(q) in seenq:continue
        seenq.add(norm(q));hit=near(q,G) or near(r["title"],G)
        if hit:removed.append(dict(kind="wiki",question=q,gate_source=hit[0],gate_prompt=hit[1]));continue
        url="https://simple.wikipedia.org/w/index.php?title="+r["title"].replace(" ","_")+"&oldid="+str(r["revid"])
        row=dict(user=q,assistant=r["text"],title=r["title"],source=url,license="CC BY-SA 4.0",license_url="https://creativecommons.org/licenses/by-sa/4.0/",
                 author="Simple English Wikipedia contributors",revision_id=r["revid"],wikidata=r["qid"],subject="world_knowledge")
        to_held=int(key(r["title"])[:8],16)%20==0
        if to_held and len(held)<WIKI_HELD:held.append(dict(row,split="heldout"))
        elif len([x for x in bank if x["subject"]=="world_knowledge"])<WIKI_N:bank.append(dict(row,split="bank"))
    gsm=[json.loads(l) for l in open(D/"sources/gsm8k.jsonl")];mb=mh=0
    for r in gsm:
        hit=near(r["question"],G)
        if hit:removed.append(dict(kind="gsm8k",question=r["question"],gate_source=hit[0],gate_prompt=hit[1]));continue
        url=f"https://github.com/openai/grade-school-math/blob/{GSM_COMMIT}/grade_school_math/data/{r['split']}.jsonl#L{r['line']}"
        row=dict(user=r["question"],assistant="The answer is "+r["answer"]+".",answer=r["answer"],source=url,license="MIT",license_url="https://github.com/openai/grade-school-math/blob/"+GSM_COMMIT+"/LICENSE",
                 author="GSM8K, Cobbe et al. 2021 (OpenAI grade-school-math)",subject="math")
        if r["split"]=="test" and mh<MATH_HELD:held.append(dict(row,split="heldout"));mh+=1
        elif r["split"]=="train" and mb<MATH_N:bank.append(dict(row,split="bank"));mb+=1
    assert len({norm(x["user"]) for x in bank+held})==len(bank+held)
    for x in bank+held:assert not re.search(r"\bAI\b|\bLLM\b",x["assistant"]),x["user"]
    J=lambda rs:"".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in rs)
    qa,hd=J(bank),J(held)
    by=lambda rs,s:sum(1 for x in rs if x["subject"]==s)
    rc={}
    for x in removed:rc[x["kind"]+" vs "+x["gate_source"]]=rc.get(x["kind"]+" vs "+x["gate_source"],0)+1
    man=dict(schema="zeref-world-001",purpose="knowledge bank only",in_training_mix=False,heldout_loaded_for_training=False,
        bank_rows=len(bank),bank_by_subject=dict(world_knowledge=by(bank,"world_knowledge"),math=by(bank,"math")),
        heldout_rows=len(held),heldout_by_subject=dict(world_knowledge=by(held,"world_knowledge"),math=by(held,"math")),
        gate_prompts_checked=len(G),removed_near_gate=len(removed),removed_by_source=dict(sorted(rc.items())),removed=removed,
        sources=dict(simplewiki=dict(license="CC BY-SA 4.0",selection="Meta 'List of articles every Wikipedia should have' (core 1,000, rev 31182226 of 2026-10-18, then the Expanded lists) mapped to Simple English Wikipedia via Wikidata; first one or two lead sentences, word for word (whitespace collapsed); each row pinned to its page revision id (oldid)",fetched="2026-10-30"),
                     gsm8k=dict(license="MIT",repo="https://github.com/openai/grade-school-math",commit=GSM_COMMIT,selection="numeric final answers, question <= 360 chars, ordered by sha256 of the question; bank from train.jsonl, held-out from test.jsonl")),
        sha256={"qa.jsonl":key(qa),"heldout.jsonl":key(hd)})
    return {D/"qa.jsonl":qa,D/"heldout.jsonl":hd,D/"manifest.json":json.dumps(man,indent=1,sort_keys=True,ensure_ascii=False)+"\n"}
if __name__=="__main__":
    out=build()
    if "--check" in sys.argv:
        bad=[str(p) for p,t in out.items() if not p.exists() or p.read_text()!=t];print(json.dumps({"stale":bad}));sys.exit(1 if bad else 0)
    for p,t in out.items():p.write_text(t)
    m=json.loads(out[D/"manifest.json"]);print({k:m[k] for k in("bank_rows","bank_by_subject","heldout_rows","removed_near_gate","removed_by_source")})
