"""Matched associative foraging task over published FlyWire-derived connectivity.

The fly does not know the rewarded station until it arrives. The explicit Q-table
is SOFTWARE associative learning; it is not biological neural plasticity. The
anatomical network influences a separately assumed navigation controller.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
import statistics
from pathlib import Path
import numpy as np
from fly_movement import DATA, HERE, incoming_matrix, load_graph, channel, sha256, wrap
from harness import canonical_dyn12

ARMS = ('real_wiring_learning','rewired_learning','no_propagation_learning',
        'frozen_after_training','no_learning')
PHASES = ('train','heldout_layout','reversal')
# Episodic phase lengths fixed before experiment execution.
PHASE_N = (80,40,40)


def trial_plan(seed: int, counts=PHASE_N):
    rng = random.Random(300700 + seed)
    rule = rng.randrange(2)  # cue 0 -> station 0 or 1; opposite for cue 1
    schedule = []
    for phase, num in zip(PHASES,counts):
        for idx in range(num):
            cue = rng.randrange(2)
            # Distinct geometry and new start headings in both evaluation phases.
            if phase == 'train':
                stations = ((-2.25,1.1),(2.25,1.1))
            elif phase == 'heldout_layout':
                stations = ((2.4,1.05),(-2.2,.95))
            else:
                stations = ((2.0,-.8),(-2.0,1.5))
            start = (rng.uniform(-.55,.55), -2.2+rng.uniform(-.24,.24))
            heading = rng.uniform(-math.pi, math.pi)
            correct = (cue ^ rule ^ int(phase == 'reversal'))
            schedule.append({'phase':phase,'cue':cue,'correct':correct,'stations':stations,
                             'start':start,'heading':heading,'episode_in_phase':idx})
    return schedule


def network_step(data, W, neural, cue, bearings, turn_target, step):
    # Both stations' visual bearings and odor cue are sensory inputs, but the
    # true reward label and chosen station's correctness NEVER enter this state.
    stim = np.zeros(len(data['ids']),dtype=np.float64)
    for i, (role,side) in enumerate(zip(data['roles'],data['sides'])):
        handed = 1.0 if side == 'left' else -1.0
        if role == 'lplc2':
            stim[i] = .19 * handed * (math.sin(bearings[0])-math.sin(bearings[1])) + .08*(2*cue-1)
        elif role == 'lc4':
            stim[i] = .16*math.cos(bearings[i % 2]) + .08*handed*math.sin(turn_target)
    neural = np.tanh(.61*neural + 2.15*(W@neural) + stim)
    return neural


def neural_motor(data, neural):
    # This is a modeled motor decoder, not a reconstructed ventral nerve cord.
    steering = (channel(data,neural,'dna02','right')-channel(data,neural,'dna02','left')
       +.7*(channel(data,neural,'dna01','right')-channel(data,neural,'dna01','left'))
       +.5*(channel(data,neural,'escw','right')-channel(data,neural,'escw','left')))
    return float(np.clip(steering,-1,1))


def run_episode(data, W, trial, choice, collect_trace=False):
    pos=list(trial['start']); heading=trial['heading']
    neural=np.zeros(len(data['ids']),dtype=np.float64)
    dyn12=[0.0]*12
    trajectory=[]; ticks=0; arrived=False
    for tick in range(48):
        bearings=[wrap(math.atan2(loc[1]-pos[1],loc[0]-pos[0])-heading) for loc in trial['stations']]
        selected_bearing=bearings[choice]  # known visual station, not hidden reward
        for _ in range(2):
            neural=network_step(data,W,neural,trial['cue'],bearings,selected_bearing,tick)
        pools=[float(np.mean(neural[i::12])) for i in range(12)]
        dyn12=canonical_dyn12(dyn12,pools,step=tick)
        motor=neural_motor(data,neural)
        # Shared visual navigation independent of connectome; neural modulation
        # is bounded so it can affect paths but cannot supply the answer label.
        turn=float(np.clip(1.9*selected_bearing+.31*motor,-2.6,2.6))
        heading=wrap(heading+.18*turn)
        speed=.86 * (.92 + .08*math.tanh(channel(data,neural,'dnp09')))
        pos[0]=max(-3.85,min(3.85,pos[0]+speed*.18*math.cos(heading)))
        pos[1]=max(-3.0,min(3.0,pos[1]+speed*.18*math.sin(heading)))
        dist=math.dist(pos,trial['stations'][choice]); ticks=tick+1
        if collect_trace:
            trajectory.append({'tick':tick,'x':round(pos[0],5),'y':round(pos[1],5),
               'heading':round(heading,5),'distance_selected':round(dist,5),
               'motor':round(motor,6),'neural':np.round(neural,4).tolist(),
               'dyn12':[round(float(x),5) for x in dyn12]})
        if dist < .42:
            arrived=True; break
    # Environment reward is withheld until terminal arrival.
    reward=int(arrived and choice==trial['correct'])
    return {'reward':reward,'arrived':arrived,'ticks':ticks,'terminal_distance':round(dist,5),'trace':trajectory}


def run_arm(data, arm, seed, counts=PHASE_N, collect_trace=False):
    if arm not in ARMS:raise ValueError(arm)
    source_condition='weight_matched_rewire' if arm=='rewired_learning' else 'no_propagation' if arm=='no_propagation_learning' else 'published_subset'
    W,_ = incoming_matrix(data,source_condition,seed)
    rng=random.Random(79100+seed)
    q=[[.5,.5],[.5,.5]]
    episodes=[]
    for i,tr in enumerate(trial_plan(seed,counts)):
        phase=tr['phase']; cue=tr['cue']
        learning = arm!='no_learning' and not (arm=='frozen_after_training' and phase=='reversal')
        epsilon=(.18 if phase=='train' else .11 if phase=='reversal' else 0) if learning else 0
        if rng.random()<epsilon:
            choice=rng.randrange(2)
        elif abs(q[cue][0]-q[cue][1])<1e-12:
            choice=rng.randrange(2)
        else:
            choice=int(q[cue][1]>q[cue][0])
        result=run_episode(data,W,tr,choice,collect_trace)
        old_q=[row[:] for row in q]
        if learning and phase!='heldout_layout' and result['arrived']:
            # Reward prediction-error update is an external software memory mechanism.
            q[cue][choice]+=.48*(result['reward']-q[cue][choice])
        episodes.append({'episode':i,'phase':phase,'episode_in_phase':tr['episode_in_phase'],
            'cue':cue,'choice':choice,'rewarded_station':tr['correct'],'selected_correctly':int(choice==tr['correct']),
            'reward':result['reward'],'arrived':result['arrived'],'ticks':result['ticks'],
            'terminal_distance':result['terminal_distance'],'q_before':old_q,
            'q_after':[row[:] for row in q], 'stations':tr['stations'],'start':tr['start'],
            'heading':tr['heading'], 'trace':result['trace']})
    metrics={}
    for phase in PHASES:
        arr=[e for e in episodes if e['phase']==phase]
        metrics[phase]={'reward_rate':sum(e['reward'] for e in arr)/len(arr),
           'choice_accuracy':sum(e['selected_correctly'] for e in arr)/len(arr),
           'arrival_rate':sum(e['arrived'] for e in arr)/len(arr),
           'mean_ticks':statistics.mean(e['ticks'] for e in arr)}
    return {'arm':arm,'seed':seed,'metrics':metrics,'episodes':episodes,
            'final_q':q,'source_network_condition':source_condition}


def experiment(seeds=8, counts=PHASE_N, out=None):
    data=load_graph()
    all_runs=[]
    detail={}
    for seed in range(seeds):
        for arm in ARMS:
            run=run_arm(data,arm,seed,counts,collect_trace=(seed==0))
            # Seed 0 preserves full per-tick neural/dyn12 traces; all seeds
            # preserve all episode choices, rewards, Q updates and metrics.
            if seed==0:detail[arm]=run
            else:
                for ep in run['episodes']:ep.pop('trace')
            all_runs.append(run)
    summary={}
    for arm in ARMS:
        summary[arm]={}
        for phase in PHASES:
            vals=[r['metrics'][phase]['reward_rate'] for r in all_runs if r['arm']==arm]
            summary[arm][phase]={'mean':round(statistics.mean(vals),6),
                'sd':round(statistics.pstdev(vals),6),'per_seed':[round(x,6) for x in vals]}
    if out is not None:
        out.mkdir(parents=True,exist_ok=True)
        with (out/'all_runs.jsonl').open('w') as f:
            for r in all_runs:
                f.write(json.dumps(r,sort_keys=True,allow_nan=False)+'\n')
        results={'classification':'real_connectome_derived_42node_graph + ASSUMED neural/motor + SOFTWARE Q learning; NOT biological learning',
            'objective':'Learn cue -> rewarded station A/B, transfer to new positions, adapt after reversal',
            'phase_counts':dict(zip(PHASES,counts)), 'seeds':seeds,'arms':list(ARMS),
            'source_data_sha256':sha256(DATA), 'dyn12_sha256':sha256(HERE.parent/'beastbox'/'dyn12.py'),
            'source_code_sha256':sha256(Path(__file__)),
            'summary':summary, 'episode_log_sha256':sha256(out/'all_runs.jsonl')}
        (out/'results.json').write_text(json.dumps(results,indent=2,sort_keys=True)+'\n')
        return results
    return summary,all_runs


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seeds',type=int,default=8)
    ap.add_argument('--output',type=Path,default=HERE/'learning_demo')
    a=ap.parse_args()
    if a.seeds<1:ap.error('seeds must be >=1')
    result=experiment(a.seeds,out=a.output)
    print(json.dumps(result['summary'],indent=2))

if __name__=='__main__':main()
