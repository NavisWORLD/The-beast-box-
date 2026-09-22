"""Explicit public inputs, provenance, pre-split deduplication and integrity."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re

LICENSES={'cc0-1.0','cc-by-4.0','cc-by-sa-3.0','cc-by-sa-4.0','mit','apache-2.0','cdla-sharing-1.0','public-domain'}
SECRET=re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk-[\w-]{16,}|gh[pousr]_[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16})\b|(?:api[_-]?key|password|secret|access[_-]?token)\s*[:=]\s*[\w/-]{8,}',re.I)
PRIVATE=re.compile(r'runtime[-_ ]?memory|private[-_ ]?memory|conversation[-_ ]?history|beastbox://',re.I)
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(x): return hashlib.sha256(x).hexdigest()
def shingles(text):
    words=re.findall(r'\w+',text.casefold())
    parts=[' '.join(words[i:i+5]) for i in range(max(1,len(words)-4))]
    return {int.from_bytes(hashlib.blake2b(p.encode(),digest_size=8).digest(),'little') for p in parts}
def signatures(parts):
    return [min(((v*a+b)%((1<<61)-1) for v in parts),default=0) for a,b in [(3,7),(11,19),(23,31),(41,47)]]

def build_corpus(records,output,seed=67,validation_fraction=.1,benchmark_texts=()):
    if not 0<validation_fraction<1: raise ValueError('invalid validation fraction')
    output=Path(output)
    if output.exists() and any(output.iterdir()): raise FileExistsError('corpus output must be empty')
    rows=[]; rejected=Counter()
    for r in records:
        text=r.get('text'); source=r.get('source'); license_=r.get('license','')
        if not isinstance(text,str) or not text.strip(): rejected['empty']+=1; continue
        text.encode('utf-8',errors='strict')
        if not isinstance(source,str) or not source or PRIVATE.search(source): rejected['private_or_missing_source']+=1; continue
        if not isinstance(license_,str) or license_.casefold() not in LICENSES: rejected['license']+=1; continue
        if SECRET.search(text): rejected['secret']+=1; continue
        row=dict(r); row['sha256']=sha(text.encode()); rows.append(row)
    rows.sort(key=lambda x:(x['sha256'],x['source']))
    accepted=[]; seen=set(); index=defaultdict(set); sets=[]
    benchmarks=[shingles(t) for t in benchmark_texts]
    for row in rows:
        if row['sha256'] in seen: rejected['duplicate']+=1; continue
        seen.add(row['sha256']); parts=shingles(row['text'])
        if any(len(parts&b)/max(1,len(parts|b))>=.8 for b in benchmarks): rejected['benchmark_overlap']+=1; continue
        sig=signatures(parts); candidates=set().union(*(index[(i,s)] for i,s in enumerate(sig)))
        if any(len(parts&sets[j])/max(1,len(parts|sets[j]))>=.95 for j in candidates): rejected['near_duplicate']+=1; continue
        j=len(accepted); accepted.append(row); sets.append(parts)
        for i,s in enumerate(sig): index[(i,s)].add(j)
    if len(accepted)<2: raise ValueError('not enough accepted documents')
    accepted.sort(key=lambda r:sha(f'{seed}:{r["sha256"]}'.encode()))
    n=max(1,min(len(accepted)-1,round(len(accepted)*validation_fraction)))
    splits={'train':accepted[n:],'validation':accepted[:n]}; output.mkdir(parents=True,exist_ok=True)
    files={}
    for name,values in splits.items():
        data=b''.join(canonical(r)+b'\n' for r in values); files[name+'.jsonl']=sha(data)
        (output/(name+'.jsonl')).write_bytes(data)
    manifest={'schema':'rawrphos-corpus-v1','seed':seed,'validation_fraction':validation_fraction,
        'document_counts':{k:len(v) for k,v in splits.items()},'files':files,'rejected':dict(rejected),
        'deduplication':'exact hash; four minhash candidate signatures + exact 5-word Jaccard>=.95; probabilistic recall',
        'secret_screen':'heuristic patterns; public explicit sources only','benchmark_documents':len(benchmarks),
        'benchmark_sha256':sha(canonical(sorted(sha(t.encode()) for t in benchmark_texts))),
        'sources':sorted({(r['source'],r.get('revision','unspecified'),r['license']) for r in accepted})}
    manifest['dataset_sha256']=sha(canonical(manifest)); (output/'manifest.json').write_bytes(canonical(manifest))
    return manifest

def load_corpus(directory):
    p=Path(directory); m=json.loads((p/'manifest.json').read_text()); unsigned=dict(m); digest=unsigned.pop('dataset_sha256')
    if sha(canonical(unsigned))!=digest: raise ValueError('corpus manifest hash mismatch')
    result={'manifest':m}
    for split in ('train','validation'):
        data=(p/(split+'.jsonl')).read_bytes()
        if sha(data)!=m['files'][split+'.jsonl']: raise ValueError('corpus split hash mismatch')
        result[split]=[json.loads(line) for line in data.splitlines()]
        if any(sha(r['text'].encode())!=r['sha256'] for r in result[split]): raise ValueError('document hash mismatch')
    if {r['sha256'] for r in result['train']} & {r['sha256'] for r in result['validation']}: raise ValueError('split overlap')
    return result

def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--output',required=True)
    p.add_argument('--seed',type=int,default=67); p.add_argument('--benchmark-jsonl')
    a=p.parse_args(); benchmarks=[]
    if a.benchmark_jsonl:
        benchmarks=[json.loads(line)['text'] for line in Path(a.benchmark_jsonl).read_text().splitlines()]
    rows=(json.loads(line) for line in Path(a.input).read_text().splitlines())
    print(json.dumps(build_corpus(rows,a.output,seed=a.seed,benchmark_texts=benchmarks),indent=2))
if __name__=='__main__': main()
