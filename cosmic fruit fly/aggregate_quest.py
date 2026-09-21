"""Resumable, hash-bound aggregation for the sensor quest."""
import argparse, json, statistics
from pathlib import Path
from run_sensor_quest import ARMS, PHASES, COUNTS, HERE, DATA, sha256


def aggregate(out, seeds):
    runs=[]
    for s in range(seeds):
        p=out/f'seed-{s}.jsonl'
        if not p.is_file():raise FileNotFoundError(p)
        rows=[json.loads(x) for x in p.read_text().splitlines()]
        if {r['arm'] for r in rows}!=set(ARMS) or any(r['seed']!=s for r in rows):raise RuntimeError(f'missing/mismatched runs: {p}')
        runs.extend(rows)
    summary={}
    for arm in ARMS:
        summary[arm]={}
        for phase in PHASES:
            ar=[r['metrics'][phase] for r in runs if r['arm']==arm]
            summary[arm][phase]={metric:{'mean':round(statistics.mean(r[metric] for r in ar),6),
                'sd':round(statistics.pstdev(r[metric] for r in ar),6)} for metric in ('reward','arrived','ticks','collisions','visual_frames')}
    with (out/'runs.jsonl').open('w') as f:
        for r in runs:f.write(json.dumps(r,sort_keys=True,allow_nan=False)+'\n')
    results={'classification':'REAL FlyWire-derived bounded graph + ASSUMED neural/vision/motor + SOFTWARE Q memory',
       'sensor_contract':'egocentric 96x64 RGB virtual camera segmented after rasterization; station odors; tactile contact; heading; no reward label before terminal station contact',
       'source_hash':sha256(DATA),'code_hash':sha256(HERE/'run_sensor_quest.py'),
       'sensor_code_hash':sha256(HERE/'sandbox_sensors.py'), 'dyn12_hash':sha256(HERE.parent/'beastbox'/'dyn12.py'),
       'episode_log_hash':sha256(out/'runs.jsonl'), 'arms':ARMS,'phases':dict(zip(PHASES,COUNTS)),
       'seeds':seeds,'summary':summary,'physical_authority':'none; virtual arena only',
       'source_license':'CC BY-NC 4.0; commercial use not granted'}
    (out/'results.json').write_text(json.dumps(results,sort_keys=True,indent=2,allow_nan=False)+'\n')
    return results

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=HERE/'sensor_quest_demo');ap.add_argument('--seeds',type=int,default=4)
    a=ap.parse_args();print(json.dumps(aggregate(a.out,a.seeds)['summary'],indent=2))
