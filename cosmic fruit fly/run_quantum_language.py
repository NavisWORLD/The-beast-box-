"""Matched quantum-summary replay/ablation and bounded text actuator experiment.

No live IBM/physiological link, no biological speech, no host keyboard access.
"""
from __future__ import annotations
import argparse, json, statistics
from pathlib import Path
from fly_movement import HERE, DATA, sha256
from quantum_language import DATA as QUANTUM_DATA, load_measurements
from run_build_grow import simulate

OUT=HERE/'quantum_language_demo'
ARMS={
  'real_quantum_typing':('real_wiring','replay',True),
  'real_quantum_off':('real_wiring','off',True),
  'real_quantum_shuffled':('real_wiring','shuffled',True),
  'rewired_quantum_typing':('rewired','replay',True),
  'no_propagation_quantum_typing':('no_propagation','replay',True),
  'real_quantum_type_disabled':('real_wiring','replay',False),
}

def main(seeds=6,out=OUT):
    if seeds<1:raise ValueError('seeds must be positive')
    load_measurements()
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    for seed in range(seeds):
        for name,(wiring,quantum,typing) in ARMS.items():
            r=simulate(seed,wiring,quantum_mode=quantum,typing=typing,
                       trace=(name=='real_quantum_typing' or (seed==0 and name=='real_quantum_off')))
            if name=='real_quantum_typing' and r['stages_completed']!=11:
                raise RuntimeError('replay arm lost stage: record failure and abort footage')
            r['experiment_arm']=name
            results.append(r)
    with (out/'runs.jsonl').open('w',encoding='utf8') as f:
        for r in results:
            f.write(json.dumps(r,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n')
    summary={}
    for name in ARMS:
        rows=[r for r in results if r['experiment_arm']==name]
        summary[name]={key:{'mean':round(statistics.mean(r[key] for r in rows),7),
                            'sd':round(statistics.pstdev(r[key] for r in rows),7)}
                       for key in ('steps','stages_completed','offspring_spawned','offspring_fed','typed_word_count','mean_abs_quantum_drive','neural_mean_abs')}
    off=next(r for r in results if r['experiment_arm']=='real_quantum_off' and r['seed']==0)
    real=next(r for r in results if r['experiment_arm']=='real_quantum_typing' and r['seed']==0)
    if len(real['trace'])!=len(off['trace']):raise RuntimeError('unmatched trace lengths')
    delta=sum(sum(abs(x-y) for x,y in zip(a['neural'],b['neural']))/42
        for a,b in zip(real['trace'],off['trace']))/len(real['trace'])
    evidence={'classification':'historical 9 IBM summary records injected as bounded model signal; FlyWire-derived anatomical subset with assumed dynamics; simulated sensory/typing, NOT real bio telemetry, no learned language',
       'quantum_source_url':'https://github.com/NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2/blob/main/workload_decode_summary.json',
       'quantum_source_git_blob_sha1':'084282a26bf923f03188a2be4c36f3fb34b09987',
       'quantum_subset_count':9,'quantum_total_reported_shots':9*4224,'bio_signal_status':'BLOCKED: no verified physiological recording. COSMOS MockBioProvider is simulated and was refused',
       'anatomy_data_sha256':sha256(DATA),'quantum_derived_file_sha256':sha256(QUANTUM_DATA),
       'code_sha256':{p:sha256(HERE/p) for p in ('quantum_language.py','run_build_grow.py','run_quantum_language.py','sandbox_ecology.py')},
       'ledger_sha256':sha256(out/'runs.jsonl'), 'seeds':seeds,'arms':list(ARMS),
       'seed0_mean_absolute_neural_difference_vs_quantum_off':round(delta,8),
       'summary':summary,'text_claim':'finite event-mapped vocabulary: programmed typing, no language learning',
       'capabilities':'closed software sandbox only; no host keyboard, shell, network, hardware, tool authority'}
    (out/'results.json').write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n',encoding='utf8')
    print(json.dumps({'runs':len(results),'seeds':seeds,'delta':round(delta,8),'summary':summary},indent=2))
    return evidence

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seeds',type=int,default=6)
    p.add_argument('--output',type=Path,default=OUT)
    a=p.parse_args();main(a.seeds,a.output)
