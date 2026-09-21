"""Paired-seed bootstrap on measured outcomes; descriptive, not causality proof."""
import argparse,json,random,statistics
from pathlib import Path
from fly_movement import HERE,sha256


def bootstrap(d, n=12000):
    rng=random.Random(912842)
    vals=[sum(d[rng.randrange(len(d))] for _ in d)/len(d) for _ in range(n)]
    vals.sort()
    return [round(vals[int(.025*n)],7),round(vals[int(.975*n)],7)]

def main(folder):
    src=folder/'results.json';r=json.loads(src.read_text())
    assert sha256(folder/'runs.jsonl')==r['ledger_sha256']
    s=r['summary']; den=len(s['baseline']['per_seed_novel'])*24
    controls=['baseline','quantum_only','mock_bio_only','mock_fusion','rewired_mock_fusion',
              'no_propagation_mock_fusion','shuffle_quantum','shuffle_mock_bio']
    outcomes={}
    for arm in controls:
        trials=s[arm]['per_seed_novel'];rev=s[arm]['per_seed_reversal']
        paired=[(a-b)/24 for a,b in zip(trials,s['baseline']['per_seed_novel'])]
        outcomes[arm]={'heldout_success':sum(trials),'heldout_total':den,
                       'reversal_success':sum(rev),'reversal_total':den,
                       'heldout_minus_baseline_rate':round(sum(paired)/len(paired),7),
                       'paired_seed_bootstrap_95pct':bootstrap(paired),
                       'per_seed_heldout':trials,'per_seed_reversal':rev}
    effects=[(f-q-b+a)/24 for f,q,b,a in zip(
        s['mock_fusion']['per_seed_novel'],s['quantum_only']['per_seed_novel'],
        s['mock_bio_only']['per_seed_novel'],s['baseline']['per_seed_novel'])]
    result={'method':'paired eight-seed percentile bootstrap; resample seeds, 12000 draws',
            'bio_limitation':'mock biology only, NOT real physiology',
            'quantum_limitation':'nine source-reported historical IBM summaries, not full archive',
            'experiment_sha256':sha256(src),'outcomes':outcomes,
            'simulated_bio_x_quantum_interaction':{
                'mean':round(sum(effects)/len(effects),7),'paired_seed_bootstrap_95pct':bootstrap(effects),
                'per_seed':effects},
            'caution':'tiny paired differences, scripted grammar, limited seeds; exploratory, not biological effect'}
    (folder/'analysis.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'summary':{a:{k:outcomes[a][k] for k in ('heldout_success','heldout_total','heldout_minus_baseline_rate','paired_seed_bootstrap_95pct')} for a in controls},
                      'mock_interaction':result['simulated_bio_x_quantum_interaction']},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,default=HERE/'fusion_demo')
    main(p.parse_args().folder)
