"""Frozen decoding and reply-loss comparisons; no model-as-judge scores."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import resource
import time
from rawrphos.inference.engine import Engine
from rawrphos.inference.chat import format_chat
from rawrphos.data.conversation import load_dataset,encode_example
from rawrphos.data.corpus import sha
from rawrphos.training.conversation import heldout
from rawrphos.training.checkpoint import parameter_hash


def output_metrics(text):
    words=re.findall(r"\w+",text.casefold())
    grams=[tuple(words[i:i+3]) for i in range(max(0,len(words)-2))]
    repeated=(len(grams)-len(set(grams)))/max(1,len(grams))
    return {'repeated_trigram_fraction':repeated,
        'punctuation_loop':bool(re.search(r'(?:[=]\s*){4,}|([.!?,"\'])\1{5,}',text)),
        'role_leak':bool(re.search(r'(?:^|\n)\s*(?:user|assistant|system):',text,re.I)),
        'empty_or_punctuation_only':not bool(words)}


def evaluate(checkpoint,dataset,output,expected_sha256,owner_prompts,threads=4):
    output=Path(output)
    if output.exists():raise FileExistsError('evaluation is immutable')
    began=time.perf_counter();engine=Engine(checkpoint,max_new_tokens=256,threads=threads,expected_sha256=expected_sha256)
    before=parameter_hash(engine.model)
    data=load_dataset(dataset)
    val=[encode_example(r,engine.tokenizer,384) for r in data['validation']]
    probes_path=Path(__file__).parent/'conversation/probes.json'
    probes=json.loads(probes_path.read_text())
    owners={r['id']:r['owner_effective_prompt'] for r in json.loads(Path(owner_prompts).read_text())['samples']}
    report={'schema':'rawrphos-conversation-evaluation-v1','checkpoint':engine.info(),
        'dataset_sha256':data['manifest']['dataset_sha256'],'probe_sha256':sha(probes_path.read_bytes()),
        'heldout':heldout(engine.model,val,8,len(val)),'decoding':{'temperature':0,'seed':67,'top_k':40},
        'samples':[],'limits':['Frozen prompts are development probes, not a general-capability benchmark.',
          'Coherence/relevance require separately recorded human-readable rubric judgments.',
          'Owner prompts are captured from isolated fresh state, not production memory.']}
    for probe in probes:
        for layer,prompt,budget in [('chat',format_chat(probe['messages']),64),('owner',owners[probe['id']],256)]:
            text=engine.complete(prompt,max_tokens=budget,temperature=0,seed=67)
            report['samples'].append(dict(id=probe['id'],category=probe['category'],layer=layer,
                prompt=prompt,output=text,max_tokens=budget,**output_metrics(text),**engine.last_metrics))
    report['summary']={}
    for layer in ('chat','owner'):
        rows=[r for r in report['samples'] if r['layer']==layer];n=len(rows)
        report['summary'][layer]={'cases':n,
            'mean_repeated_trigram_fraction':sum(r['repeated_trigram_fraction'] for r in rows)/n,
            'punctuation_loop_count':sum(r['punctuation_loop'] for r in rows),
            'role_leak_count':sum(r['role_leak'] for r in rows),
            'empty_or_punctuation_only_count':sum(r['empty_or_punctuation_only'] for r in rows),
            'eos_count':sum(r['eos_emitted'] for r in rows),
            'mean_generation_seconds':sum(r['generation_seconds'] for r in rows)/n,
            'aggregate_tokens_per_second':sum(r['generated_tokens'] for r in rows)/sum(r['generation_seconds'] for r in rows)}
    report.update(wall_seconds=time.perf_counter()-began,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        parameter_hash_before=before,parameter_hash_after=parameter_hash(engine.model))
    if before!=report['parameter_hash_after']:raise ValueError('evaluation mutated parameters')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'checkpoint_sha256':expected_sha256,'heldout':report['heldout'],'summary':report['summary']},indent=2),flush=True)
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);p.add_argument('--dataset',required=True)
    p.add_argument('--output',required=True);p.add_argument('--expected-sha256',required=True);p.add_argument('--owner-prompts',required=True)
    p.add_argument('--threads',type=int,default=4);a=p.parse_args();evaluate(a.checkpoint,a.dataset,a.output,a.expected_sha256,a.owner_prompts,a.threads)
if __name__=='__main__':main()
