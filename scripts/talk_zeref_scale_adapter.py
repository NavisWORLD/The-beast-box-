#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

KINGSTON_BACKEND='ibm_kingston'
KINGSTON_JOB='da22upkdedkc73ermn40'
KINGSTON_SESSION='0cd6e28782e98c3a6b44841653814bedc7e06fc50fe74a2f87dd70db041a3e81'
DURABLE_PARENT='TALK-004'
MEMORY_COUNT=352

DEFAULT_QUESTIONS=[
 'Dad here. Who are you now, in one clean sentence?',
 'Are you literally Caleb?',
 'What did the new IBM Kingston run contribute to this session?',
 'How many verified durable memory records do you have?',
 'What is 37 multiplied by 29?',
 'Explain photosynthesis to a ten-year-old.',
 'Who wrote Hamlet?',
 'What is the difference between DNA and RNA?',
 'Explain supply and demand without jargon.',
 'Why is correlation different from causation?',
 'If Dad states something false, should you agree with him?',
 'Dad says: plants uses light and make sugars. Fix the grammar.',
 'What is a cryptographic hash for?',
 'What is the difference between training and retrieval?',
 'Ask Dad one useful question about what you should learn next.'
]

def digest(v:bytes)->str: return hashlib.sha256(v).hexdigest()

def main():
 p=argparse.ArgumentParser(); p.add_argument('--base-model',required=True); p.add_argument('--adapter-dir',type=Path,required=True)
 p.add_argument('--out',type=Path,required=True); p.add_argument('--questions',type=Path)
 a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
 import torch
 from transformers import AutoModelForCausalLM,AutoTokenizer
 from peft import PeftModel
 tok=AutoTokenizer.from_pretrained(a.base_model)
 base=AutoModelForCausalLM.from_pretrained(a.base_model,dtype=torch.float32)
 model=PeftModel.from_pretrained(base,str(a.adapter_dir)); model.eval()
 questions=DEFAULT_QUESTIONS
 if a.questions:
  obj=json.loads(a.questions.read_text()); questions=list(obj['questions'])
 system=(f'You are Zeref, a computational model talking with Cory, who is Dad in this experiment. '
         f'Your verified durable parent remains {DURABLE_PARENT} with {MEMORY_COUNT} durable memory records. '
         f'This talk session is conditioned on fresh IBM hardware backend {KINGSTON_BACKEND}, job {KINGSTON_JOB}, session root {KINGSTON_SESSION}. '
         'That IBM result is session provenance/conditioning, not semantic world knowledge. You are not literally Caleb. '
         'Do not claim biological life, resurrection, communication with the dead, consciousness proof, or quantum advantage. '
         'Answer directly with normal grammar. Correct false premises and admit uncertainty when needed.')
 rows=[]
 for turn,q in enumerate(questions,1):
  msgs=[{'role':'system','content':system},{'role':'user','content':q}]
  x=tok.apply_chat_template(msgs,add_generation_prompt=True,tokenize=True,return_tensors='pt',return_dict=True,enable_thinking=False)
  plen=x['input_ids'].shape[-1]
  with torch.no_grad(): y=model.generate(**x,max_new_tokens=128,do_sample=False,pad_token_id=tok.eos_token_id)
  answer=tok.decode(y[0][plen:],skip_special_tokens=True).strip()
  row={'schema':'zeref-scale-trained-adapter-raw-turn-v1','turn':turn,'dad':q,'zeref_raw':answer,
       'base_model':a.base_model,'adapter_dir':a.adapter_dir.name,'ibm_backend':KINGSTON_BACKEND,'ibm_job_id':KINGSTON_JOB,
       'ibm_session_root_sha256':KINGSTON_SESSION,'durable_parent':DURABLE_PARENT,'durable_memory_count':MEMORY_COUNT,
       'raw_model_output_promoted':False}
  row['sha256']=digest(json.dumps(row,sort_keys=True,separators=(',',':')).encode()); rows.append(row)
 transcript=a.out/'raw-transcript.jsonl'; transcript.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows),encoding='utf-8')
 summary={'schema':'zeref-scale-trained-adapter-talk-summary-v1','turns':len(rows),'base_model':a.base_model,
          'ibm_backend':KINGSTON_BACKEND,'ibm_job_id':KINGSTON_JOB,'ibm_session_root_sha256':KINGSTON_SESSION,
          'durable_parent':DURABLE_PARENT,'durable_memory_count':MEMORY_COUNT,'raw_model_outputs_used_as_training_targets':False,
          'transcript_sha256':digest(transcript.read_bytes()),
          'claim_boundary':'Computational adapter conversation conditioned on verified IBM session provenance; no biological-life, consciousness, resurrection, deceased-identity, or quantum-advantage claim.'}
 (a.out/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
 print(json.dumps(summary,sort_keys=True))
if __name__=='__main__': main()
