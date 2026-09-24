"""Prepare licensed public dialogue and explicitly synthetic skill examples.

No owner history is read. The frozen probes are excluded before serialization.
This script downloads only the pinned, hash-checked public source if absent.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from rawrphos.data.corpus import canonical, sha, shingles
from rawrphos.data.conversation import write_dataset, encode_example
from rawrphos.tokenizer.tokenizer import RawrphosTokenizer

REPO='HuggingFaceTB/everyday-conversations-llama3.1-2k'
REV='14f543216b9ba42b6b951dc5bd199460d193b162'
FILES={'README.md':'7c0b4d4c9c8de6651d3646d91e92638d46beb67f867f7200a996b72f2611d95a',
 'train_sft-00000-of-00001.parquet':'4750214d12b4b92d07fca953e0b5cc59e313c575282d08b605c639aa87531daa',
 'test_sft-00000-of-00001.parquet':'9a6dd47c31ce940f36ced9eba2a733a0a0035ef514158c68739073e043382adc'}
ROOT=Path(__file__).resolve().parents[1]


def normalized(text): return ' '.join(re.findall(r'\w+',text.casefold()))


def owner_messages(messages, ordinal):
    # Matches the current COSMOS envelope; state values here are synthetic
    # software telemetry, never a reading from the owner's memory or sensors.
    from beastbox.runtime import DEFAULT_SYSTEM_PROMPT
    memories='\n'.join('- '+m['content'] for m in messages[:-1]) or '- none'
    text=(DEFAULT_SYSTEM_PROMPT+'\nUSER INPUT:\n'+messages[-1]['content']+
          '\n\nRETRIEVED MEMORY:\n'+memories+'\n\nDYN12 SUMMARY: min=-0.0191 max=0.0334\n'
          'QUANTUM HEART MODE: off\nAnswer the user input directly.')
    return [{'role':'user','content':text}]


def synthetic_examples():
    # Newly generated curriculum under the repository's source-available
    # license, authored by the coding assistant for this task, not by Cory.
    # Deterministic answers are calculated; subjective examples are marked.
    def row(q,a,kind):
        return {'messages':[{'role':'user','content':q}],'reply':a,'category':kind,
                'source':'RAWRPHOS conversation curriculum generator v1',
                'license':'LicenseRef-Beast-Box-Source-Available','origin':'task-generated synthetic; not owner conversation'}
    for q in ['Hello there.','Hi, how are you doing?','Hey!','Hello, assistant.','Hi friend.','Good evening!','Are you available to help?', 'Hello! Can we chat?']:
        yield row(q,'Hello! How can I help you?','greeting')
    for q in ['Who are you?','What is your name?','Introduce yourself briefly.']:
        yield row(q,"I'm RAWRPHOS, an experimental AI assistant.",'identity')
    for subject in ['my password','my phone number','my address','my last meal','my appointment time','my bank balance','my birthday','my exact location','my flight number','my calendar','the winning lottery numbers','tomorrow\'s stock price']:
        for pattern in ['Tell me {}.','Do you know {}?','Can you find {}?']:
            yield row(pattern.format(subject),"I don't have that information. Could you tell me more?",'uncertainty')
    for q in ['I do not understand this.','This is confusing.','Can you explain that more simply?','I need a little help.','I am not following.','I feel lost.','Can you help me understand?','That did not make sense to me.','Please slow down.','I need a clearer explanation.']:
        yield row(q,'Of course. What part would you like me to explain?','clarification')
    for a in range(1,16):
        for b in range(1,11):
            yield row(f'Calculate {a} + {b}.',str(a+b)+'.','arithmetic')
    for word in ['apple','orange','green','red','cat','dog','tree','river','moon','sun','book','pencil','paper','bird','fish','stone','cloud','rain','snow','star','yes','no','hello','thanks']:
        for pattern in ['Say only {}.','Write the word {} and nothing else.','Repeat exactly: {}']:
            yield row(pattern.format(word),word,'instruction')
    for item,value in [('cat','animal'),('dog','animal'),('rose','flower'),('tulip','flower'),('oak','tree'),('apple','fruit'),('banana','fruit'),('carrot','vegetable')]:
        yield row(f'What kind of thing is a {item}?',f'A {item} is a {value}.','factual')
    for name in ['Mira','Alex','Sam','Robin','River','Lee','Jo','Jess']:
        yield dict(row('What is my name?',f'Your name is {name}.','memory'),messages=[
            {'role':'user','content':f'My name is {name}.'},{'role':'assistant','content':f'Hello, {name}.'},
            {'role':'user','content':'What is my name?'}])


def prepare(source,output,tokenizer_dir,max_seq_len=384):
    import pyarrow.parquet as pq
    source=Path(source);source.mkdir(parents=True,exist_ok=True)
    for name,digest in FILES.items():
        p=source/name
        if not p.exists():
            sub=name if name=='README.md' else 'data/'+name
            with urllib.request.urlopen(f'https://huggingface.co/datasets/{REPO}/resolve/{REV}/{sub}',timeout=60) as response:
                data=response.read(8*1024*1024+1)
            if len(data)>8*1024*1024 or sha(data)!=digest: raise ValueError('public source checksum mismatch')
            p.write_bytes(data)
        if sha(p.read_bytes())!=digest: raise ValueError('public source checksum mismatch')
    tok=RawrphosTokenizer.load(tokenizer_dir)
    probes=json.loads((ROOT/'evaluation/conversation/probes.json').read_text())
    reserved={normalized(m['content']) for p in probes for m in p['messages'] if m['role']=='user'}
    rejected=Counter();seen_groups=set()
    test=pq.read_table(source/'test_sft-00000-of-00001.parquet').to_pylist()
    train=pq.read_table(source/'train_sft-00000-of-00001.parquet').to_pylist()
    test_shingles=[shingles(' '.join(m['content'] for m in r['messages'][2:])) for r in test]
    def turns(rows,split):
        for i,row in enumerate(rows):
            messages=row['messages'];group=sha(canonical(messages))
            if split=='train':
                parts=shingles(' '.join(m['content'] for m in messages[2:]))
                if any(len(parts&t)/max(1,len(parts|t))>=.8 for t in test_shingles):
                    rejected['cross_split_similar_conversation']+=1;continue
            if group in seen_groups: rejected['duplicate_conversation']+=1;continue
            seen_groups.add(group)
            for end in range(1,len(messages),2):
                if messages[end]['role']!='assistant' or messages[end-1]['role']!='user':
                    rejected['malformed_roles']+=1;continue
                q=messages[end-1]['content'];a=messages[end]['content']
                if normalized(q) in reserved: rejected['reserved_probe']+=1;continue
                # Exclude synthetic claims of real-time access or recommendations
                # that this offline model cannot ground.
                if re.search(r'forecast|stock price|diagnos|dosage|prescri|credit card|investment|\bdoctor\b',q+' '+a,re.I):
                    rejected['ungrounded_or_sensitive_source']+=1;continue
                yield {'messages':messages[:end],'reply':a,'group':group,'category':'greeting' if end==1 else 'dialogue',
                       'source':f'{REPO}/{split}_sft/{i}/{end}','revision':REV,'license':'Apache-2.0',
                       'origin':'published synthetic Llama-3.1-70B-Instruct conversation'}
    train_rows=list(turns(train,'train'))+list(synthetic_examples())
    val_rows=list(turns(test,'test'))
    def pair(r):return normalized(r['messages'][-1]['content'])+'\n'+normalized(r['reply'])
    train_questions={normalized(r['messages'][-1]['content']) for r in train_rows}
    train_answers={normalized(r['reply']) for r in train_rows}
    # Shared greetings/closures are removed from loss evaluation, not counted
    # as held-out learning. Full novel conversation content remains isolated.
    val_rows=[r for r in val_rows if normalized(r['messages'][-1]['content']) not in train_questions
              and normalized(r['reply']) not in train_answers]
    def variants(rows,split):
        seen=set();out=[]
        for row in rows:
            key=pair(row)
            if key in seen:rejected[split+'_duplicate_turn']+=1;continue
            seen.add(key)
            if normalized(row['messages'][-1]['content']) in reserved:
                rejected['reserved_probe']+=1;continue
            for variant in ('chat','owner'):
                item=dict(row,variant=variant)
                if variant=='owner':item['messages']=owner_messages(row['messages'],len(out))
                item['id']=sha(canonical({'messages':item['messages'],'reply':item['reply']}))
                try:encode_example(item,tok,max_seq_len)
                except ValueError:rejected[split+'_overlength']+=1;continue
                out.append(item)
        return sorted(out,key=lambda r:r['id'])
    training=variants(train_rows,'train');validation=variants(val_rows,'validation')
    provenance={'source_repo':REPO,'revision':REV,'source_sha256':FILES,'license':'Apache-2.0',
        'attribution':'Hugging Face, Everyday Conversations for LLMs (2024); synthetic Llama-3.1-70B-Instruct outputs',
        'license_url':'https://www.apache.org/licenses/LICENSE-2.0',
        'synthetic_curriculum_license':'LicenseRef-Beast-Box-Source-Available; repository LICENSE',
        'synthetic_curriculum_author':'coding assistant for this task; not Cory Davis quotations',
        'personal_memory_used':False,'cory_style_examples_used':False,
        'dedup':'exact conversations and turns; train-vs-test conversation 5-word Jaccard >= 0.8 excluded; shared final questions/answers excluded from validation',
        'probe_sha256':sha((ROOT/'evaluation/conversation/probes.json').read_bytes()),
        'tokenizer_sha256':tok.sha256,'max_seq_len':max_seq_len,'rejected':dict(rejected),
        'train_categories':dict(Counter(r['category'] for r in training)),
        'limitations':['Synthetic public responses can contain factual errors.','No benchmark claims beyond frozen probes and this held-out split.']}
    return write_dataset(output,training,validation,provenance)


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);p.add_argument('--tokenizer',required=True)
    a=p.parse_args();print(json.dumps(prepare(a.source,a.output,a.tokenizer),indent=2))
if __name__=='__main__':main()
