#!/usr/bin/env python3
"""LoRA SFT for ZEREF-SCALE-001 on a pretrained language backbone."""
from __future__ import annotations
import argparse, json, os
from pathlib import Path

IBM_STATE_ROLE = "session_provenance_not_semantic_knowledge"
raw_model_output_promoted = False

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--model-id',default='Qwen/Qwen3.5-9B')
    p.add_argument('--output-dir',default='zeref-scale-001-adapter')
    p.add_argument('--hub-model-id',required=True)
    p.add_argument('--epochs',type=float,default=1.0)
    a=p.parse_args()
    if not os.environ.get('HF_TOKEN'):
        raise RuntimeError('HF_TOKEN with Hub write permission is required for persistent training')
    from datasets import load_dataset
    from peft import LoraConfig
    from trl import SFTConfig, SFTTrainer

    ds=load_dataset('json',data_files=str(a.dataset),split='train')
    if any(bool(x) for x in ds['raw_model_output_promoted']):
        raise RuntimeError('raw model output cannot be promoted into Zeref scale SFT')
    peft=LoraConfig(
        r=32,lora_alpha=64,lora_dropout=0.05,bias='none',
        target_modules='all-linear',task_type='CAUSAL_LM'
    )
    cfg=SFTConfig(
        output_dir=a.output_dir,
        num_train_epochs=a.epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=1e-5,
        warmup_ratio=0.05,
        weight_decay=0.01,
        logging_steps=5,
        save_strategy='steps',save_steps=50,
        max_length=2048,
        gradient_checkpointing=True,
        bf16=True,
        report_to='trackio',
        project='zeref-scale-001',run_name='dad-knowledge-backbone-sft',
        push_to_hub=True,hub_model_id=a.hub_model_id,
    )
    trainer=SFTTrainer(model=a.model_id,train_dataset=ds,peft_config=peft,args=cfg)
    trainer.train()
    trainer.push_to_hub()
    print(json.dumps({
        'status':'completed','base_model':a.model_id,'hub_model_id':a.hub_model_id,
        'ibm_state_role':IBM_STATE_ROLE,'raw_model_output_promoted':raw_model_output_promoted,
        'claim_boundary':'IBM session state is conditioning/provenance, not semantic knowledge.'
    },sort_keys=True))
if __name__=='__main__': main()
