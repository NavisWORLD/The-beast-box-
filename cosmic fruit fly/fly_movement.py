"""Executed 2D virtual-fly movement driven through a bounded published-connectivity subset.

Neural time constants, sensory encoding, effector decoding, locomotion and environment
are computational ASSUMPTIONS. Real FlyWire-derived connectivity is not a complete
brain, virtual walking is not an observed biological motor output. No tools or IO
except explicit local evidence outputs; never grants a model external authority.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
import statistics
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE / 'data' / 'real_flywire_subset.json'
SENSORY = ('lc4', 'lplc2')
MOTOR = ('dnp09', 'dna01', 'dna02', 'mdn', 'gf', 'escw')
CONDITIONS = ('published_subset', 'weight_matched_rewire', '25pct_lesion', 'no_propagation')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_graph(path=DATA):
    blob = json.loads(Path(path).read_text(encoding='utf8'))
    n = len(blob['ids'])
    assert n == 42 and len(set(blob['ids'])) == n
    assert len(blob['roles']) == n and len(blob['sides']) == n
    assert len(blob['edges']) == 95
    assert blob['origin_class'] == 'source_declared_biological'
    assert all(0 <= a < n and 0 <= b < n and math.isfinite(w) for a,b,w in blob['edges'])
    return blob


def incoming_matrix(data, condition, seed):
    n = len(data['ids'])
    edges = list(data['edges'])
    if condition == 'weight_matched_rewire':
        # Reassign destination endpoints; preserve source, signed weights,
        # edge count. The directional degree distribution is not preserved.
        targets = [b for a,b,w in edges]
        random.Random(seed + 1903).shuffle(targets)
        edges = [(a,targets[i],w) for i,(a,b,w) in enumerate(edges)]
    W = np.zeros((n,n),dtype=np.float64)
    for a,b,w in edges:
        W[b,a] += w
    if condition == 'no_propagation':
        W[:] = 0
    norm = np.maximum(1,np.sum(abs(W),axis=1))
    W /= norm[:,None]  # normalization is a numerical model assumption
    damage = set()
    if condition == '25pct_lesion':
        # Match lesion across seeds, applied to all neuron populations;
        # disconnect BOTH afferent and efferent edges.
        damage = set(random.Random(seed + 883).sample(range(n),n//4))
        for i in damage:
            W[i,:] = 0
            W[:,i] = 0
    return W,damage


def wrap(a):
    return (a + math.pi) % (2*math.pi) - math.pi


def sensor(data, pos, heading, target, obstacle, tick):
    bx,by = target
    dx,dy=bx-pos[0], by-pos[1]
    bearing=wrap(math.atan2(dy,dx)-heading)
    distance=math.hypot(dx,dy)
    odx,ody=obstacle[0]-pos[0],obstacle[1]-pos[1]
    ob=wrap(math.atan2(ody,odx)-heading)
    od=math.hypot(odx,ody)
    near=max(0,1-od/2.3)*max(0,math.cos(ob))
    # Feed actual recorded neuron role/side metadata, but sensor tuning and
    # all numeric gains are ASSUMED; no claim of measured physiology.
    v=np.zeros(len(data['ids']))
    for i,(role,side) in enumerate(zip(data['roles'],data['sides'])):
        sided=1 if side == 'left' else -1
        if role=='lplc2':
            v[i]=0.45*math.sin(bearing)*sided + 0.22*near
        elif role=='lc4':
            v[i]=0.95*near+0.04*math.cos(tick*.085+i)
    return v,bearing,distance,near


def channel(data,state,role,side=None):
    ix=[i for i,(r,s) in enumerate(zip(data['roles'],data['sides'])) if r==role and (side is None or s==side)]
    return float(np.mean(state[ix])) if ix else 0.0


def step_brain(data,W,damage,state,stim):
    drive=W@state
    nxt=np.tanh(.61*state+2.15*drive+stim)
    if damage:
        nxt[list(damage)]=0.
    return nxt


def control(data,state,bearing,near):
    # Behavioral motor interface is a modeled adapter. Descending brain
    # neurons alone are not VNC motor circuits; neither body mechanics nor
    # flight/walking physiology is derived from the connectome.
    steer=channel(data,state,'dna02','right')-channel(data,state,'dna02','left')
    steer+=.7*(channel(data,state,'dna01','right')-channel(data,state,'dna01','left'))
    steer+=.65*(channel(data,state,'escw','right')-channel(data,state,'escw','left'))
    steer+=.65*(channel(data,state,'gf','right')-channel(data,state,'gf','left'))
    drive=channel(data,state,'dnp09')
    reversal=channel(data,state,'mdn')
    escape=channel(data,state,'gf')+channel(data,state,'escw')
    speed=max(0.08,min(.90, .37+.27*drive-.11*reversal + .07*escape))
    turn=max(-1.9,min(1.9, 1.50*steer +.16*math.tanh(bearing) * abs(drive)))
    return speed,turn,{'forward_dnp09':round(drive,5),'steer_dna':round(steer,5),
                       'reverse_mdn':round(reversal,5),'escape_gf_escw':round(escape,5)}


def simulate(data,condition,seed=0,ticks=260):
    W, damage = incoming_matrix(data,condition,seed)
    rng=random.Random(1200+seed)
    pos=[-3.3,-.7+.4*rng.random()]
    heading=.1+.12*rng.uniform(-1,1)
    target=(3.3,1.15)
    obstacle=(0.0,.6)
    state=np.zeros(len(data['ids']),dtype=np.float64)
    dyn12=[0.]*12
    # Import real public Beast Box dyn12 function from unchanged archived file.
    # Local copy was byte checked in the earlier experiment.
    from harness import canonical_dyn12
    path=[]
    for tick in range(ticks):
        stim,bearing,distance,near=sensor(data,pos,heading,target,obstacle,tick)
        for _ in range(3):
            state=step_brain(data,W,damage,state,stim)
        pools=[float(np.mean(state[i::12])) for i in range(12)]
        dyn12=canonical_dyn12(dyn12,pools,step=tick)
        speed,turn,motor=control(data,state,bearing,near)
        dt=.10
        heading=wrap(heading +turn*dt)
        # Explicit numerical body/environment. Virtual fly cannot access host.
        ahead=[pos[0]+speed*dt*math.cos(heading), pos[1]+speed*dt*math.sin(heading)]
        # collision radius .25, disk obstacle radius .57
        if math.hypot(ahead[0]-obstacle[0],ahead[1]-obstacle[1])<.82:
            heading=wrap(heading+(1 if math.sin(bearing)>0 else -1)*.20)
            ahead=pos[:]
        pos=[max(-4.15,min(4.15,ahead[0])), max(-2.4,min(2.4,ahead[1]))]
        dist=math.hypot(pos[0]-target[0],pos[1]-target[1])
        path.append({'tick':tick,'x':round(pos[0],5),'y':round(pos[1],5),'heading':round(heading,5),
           'speed':round(speed,5),'turn':round(turn,5),'distance_to_target':round(dist,5),
           'loom':round(near,5),'neural':np.round(state,5).tolist(),
           'dyn12':[round(d,5) for d in dyn12], 'motor':motor})
    return {'condition':condition,'seed':seed,'lesion_indices':sorted(damage),
            'metrics':{'initial_distance':path[0]['distance_to_target'],
                       'final_distance':path[-1]['distance_to_target'],
                       'minimum_distance':min(p['distance_to_target'] for p in path),
                       'distance_traveled':round(sum(math.hypot(path[i]['x']-path[i-1]['x'],path[i]['y']-path[i-1]['y']) for i in range(1,len(path))),5),
                       'mean_speed':round(statistics.mean(p['speed'] for p in path),5),
                       'mean_abs_turn':round(statistics.mean(abs(p['turn']) for p in path),5),
                       'mean_neural_abs':round(statistics.mean(abs(x) for p in path for x in p['neural']),5)},
            'trace':path}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,default=HERE/'real_fly_demo')
    ap.add_argument('--seeds',type=int,default=8)
    ap.add_argument('--ticks',type=int,default=260)
    args=ap.parse_args()
    if args.seeds < 1 or args.ticks < 2: ap.error('positive seeds and >=2 ticks required')
    data=load_graph()
    args.output.mkdir(parents=True,exist_ok=True)
    runs=[simulate(data,c,s,args.ticks) for s in range(args.seeds) for c in CONDITIONS]
    with (args.output/'movement_traces.jsonl').open('w') as f:
        for r in runs: f.write(json.dumps(r,sort_keys=True,allow_nan=False)+'\n')
    summary={c:{m:{'mean':round(statistics.mean(r['metrics'][m] for r in runs if r['condition']==c),5),
                    'sd':round(statistics.pstdev(r['metrics'][m] for r in runs if r['condition']==c),5)}
                  for m in runs[0]['metrics']} for c in CONDITIONS}
    manifest={'classification':'REAL CONNECTIVITY SUBSET + ASSUMED NEURAL AND BODY DYNAMICS; NOT BIOLOGICAL LOCOMOTION',
             'source':{k:v for k,v in data.items() if k not in ('edges','ids','roles','sides')},
             'data_sha256':sha256(DATA),'code_sha256':sha256(Path(__file__)),
             'dyn12_sha256':sha256(HERE.parent/'beastbox'/'dyn12.py'),
             'conditions':CONDITIONS,'seeds':args.seeds,'ticks_per_run':args.ticks,
             'edges_aggregated':len(data['edges']),'neurons':len(data['ids']),
             'trace_sha256':sha256(args.output/'movement_traces.jsonl'),
             'summary':summary}
    (args.output/'results.json').write_text(json.dumps(manifest,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({'classification':manifest['classification'],'summary':summary},indent=2))

if __name__=='__main__':main()
