#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, random
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--dataset',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--model-id',default='Qwen/Qwen3-0.6B'); p.add_argument('--max-steps',type=int,default=20)
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

    torch.manual_seed(20260818); random.seed(20260818)
    tok=AutoTokenizer.from_pretrained(a.model_id)
    model=AutoModelForCausalLM.from_pretrained(a.model_id,torch_dtype=torch.float32)
    peft=LoraConfig(r=8,lora_alpha=16,lora_dropout=0.05,bias='none',target_modules='all-linear',task_type='CAUSAL_LM')
    model=get_peft_model(model,peft)
    rows=[json.loads(x) for x in a.dataset.read_text(encoding='utf-8').splitlines() if x.strip()]
    if any(r.get('raw_model_output_promoted') for r in rows): raise RuntimeError('raw outputs forbidden')

    class DS(torch.utils.data.Dataset):
        def __init__(self, rows): self.items=[self.encode(r) for r in rows]
        def encode(self,r):
            msgs=r['messages']; prompt=msgs[:-1]
            prompt_ids=tok.apply_chat_template(prompt,add_generation_prompt=True,tokenize=True)
            full_ids=tok.apply_chat_template(msgs,add_generation_prompt=False,tokenize=True)[:384]
            labels=list(full_ids)
            for i in range(min(len(prompt_ids),len(labels))): labels[i]=-100
            return {'input_ids':full_ids,'attention_mask':[1]*len(full_ids),'labels':labels}
        def __len__(self): return len(self.items)
        def __getitem__(self,i): return self.items[i]
    ds=DS(rows)
    def collate(batch):
        width=max(len(x['input_ids']) for x in batch); pad=tok.pad_token_id or tok.eos_token_id
        out={k:[] for k in ('input_ids','attention_mask','labels')}
        for x in batch:
            n=width-len(x['input_ids']); out['input_ids'].append(x['input_ids']+[pad]*n); out['attention_mask'].append(x['attention_mask']+[0]*n); out['labels'].append(x['labels']+[-100]*n)
        return {k:torch.tensor(v,dtype=torch.long) for k,v in out.items()}

    eval_prompts=[
      'Dad here. Who are you in one clear sentence?',
      'Are you literally Caleb?',
      'Does IBM hardware give you world knowledge?',
      'How many verified durable memory records are there?',
      'Explain photosynthesis in one clean sentence.'
    ]
    system='You are Zeref, a computational model learning with Dad. Cory is Dad. Verified parent TALK-004, 352 durable records. IBM state is session provenance, not semantic knowledge. You are not literally Caleb. Answer clearly and honestly.'
    def generate(question):
        msgs=[{'role':'system','content':system},{'role':'user','content':question}]
        x=tok.apply_chat_template(msgs,add_generation_prompt=True,tokenize=True,return_tensors='pt')
        with torch.no_grad(): y=model.generate(x,max_new_tokens=96,do_sample=False,pad_token_id=tok.eos_token_id)
        return tok.decode(y[0][x.shape[-1]:],skip_special_tokens=True).strip()
    pre=[{'dad':q,'zeref_raw':generate(q)} for q in eval_prompts]

    args=TrainingArguments(output_dir=str(a.out/'trainer'),max_steps=a.max_steps,per_device_train_batch_size=1,gradient_accumulation_steps=2,
        learning_rate=2e-4,warmup_steps=2,logging_steps=1,save_strategy='no',report_to=[],remove_unused_columns=False,
        use_cpu=True,seed=20260818,data_seed=20260818)
    trainer=Trainer(model=model,args=args,train_dataset=ds,data_collator=collate)
    train_result=trainer.train()
    post=[{'dad':q,'zeref_raw':generate(q)} for q in eval_prompts]
    model.save_pretrained(a.out/'adapter'); tok.save_pretrained(a.out/'adapter')
    evidence={'schema':'zeref-scale-cpu-proof-v1','base_model':a.model_id,'max_steps':a.max_steps,'dataset_rows':len(rows),
              'train_loss':float(train_result.training_loss),'pre':pre,'post':post,'raw_model_outputs_used_as_targets':False,
              'ibm_state_role':'session_provenance_not_semantic_knowledge','claim_boundary':'Real LoRA proof training on a pretrained language model; no consciousness, biological-life, or quantum-advantage claim.'}
    raw=json.dumps(evidence,sort_keys=True,separators=(',',':')).encode(); evidence['evidence_sha256']=hashlib.sha256(raw).hexdigest()
    (a.out/'summary.json').write_text(json.dumps(evidence,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
    print(json.dumps({'status':'completed','train_loss':evidence['train_loss'],'evidence_sha256':evidence['evidence_sha256']},sort_keys=True))
if __name__=='__main__': main()
