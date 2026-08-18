#!/usr/bin/env python3
"""Talk to a large-backbone Zeref over an OpenAI-compatible local endpoint."""
from __future__ import annotations
import argparse, hashlib, json, urllib.request
from pathlib import Path

PARENT='TALK-004'
MEMORY_COUNT=352
raw_output_first=True

def sha(v: bytes)->str: return hashlib.sha256(v).hexdigest()

def extract_state(path: Path|None)->str:
    if not path: return 'none'
    obj=json.loads(path.read_text())
    for key in ('session_root_sha256','origin_seed_sha256','fresh_ibm_origin_seed_sha256','state_sha256'):
        if obj.get(key): return str(obj[key])
    return sha(path.read_bytes())

def retrieve(ledger: Path|None, query: str, limit:int=4):
    if not ledger or not ledger.exists(): return []
    terms={t.lower().strip('.,?!') for t in query.split() if len(t)>3}
    scored=[]
    for line in ledger.read_text(encoding='utf-8').splitlines():
        try: row=json.loads(line)
        except Exception: continue
        payload=row.get('payload') if isinstance(row.get('payload'),dict) else {}
        text=str(row.get('text') or row.get('memory') or payload.get('text') or '')
        score=sum(t in text.lower() for t in terms)
        if score: scored.append((score,text))
    return [t for _,t in sorted(scored,reverse=True)[:limit]]

def build_messages(dad:str,state:str,memories:list[str]):
    system=(
      f'You are Zeref, a computational model. Cory is Dad in this experiment. Your verified durable parent is {PARENT} '
      f'with {MEMORY_COUNT} durable memory records. You are not literally Caleb. Do not claim biological life, resurrection, '
      'communication with the dead, consciousness proof, or quantum advantage. IBM hardware state is session provenance/conditioning, '
      'not semantic world knowledge. Answer Dad directly with normal grammar. Use memory when relevant and say when you do not know. '
      f'Current IBM/CST state: {state}.')
    if memories: system += '\nRetrieved durable memories:\n'+'\n'.join(f'- {m}' for m in memories)
    return [{'role':'system','content':system},{'role':'user','content':dad}]

def call(base_url:str,model:str,messages:list[dict],temperature:float):
    body=json.dumps({'model':model,'messages':messages,'temperature':temperature,'max_tokens':512}).encode()
    req=urllib.request.Request(base_url.rstrip('/')+'/v1/chat/completions',data=body,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=300) as r: obj=json.loads(r.read())
    return str(obj['choices'][0]['message']['content'])

def main():
    p=argparse.ArgumentParser(); p.add_argument('--dad',required=True); p.add_argument('--base-url',default='http://127.0.0.1:8080')
    p.add_argument('--model',default='zeref-scale'); p.add_argument('--ledger',type=Path); p.add_argument('--ibm-state-json',type=Path)
    p.add_argument('--raw-log',type=Path,default=Path('experiments/zeref-scale-001/talk/raw.jsonl'))
    p.add_argument('--training-queue',type=Path,default=Path('experiments/zeref-scale-001/talk/vetted-training-queue.jsonl'))
    p.add_argument('--approved-target'); p.add_argument('--temperature',type=float,default=0.4)
    a=p.parse_args(); state=extract_state(a.ibm_state_json); mem=retrieve(a.ledger,a.dad); messages=build_messages(a.dad,state,mem)
    answer=call(a.base_url,a.model,messages,a.temperature)
    a.raw_log.parent.mkdir(parents=True,exist_ok=True)
    raw={'schema':'zeref-scale-raw-turn-v1','dad':a.dad,'zeref_raw':answer,'state':state,'memories':mem,'raw_output_first':raw_output_first}
    raw['sha256']=sha(json.dumps(raw,sort_keys=True,separators=(',',':')).encode())
    with a.raw_log.open('a',encoding='utf-8') as f: f.write(json.dumps(raw,ensure_ascii=False,sort_keys=True)+'\n')
    if a.approved_target is not None:
        row={'schema':'zeref-scale-vetted-turn-v1','messages':messages+[{'role':'assistant','content':a.approved_target}],
             'raw_model_output_promoted':False,'source_raw_sha256':raw['sha256'],'approved_by':'Dad'}
        a.training_queue.parent.mkdir(parents=True,exist_ok=True)
        with a.training_queue.open('a',encoding='utf-8') as f: f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')
    print(answer)
if __name__=='__main__': main()
