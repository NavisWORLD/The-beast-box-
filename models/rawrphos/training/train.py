"""Bounded actual CPU training, immutable checkpoints and exact RNG resume."""
import argparse
from dataclasses import asdict,dataclass
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import resource
import subprocess
import time
import traceback
import torch
from rawrphos.architecture.model import RawrphosConfig,RawrphosLM
from rawrphos.tokenizer.tokenizer import RawrphosTokenizer
from rawrphos.data.corpus import load_corpus,canonical,sha
from rawrphos.training.checkpoint import load_checkpoint,save_checkpoint,parameter_hash,rng_state,restore_rng


@dataclass
class TrainingConfig:
    total_steps: int=3000
    batch_size: int=8
    seq_len: int=128
    vocab_size: int=4096
    learning_rate: float=.0008
    min_lr_ratio: float=.1
    warmup_steps: int=100
    weight_decay: float=.01
    gradient_accumulation: int=1
    gradient_clip: float=1.0
    seed: int=67
    eval_every: int=250
    eval_batches: int=8
    checkpoint_every: int=500
    threads: int=4
    def __post_init__(self):
        for name in ['total_steps','batch_size','seq_len','vocab_size','gradient_accumulation','eval_every','eval_batches','checkpoint_every','threads']:
            if type(getattr(self,name)) is not int or getattr(self,name)<1: raise ValueError('invalid '+name)
        if self.warmup_steps<0 or self.learning_rate<=0 or not math.isfinite(self.learning_rate): raise ValueError('invalid schedule')
        if not 0<=self.min_lr_ratio<=1 or self.gradient_clip<=0 or self.weight_decay<0: raise ValueError('invalid optimization config')

def learning_rate(step,c):
    if step<c.warmup_steps: return c.learning_rate*(step+1)/max(1,c.warmup_steps)
    progress=min(1,max(0,(step-c.warmup_steps)/max(1,c.total_steps-c.warmup_steps)))
    return c.learning_rate*(c.min_lr_ratio+(1-c.min_lr_ratio)*.5*(1+math.cos(math.pi*progress)))

def pack(rows,tokenizer):
    ids=[]
    for row in rows: ids.extend(tokenizer.encode(row['text'],add_bos=True,add_eos=True))
    return torch.tensor(ids,dtype=torch.long)

def batch(tokens,c,generator):
    if len(tokens)<=c.seq_len: raise ValueError('split too short for sequence length')
    starts=torch.randint(len(tokens)-c.seq_len,(c.batch_size,),generator=generator)
    windows=tokens[starts[:,None]+torch.arange(c.seq_len+1)[None,:]]
    return windows[:,:-1],windows[:,1:]

@torch.inference_mode()
def validate(model,tokens,c):
    model.eval(); gen=torch.Generator().manual_seed(c.seed+100000); loss=0.0
    for _ in range(c.eval_batches):
        x,y=batch(tokens,c,gen); value=model(x,targets=y)['loss']
        if not bool(torch.isfinite(value)): raise FloatingPointError('nonfinite held-out loss')
        loss+=value.item()
    model.train()
    return {'loss':loss/c.eval_batches,'perplexity':math.exp(min(80,loss/c.eval_batches)),
            'tokens':c.eval_batches*c.batch_size*c.seq_len,'sampling_seed':c.seed+100000}

def source_identity():
    root=Path(__file__).resolve().parents[3]
    try:
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        dirty=bool(subprocess.check_output(['git','status','--porcelain','--','models/rawrphos'],cwd=root,text=True).strip())
    except (OSError,subprocess.CalledProcessError): commit=None; dirty=None
    paths=[p for p in Path(__file__).resolve().parents[1].rglob('*.py') if 'tests' not in p.parts]
    files={str(p.relative_to(Path(__file__).resolve().parents[1])):sha(p.read_bytes()) for p in sorted(paths)}
    return {'commit':commit,'dirty':dirty,'source_files':files,'source_sha256':sha(canonical(files))}

def train(corpus,output,model_config,training_config,steps=None,resume=None):
    c=training_config; output=Path(output); output.mkdir(parents=True,exist_ok=True)
    requested_model_config=model_config.to_dict()
    torch.set_num_threads(c.threads); torch.manual_seed(c.seed); random.seed(c.seed)
    torch.use_deterministic_algorithms(True)
    data=load_corpus(corpus); dataset_hash=data['manifest']['dataset_sha256']
    source=source_identity(); began=time.perf_counter(); start_step=0; prior_seconds=0.0
    gen=torch.Generator().manual_seed(c.seed+1); history=[]; parent=None
    if resume:
        loaded=load_checkpoint(resume); meta=loaded['metadata']; state=loaded['state']
        if meta['training_config']!=asdict(c) or meta['dataset_manifest_sha256']!=dataset_hash:
            raise ValueError('resume training configuration or dataset identity mismatch')
        if meta['requested_model_config']!=requested_model_config: raise ValueError('resume architecture mismatch')
        model=loaded['model']; tokenizer=loaded['tokenizer']; start_step=meta['training_steps']
        initial_hash=meta['initial_parameter_sha256']; history=list(meta['validation_history'])
        gen.set_state(state['data_rng']); parent=meta['checkpoint_sha256']; prior_seconds=meta['training_seconds']
    else:
        tokenizer=RawrphosTokenizer.train((r['text'] for r in data['train']),c.vocab_size)
        if tokenizer.vocab_size!=model_config.vocab_size:
            model_config=RawrphosConfig.from_dict(dict(model_config.to_dict(),vocab_size=tokenizer.vocab_size))
        model=RawrphosLM(model_config); initial_hash=parameter_hash(model)
    optimizer=torch.optim.AdamW(model.parameters(),lr=c.learning_rate,betas=(.9,.95),weight_decay=c.weight_decay)
    if resume:
        optimizer.load_state_dict(state['optimizer']); restore_rng(state['rng'])
    train_tokens=pack(data['train'],tokenizer); val_tokens=pack(data['validation'],tokenizer)
    if not history: history.append(dict(step=0,**validate(model,val_tokens,c)))
    end=min(c.total_steps,start_step+(c.total_steps-start_step if steps is None else steps))
    if end<=start_step: raise ValueError('no optimizer steps requested')
    latest=None; last_loss=None; run_tokens=0; optimization_started=time.perf_counter()
    log=output/'training.jsonl'
    try:
        for step in range(start_step,end):
            model.train(); optimizer.zero_grad(set_to_none=True); loss_value=0
            for group in optimizer.param_groups: group['lr']=learning_rate(step,c)
            for _ in range(c.gradient_accumulation):
                x,y=batch(train_tokens,c,gen); result=model(x,targets=y); loss=result['loss']
                if not bool(torch.isfinite(loss)): raise FloatingPointError('nonfinite training loss')
                (loss/c.gradient_accumulation).backward(); loss_value+=loss.item()/c.gradient_accumulation
            grad=torch.nn.utils.clip_grad_norm_(model.parameters(),c.gradient_clip,error_if_nonfinite=True)
            optimizer.step(); run_tokens+=c.batch_size*c.seq_len*c.gradient_accumulation; last_loss=loss_value
            current=step+1
            if current%c.eval_every==0 or current==end:
                measurement=dict(step=current,train_loss=loss_value,gradient_norm=float(grad),
                    learning_rate=optimizer.param_groups[0]['lr'],**validate(model,val_tokens,c))
                history.append(measurement)
                with log.open('a') as f: f.write(json.dumps(measurement)+'\n')
                print(json.dumps(measurement),flush=True)
            if current%c.checkpoint_every==0 or current==end:
                elapsed=time.perf_counter()-began; latest=output/f'step-{current:08d}'
                metadata={'schema':'rawrphos-training-v1','training_steps':current,
                    'training_tokens':current*c.batch_size*c.seq_len*c.gradient_accumulation,
                    'corpus_token_counts':{'train':len(train_tokens),'validation':len(val_tokens)},
                    'training_config':asdict(c),'training_config_sha256':sha(canonical(asdict(c))),
                    'requested_model_config':requested_model_config,
                    'dataset_manifest_sha256':dataset_hash,'initial_parameter_sha256':initial_hash,
                    'parent_checkpoint_sha256':parent,'source':source,'validation_history':history,
                    'last_train_loss':last_loss,'training_seconds':prior_seconds+elapsed,
                    'run_optimizer_tokens_per_second':run_tokens/(time.perf_counter()-optimization_started),
                    'peak_process_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    'hardware':{'device':'cpu','threads':c.threads,'torch':torch.__version__,'python':platform.python_version(),'platform':platform.platform()},
                    'precision':'float32','training_seq_len':c.seq_len,'context_limit':model.config.max_seq_len,
                    'context_extrapolation_validated':False,'failure_status':None,'financial_cost':None,
                    'release_status':'trained-candidate','adaptation_during_inference':False}
                save_checkpoint(latest,model,tokenizer,metadata,{'optimizer':optimizer.state_dict(),'rng':rng_state(),'data_rng':gen.get_state()})
                (output/'latest.json').write_text(json.dumps({'checkpoint':str(latest.resolve()),'step':current}))
        return {'checkpoint':str(latest.resolve()),'steps':end,'validation':history[-1]}
    except BaseException as exc:
        with (output/'failures.jsonl').open('a') as f:
            f.write(json.dumps({'step':locals().get('step',start_step),'error_type':type(exc).__name__,
                'last_complete_checkpoint':None if latest is None else str(latest),'time':time.time()})+'\n')
        raise

def main():
    p=argparse.ArgumentParser(); p.add_argument('--corpus',required=True); p.add_argument('--output',required=True)
    p.add_argument('--model-config',required=True); p.add_argument('--training-config',required=True)
    p.add_argument('--steps',type=int); p.add_argument('--resume')
    a=p.parse_args(); mc=RawrphosConfig.from_dict(json.loads(Path(a.model_config).read_text())); tc=TrainingConfig(**json.loads(Path(a.training_config).read_text()))
    print(json.dumps(train(a.corpus,a.output,mc,tc,a.steps,a.resume),indent=2))
if __name__=='__main__': main()
