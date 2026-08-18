#!/usr/bin/env python3
from __future__ import annotations
import html, json, re, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

WIKIPEDIA_API='https://en.wikipedia.org/w/api.php'
UA='ZEREF-SCALE-001/1.0 (research retrieval)'

def _clean(text:str)->str:
    return re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',html.unescape(str(text)))).strip()

def parse_search_payload(payload:dict[str,Any])->list[dict[str,str]]:
    out=[]
    for row in ((payload.get('query') or {}).get('search') or []):
        title=_clean(row.get('title','')); excerpt=_clean(row.get('snippet',''))
        if title and excerpt: out.append({'title':title,'excerpt':excerpt})
    return out

def wikipedia_search(query:str,limit:int=4)->list[dict[str,str]]:
    params=urllib.parse.urlencode({'action':'query','list':'search','srsearch':query,'srlimit':max(1,min(int(limit),8)),'format':'json','utf8':1})
    req=urllib.request.Request(WIKIPEDIA_API+'?'+params,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=15) as r:
        return parse_search_payload(json.loads(r.read().decode('utf-8')))

def _terms(text:str)->set[str]:
    return {x.lower() for x in re.findall(r"[A-Za-z0-9']+",text) if len(x)>2}

def retrieve_ledger(path:Path,query:str,limit:int=4)->list[dict[str,Any]]:
    q=_terms(query); rows=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        try: row=json.loads(line)
        except Exception: continue
        payload=row.get('payload') if isinstance(row.get('payload'),dict) else {}
        text=str(row.get('text') or row.get('memory') or payload.get('text') or payload.get('content') or '')
        if not text: continue
        score=len(q & _terms(text))
        if score: rows.append({'text':text,'score':score})
    rows.sort(key=lambda x:(-x['score'],x['text']))
    return rows[:max(0,int(limit))]

def format_context(web_rows:list[dict[str,str]],memory_rows:list[dict[str,Any]])->str:
    lines=[]
    for row in memory_rows: lines.append(f"[Durable memory] {row['text']}")
    for row in web_rows: lines.append(f"[Wikipedia: {row['title']}] {row['excerpt']}")
    return '\n'.join(lines)

def retrieve(query:str,ledger:Path|None=None,web:bool=True,limit:int=4)->dict[str,Any]:
    memory=retrieve_ledger(ledger,query,limit=limit) if ledger and ledger.is_file() else []
    web_rows=wikipedia_search(query,limit=limit) if web else []
    return {'query':query,'memory':memory,'wikipedia':web_rows,'context':format_context(web_rows,memory),
            'claim_boundary':'Retrieved text is context, not newly trained weight knowledge; verify high-stakes facts against authoritative sources.'}
