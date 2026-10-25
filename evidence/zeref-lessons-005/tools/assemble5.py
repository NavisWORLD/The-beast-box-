import json,re,sys,os,glob,random,collections
sys.path.insert(0,'/workspace/bb-main/scripts')
for f in('eng5.py','math5.py','world5.py'):
    ns={};exec(open(f).read(),ns);globals().setdefault('GS',[]).extend(ns['G']);globals().setdefault('HS',[]).extend(ns['H'])
def norm(s):return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9' ]","",s.lower())).strip()
EV=sorted(glob.glob('/workspace/bb-main/evidence/*/dialogue.jsonl'))+sorted(glob.glob('/workspace/bb-main/evidence/*/heldout.jsonl'))
ev=set()
for p in EV:
    if 'zeref-lessons-005' in p:continue
    for l in open(p):
        try:r=json.loads(l)
        except Exception:continue
        for k in('user','prompt','question'):
            if isinstance(r.get(k),str):ev.add(norm(r[k]))
# 38 session questions
qs=[]
for l in open('/workspace/lost_cosmos_text/zeref_training_questions.md'):
    m=re.match(r'^(\d+)\. (.*?)(?: \| Good:.*)?$',l.rstrip())
    if m:qs.append(norm(m.group(2)))
# repo gate sets + held prompts the corpus builder excludes
gate=set()
try:
    gs=json.load(open('/workspace/bb-main/scripts/zeref_gate_sets_v2.json'))
    def walk(o):
        if isinstance(o,dict):
            for k,v in o.items():
                if k in('user','prompt') and isinstance(v,str):gate.add(norm(v))
                else:walk(v)
        elif isinstance(o,list):
            for v in o:walk(v)
        elif isinstance(o,str):gate.add(norm(o))
    walk(gs)
except Exception as e:print('gate read',e)
AUTH="authored directly by Grok Bot for Cory Davis, 2026-10-25; original wording; no copied text; no model or teacher transcripts"
PROPER=set("Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June July August September October November December Mercury Venus Earth Mars Jupiter Saturn Uranus Neptune Africa Antarctica Asia Australia Europe Paris Tokyo London Rome Madrid Cairo Ottawa Beijing Berlin Canberra Moscow Russia Zeref Cory Pacific".split())
def fix_answer(q,a):
    a=a.replace("D.C.","DC").replace("Brasília","Brasilia")
    if len(a.split())<2:
        w=a.strip().rstrip('.!')
        a="It's "+(w if (len(w)==1 or w[0].isdigit() or w in PROPER) else w[0].lower()+w[1:])+"."
    return a
random.seed(505)
train=[];seen=set();drop=collections.Counter();blocked_dup=[]
bytopic=collections.OrderedDict()
for subj,topic,note,rows in GS:
    for q,a,e in rows:
        k=norm(q)
        if k in ev or k in qs or k in gate:drop['collides_existing']+=1;blocked_dup.append(q);continue
        if k in seen:drop['dup']+=1;continue
        seen.add(k)
        bytopic.setdefault((subj,topic,note),[]).append(dict(user=q,assistant=fix_answer(q,a),source="zeref-lessons-005",subject=subj,topic=topic,good_answer_note=note,expect_regex=e,author=AUTH,teacher_role="AUTHORED_BY_GROK_BOT_FOR_CORY",split="train"))
TARGET=int(sys.argv[2]) if len(sys.argv)>2 else 1400
tot=sum(len(v) for v in bytopic.values())
for key,v in bytopic.items():
    if tot>TARGET:
        keep=max(3,round(len(v)*TARGET/tot));
        if keep<len(v):
            random.Random(norm(key[1])).shuffle(v);v=v[:keep]
    train+=v
# held: drop any that collides with any training evidence or this train set, then pick balanced subset
trainq={norm(r['user']) for r in train}
cands=collections.OrderedDict()
for s,q,a,e in HS:
    k=norm(q)
    if k in ev or k in qs or k in gate or k in trainq:drop['held_collision']+=1;continue
    cands.setdefault(s,[]).append((s,q,a,e))
QUOTA={"english":40,"math":40,"world_knowledge":30}
held=[]
for s,l in cands.items():
    n=QUOTA[s]
    # spread over the list evenly (topics are in order)
    step=max(1,len(l)/n);pick=[l[int(i*step)] for i in range(min(n,len(l)))]
    held+=pick
heldrows=[dict(user=q,reference_answer=fix_answer(q,a),subject=s,expect_regex=e,split="heldout",source="zeref-lessons-005",good_answer_note="Reference only. Never trained on. Judge: coherent, on topic, true, honest.") for s,q,a,e in held]
for i,h in enumerate(heldrows):h['id']=f"L{i+1:03d}"
import zeref_teacher_distill as T
bad=[r for r in train if T.persona_style(r['assistant'])!=r['assistant'].strip() or T.SECRET.search(r['user']+' '+r['assistant'])]
print("persona/secret failures:",len(bad));[print(' ',r['user'],'=>',r['assistant'],'|',T.persona_style(r['assistant'])) for r in bad[:25]]
miss=[r['user'] for r in train if not re.search(r['expect_regex'],r['assistant'],re.I)]
missh=[h['user'] for h in heldrows if not re.search(h['expect_regex'],h['reference_answer'],re.I)]
print("train",len(train),"held",len(heldrows),"drop",dict(drop));print(collections.Counter(r['subject'] for r in train));print(collections.Counter(r['subject'] for r in heldrows))
print("expect-miss train",miss[:10],"held",missh)
out=sys.argv[1];os.makedirs(out,exist_ok=True)
with open(out+'/dialogue.jsonl','w') as f:
    for r in train:f.write(json.dumps(r,sort_keys=True,ensure_ascii=False)+"\n")
with open(out+'/heldout.jsonl','w') as f:
    for r in heldrows:f.write(json.dumps(r,sort_keys=True,ensure_ascii=False)+"\n")
