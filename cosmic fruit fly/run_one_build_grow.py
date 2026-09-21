"""Authorized local-only experiment menu: select actions before a single run."""
import argparse, json
from pathlib import Path
from sandbox_ecology import ACTIONS
from run_build_grow import simulate, ARMS, DEFAULT_ENABLED, HERE, DATA, sha256


def main():
    ap=argparse.ArgumentParser(description='Run a single isolated sandbox lifecycle with configurable permissions')
    ap.add_argument('--arm',choices=ARMS,default='real_wiring')
    ap.add_argument('--seed',type=int,default=0)
    ap.add_argument('--allow',default=','.join(ACTIONS),help='comma-separated sandbox actions; unlisted actions denied')
    ap.add_argument('--out',type=Path,default=HERE/'build_grow_demo'/'custom_run.json')
    ap.add_argument('--max-ticks',type=int,default=155)
    opts=ap.parse_args()
    allow=frozenset(x.strip() for x in opts.allow.split(',') if x.strip())
    unknown=allow-set(ACTIONS)
    if unknown:ap.error('unrecognized action(s): '+', '.join(sorted(unknown)))
    if opts.seed<0 or opts.max_ticks<1:ap.error('seed >= 0, ticks >= 1 required')
    result=simulate(opts.seed,opts.arm,enabled=allow,trace=True,max_ticks_per_goal=opts.max_ticks)
    result['source_data_sha256']=sha256(DATA)
    result['permissions_requested']=sorted(allow)
    opts.out.parent.mkdir(parents=True,exist_ok=True)
    opts.out.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('arm','seed','steps','stages_completed','offspring_spawned','offspring_fed','permissions_requested')},indent=2))

if __name__=='__main__':main()
