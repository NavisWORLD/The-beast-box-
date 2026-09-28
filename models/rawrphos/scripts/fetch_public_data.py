"""Fetch pinned public text, never private memory; preserve whole documents."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request

STORIES_REV='f54c09fd23315a6f9c86f9dc80f725de7d8f9c64'
WIKI_REV='b08601e04326c79dfdd32d625aee71d232d685c3'

def take_stories(stream,limit):
    if type(limit) is not int or not 1<=limit<=100000: raise ValueError('invalid story count')
    parts=[]; count=0; size=0
    for raw in stream:
        size+=len(raw)
        if size>250*1024*1024: raise ValueError('public sample size limit exceeded')
        line=raw.decode('utf-8',errors='strict')
        if line.strip()=='<|endoftext|>':
            text=''.join(parts).strip(); parts=[]
            if text:
                yield text; count+=1
                if count==limit: return
        else: parts.append(line)
    # Truncated final story is excluded.

def acquire(output,stories=50000):
    import pyarrow.parquet as pq
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    destination=output/'public-input.jsonl'; sources=[]
    with destination.open('x',encoding='utf-8') as f:
        url=f'https://huggingface.co/datasets/roneneldan/TinyStories/resolve/{STORIES_REV}/TinyStories-train.txt'
        count=0; h=hashlib.sha256()
        with urllib.request.urlopen(url,timeout=60) as stream:
            for i,text in enumerate(take_stories(stream,stories)):
                row={'text':text,'source':'roneneldan/TinyStories/TinyStories-train.txt','license':'CDLA-Sharing-1.0',
                     'revision':STORIES_REV,'source_ordinal':i,'origin':'published GPT-3.5/GPT-4 synthetic fiction'}
                line=json.dumps(row,sort_keys=True,ensure_ascii=False)+'\n'; f.write(line); h.update(line.encode()); count+=1
        sources.append({'url':url,'revision':STORIES_REV,'license':'CDLA-Sharing-1.0','records':count,
            'sample_serialization_sha256':h.hexdigest(),'full_source_file_hash':None,'sampling':'first complete records',
            'attribution':'Ronen Eldan and Yuanzhi Li, TinyStories, arXiv:2305.07759',
            'license_url':'https://cdla.dev/sharing-1-0/','factual_ground_truth':False})
        url=f'https://huggingface.co/datasets/Salesforce/wikitext/resolve/{WIKI_REV}/wikitext-2-raw-v1/train-00000-of-00001.parquet'
        with urllib.request.urlopen(url,timeout=60) as stream: payload=stream.read(20*1024*1024+1)
        if len(payload)>20*1024*1024: raise ValueError('oversized WikiText')
        path=output/'wikitext2-train.parquet'; path.write_bytes(payload); digest=hashlib.sha256(payload).hexdigest()
        lines=pq.read_table(path,columns=['text'])['text'].to_pylist(); articles=[]; parts=[]
        for text in lines:
            if re.fullmatch(r'\s*= [^=]+ =\s*',text) and parts: articles.append(''.join(parts)); parts=[]
            parts.append(text)
        if parts: articles.append(''.join(parts))
        for i,text in enumerate(articles):
            row={'text':text,'source':'Salesforce/wikitext/wikitext-2-raw-v1/train','license':'CC-BY-SA-3.0',
                 'revision':WIKI_REV,'source_sha256':digest,'source_ordinal':i}
            f.write(json.dumps(row,sort_keys=True,ensure_ascii=False)+'\n')
        sources.append({'url':url,'revision':WIKI_REV,'license':'CC-BY-SA-3.0 / GFDL (upstream)',
            'articles':len(articles),'source_sha256':digest,'bytes':len(payload),'sampling':'upstream training split; entire articles',
            'attribution':'Salesforce WikiText / Stephen Merity et al. / original Wikipedia contributors',
            'license_url':'https://creativecommons.org/licenses/by-sa/3.0/'})
    receipt={'schema':'rawrphos-public-acquisition-v1','sources':sources,'personal_memory_used':False,
             'input_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'input_bytes':destination.stat().st_size}
    (output/'acquisition.json').write_text(json.dumps(receipt,indent=2))
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',required=True); p.add_argument('--stories',type=int,default=50000)
    a=p.parse_args(); print(json.dumps(acquire(a.output,a.stories),indent=2))
