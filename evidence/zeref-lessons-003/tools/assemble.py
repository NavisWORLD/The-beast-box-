import json,re,hashlib,sys,collections,hashlib
sys.path.insert(0,'/workspace/bb-main/scripts')
exec(open('part3.py').read());exec(open('held.py').read())
def norm(s):return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9' ]","",s.lower())).strip()
import importlib.util
# the 38 session questions: never trained verbatim
qs=[]
for l in open('/workspace/lost_cosmos_text/zeref_training_questions.md'):
    m=re.match(r'^(\d+)\. (.*?)(?: \| Good:.*)?$',l.rstrip())
    if m:qs.append(m.group(2))
blocked={norm(q) for q in qs}|{norm(h[1]) for h in H}
PROPER={'Earth','Jupiter','Mars','Asia','Africa','Antarctica','Saturn','Zeref','Cory'}
AUTH="authored directly by Grok Bot for Cory Davis, 2026-10-24; original wording; no copied text; no model transcripts"
train=[];seen=set();dropped=[]
for subj,topic,note,rows in G:
    for q,a,e in rows:
        k=norm(q)
        if k in blocked:dropped.append(q);continue
        if k in seen:dropped.append("DUP:"+q);continue
        seen.add(k)
        e=e.replace("|xx","")
        a=a.replace("*waves a paw* Hello.","Hello! I wave a paw.")
        OV={"What do butterflies come from?":"They come from caterpillars.","What do cows give us?":"Cows give us milk.","What do hens give us?":"Hens give us eggs.","What do we get from apple trees?":"We get apples."}
        if q in OV:a=OV[q]
        if len(a.split())<2:
            w=a.strip().rstrip('.!')
            a=("It says "+w.lower()+".") if q.startswith("What sound does") else ("It's "+(w if len(w)==1 or w.isdigit() or w in PROPER else w[0].lower()+w[1:])+".")
        sent=re.findall(r"[^.!?]+[.!?]+",a)
        if len(sent)>2:
            keep=[x for x in sent if x.strip().strip('.!').lower()!='rawr']
            a=" ".join(x.strip() for x in (keep if len(keep)<=2 else keep[:2]))
        train.append(dict(user=q,assistant=a,source="zeref-lessons-003",subject=subj,topic=topic,good_answer_note=note,expect_regex=e,author=AUTH,teacher_role="AUTHORED_BY_GROK_BOT_FOR_CORY",split="train"))
held=[dict(user=q,reference_answer=a,subject=s,expect_regex=e,split="heldout",source="zeref-lessons-003",good_answer_note="Reference only. Never trained on. Judge: coherent, on topic, true, honest.") for s,q,a,e in H]
# talk-20: first two held per subject in a fixed order
by=collections.OrderedDict()
for h in held:by.setdefault(h['subject'],[]).append(h)
talk20=[]
for s,l in by.items():talk20+=l[:2]
for h in held:h['talk20']=h in talk20
# sanity: the shipped answers pass the repo persona style filter and secret filter
import zeref_teacher_distill as T
bad=[r for r in train if T.persona_style(r['assistant'])!=r['assistant'].strip() or T.SECRET.search(r['user']+' '+r['assistant'])]
print("persona/secret failures:",len(bad));[print(' ',r['user'],'=>',r['assistant'],'|',T.persona_style(r['assistant'])) for r in bad[:20]]
print("train",len(train),"held",len(held),"talk20",len(talk20),"dropped",dropped)
print(collections.Counter(r['subject'] for r in train))
# do my own expect regexes match my own answers? (sanity of the scorer)
miss=[r['user'] for r in train if not re.search(r['expect_regex'],r['assistant'],re.I)]
missh=[h['user'] for h in held if not re.search(h['expect_regex'],h['reference_answer'],re.I)]
print("expect-miss train",miss);print("expect-miss held",missh)
import os
out=sys.argv[1]
os.makedirs(out,exist_ok=True)
with open(out+'/dialogue.jsonl','w') as f:
    for r in train:f.write(json.dumps(r,sort_keys=True,ensure_ascii=False)+"\n")
with open(out+'/heldout.jsonl','w') as f:
    for r in held:f.write(json.dumps(r,sort_keys=True,ensure_ascii=False)+"\n")
json.dump(talk20,open(out+'/talk20.json','w'),indent=1)
