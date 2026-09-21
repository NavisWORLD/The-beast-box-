"""Resumable single-seed runner; writes each actual executed arm after completion."""
import argparse,json
from pathlib import Path
from run_sensor_quest import ARMS,HERE,COUNTS,load_graph,run_arm

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,required=True);ap.add_argument('--out',type=Path,default=HERE/'sensor_quest_demo')
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    data=load_graph(); p=args.out/f'seed-{args.seed}.jsonl'
    with p.open('w') as f:
        for arm in ARMS:
            run=run_arm(data,arm,args.seed,COUNTS,trace=(args.seed==0))
            f.write(json.dumps(run,sort_keys=True,allow_nan=False)+'\n');f.flush()
            print(f'seed={args.seed} {arm} {run["metrics"]}',flush=True)
