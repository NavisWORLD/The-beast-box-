"""Bounded supervised adaptation of EXISTING weights and optimizer moments.

The first adaptation changes data/objective/context length, so it is NOT an
optimizer-exact continuation of pretraining's trajectory. Subsequent resumes
of this phase restore its complete state and require identical data/config.
"""
import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import resource
import time
import torch
from rawrphos.data.conversation import load_dataset, encode_example, collate
from rawrphos.training.checkpoint import load_checkpoint, save_checkpoint, rng_state, restore_rng
from rawrphos.training.train import source_identity

# Sampling balances skills; rows themselves stay deduplicated. The public
# dialogue remains the majority, with explicit support for short replies/EOS.
CATEGORY_MASS = {'dialogue':.55,'greeting':.10,'clarification':.08,'uncertainty':.08,
                 'instruction':.08,'arithmetic':.04,'memory':.04,'identity':.02,'factual':.01}


@dataclass
class ConversationConfig:
    batch_size: int = 8
    max_seq_len: int = 384
    learning_rate: float = 0.00008
    threads: int = 4
    checkpoint_every: int = 100
    eval_examples: int = 128
    def __post_init__(self):
        for key in ('batch_size', 'max_seq_len', 'threads', 'checkpoint_every', 'eval_examples'):
            if type(getattr(self,key)) is not int or getattr(self,key) < 1: raise ValueError('invalid '+key)
        if self.batch_size > 32 or self.max_seq_len > 512 or self.threads > 16:
            raise ValueError('CPU experiment budget exceeded')
        if not math.isfinite(self.learning_rate) or not 0 < self.learning_rate <= 0.0008:
            raise ValueError('invalid learning rate')


@torch.inference_mode()
def heldout(model, examples, batch_size=8, limit=128):
    was_training = model.training; model.eval()
    total = 0.0; tokens = 0
    try:
        for start in range(0,min(limit,len(examples)),batch_size):
            x,y = collate(examples,range(start,min(start+batch_size,limit,len(examples))))
            loss = model(x,targets=y)['loss']
            if not bool(torch.isfinite(loss)): raise FloatingPointError('nonfinite held-out loss')
            count = int((y != -100).sum()); total += loss.item()*count; tokens += count
    finally: model.train(was_training)
    return {'loss':total/tokens, 'perplexity':math.exp(min(80,total/tokens)),
            'supervised_tokens':tokens, 'examples':min(limit,len(examples)), 'objective':'assistant reply including EOS; token weighted'}


def continue_training(parent, dataset, output, *, steps, config=None, expected_sha256=None):
    c = config or ConversationConfig()
    if type(steps) is not int or not 1 <= steps <= 1000: raise ValueError('stage must be 1..1000 optimizer steps')
    torch.set_num_threads(c.threads); torch.use_deterministic_algorithms(True)
    loaded = load_checkpoint(parent,expected_checkpoint_sha256=expected_sha256)
    model, tokenizer, meta, state = (loaded[k] for k in ('model','tokenizer','metadata','state'))
    if c.max_seq_len > model.config.max_seq_len: raise ValueError('architecture context exceeded')
    data = load_dataset(dataset); dataset_hash = data['manifest']['dataset_sha256']
    continuing = meta.get('phase') == 'conversation-v1'
    if continuing:
        if meta['conversation_config'] != asdict(c): raise ValueError('conversation config mismatch')
        if meta['dataset_manifest_sha256'] != dataset_hash: raise ValueError('conversation dataset mismatch')
    train = [encode_example(r,tokenizer,c.max_seq_len) for r in data['train']]
    validation = [encode_example(r,tokenizer,c.max_seq_len) for r in data['validation']]
    categories=Counter(r.get('category','dialogue') for r in data['train'])
    sampling_weights=torch.tensor([CATEGORY_MASS[r.get('category','dialogue')]/categories[r.get('category','dialogue')]
                                   for r in data['train']],dtype=torch.float64)
    output = Path(output)
    start = meta['training_steps']; phase_start = meta.get('conversation_steps',0) if continuing else 0
    if any((output/f'step-{i:08d}').exists() for i in range(start+1,start+steps+1)):
        raise FileExistsError('stage would overwrite an existing checkpoint')
    output.mkdir(parents=True,exist_ok=True)
    optimizer = torch.optim.AdamW(model.parameters(),lr=c.learning_rate,betas=(.9,.95),weight_decay=.01)
    optimizer.load_state_dict(state['optimizer'])
    # Original post-6K schedule is already at constant 8e-5. Store the
    # adaptation schedule explicitly, including completed phase steps.
    for group in optimizer.param_groups: group['lr'] = c.learning_rate
    restore_rng(state['rng'])
    generator = torch.Generator(); generator.set_state(state['data_rng'])
    history = list(meta.get('conversation_validation_history',[])) if continuing else []
    if not history: history.append(dict(step=start,**heldout(model,validation,c.batch_size,c.eval_examples)))
    began = time.perf_counter(); optimize_seconds = 0.0; supervised = 0; input_tokens = 0
    parent_hash = meta['checkpoint_sha256']; source = source_identity()
    latest = str(Path(parent).resolve())
    baseline = meta.get('baseline_checkpoint_sha256',parent_hash) if continuing else parent_hash
    try:
        for offset in range(1,steps+1):
            tick = time.perf_counter(); model.train(); optimizer.zero_grad(set_to_none=True)
            indices = torch.multinomial(sampling_weights,c.batch_size,replacement=True,generator=generator).tolist()
            x,y = collate(train,indices); loss = model(x,targets=y)['loss']
            if not bool(torch.isfinite(loss)): raise FloatingPointError('nonfinite training loss')
            loss.backward(); grad = torch.nn.utils.clip_grad_norm_(model.parameters(),1.0,error_if_nonfinite=True)
            optimizer.step()
            if not all(bool(torch.isfinite(p).all()) for p in model.parameters()): raise FloatingPointError('nonfinite weights')
            supervised += int((y != -100).sum()); input_tokens += sum(len(train[i][0]) for i in indices)
            optimize_seconds += time.perf_counter()-tick
            current = start+offset
            if offset % c.checkpoint_every == 0 or offset == steps:
                measurement = dict(step=current,phase_steps=phase_start+offset,train_loss=loss.item(),gradient_norm=float(grad),
                    **heldout(model,validation,c.batch_size,c.eval_examples))
                history.append(measurement)
                elapsed = time.perf_counter()-began
                metadata = dict(meta, phase='conversation-v1',training_steps=current,
                    training_tokens=meta['training_tokens']+supervised,conversation_steps=phase_start+offset,
                    conversation_config=asdict(c),dataset_manifest_sha256=dataset_hash,
                    category_sampling_mass=CATEGORY_MASS,
                    dataset_provenance=data['manifest']['provenance'],baseline_checkpoint_sha256=baseline,
                    parent_checkpoint_sha256=parent_hash,source=source,conversation_validation_history=history,
                    training_seconds=meta.get('training_seconds',0)+elapsed,training_seq_len=c.max_seq_len,
                    context_extrapolation_validated=False,release_status='experimental-conversation-candidate',
                    resume_kind='optimizer+RNG retained; new supervised data/objective; exact only within this phase',
                    run_steps=offset,run_supervised_tokens=supervised,run_input_tokens=input_tokens,
                    run_wall_seconds=elapsed,run_optimization_seconds=optimize_seconds,
                    run_optimizer_tokens_per_second=input_tokens/optimize_seconds,
                    peak_process_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    hardware={'device':'cpu','threads':c.threads,'torch':str(torch.__version__)},
                    last_train_loss=loss.item(),failure_status=None,financial_cost=None)
                candidate=output/f'step-{current:08d}'
                sealed=save_checkpoint(candidate,model,tokenizer,metadata,{'optimizer':optimizer.state_dict(),
                    'rng':rng_state(),'data_rng':generator.get_state(),
                    'scheduler':{'kind':'constant','learning_rate':c.learning_rate,'completed_phase_steps':phase_start+offset}})
                parent_hash=sealed['checkpoint_sha256'];latest=str(candidate.resolve())
                marker=output/'latest.json.tmp';marker.write_text(json.dumps({'checkpoint':latest,'step':current,'sha256':parent_hash}));marker.replace(output/'latest.json')
                receipt=dict(measurement,checkpoint_sha256=parent_hash,run_wall_seconds=elapsed,input_tokens_per_second=input_tokens/optimize_seconds)
                with (output/'training.jsonl').open('a') as f: f.write(json.dumps(receipt)+'\n')
                print(json.dumps(receipt),flush=True)
        return {'checkpoint':latest,'steps':start+steps,'sha256':parent_hash,'validation':history[-1]}
    except BaseException as exc:
        with (output/'failures.jsonl').open('a') as f:
            f.write(json.dumps({'error_type':type(exc).__name__,'error':str(exc)[:512],
                'last_complete_checkpoint':latest,'completed_step':start+locals().get('offset',0)})+'\n')
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parent',required=True);p.add_argument('--dataset',required=True);p.add_argument('--output',required=True)
    p.add_argument('--steps',required=True,type=int);p.add_argument('--expected-sha256',required=True);p.add_argument('--config')
    a=p.parse_args();c=ConversationConfig(**json.loads(Path(a.config).read_text())) if a.config else ConversationConfig()
    print(json.dumps(continue_training(a.parent,a.dataset,a.output,steps=a.steps,config=c,expected_sha256=a.expected_sha256)))
if __name__=='__main__': main()
