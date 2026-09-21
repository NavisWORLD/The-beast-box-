"""New v2 foraging task: 2D rendered camera -> neural/CST -> memory -> action.

The source-derived anatomical subset is fixed. All sensory, dynamics, and
software Q-learning parameters are assumptions; rewards are terminal only.
Old experiment and evidence are never overwritten.
"""
from __future__ import annotations
import argparse
import json
import math
import random
import statistics
from pathlib import Path
import numpy as np
from sandbox_sensors import camera, interpret_camera, odor, collision, wrap, OBSTACLES
from fly_movement import DATA, HERE, incoming_matrix, load_graph, channel, sha256
from functools import lru_cache
import importlib.util

@lru_cache(maxsize=1)
def _dyn12_function():
    path=HERE.parent/'beastbox'/'dyn12.py'
    if not path.is_file():raise FileNotFoundError(path)
    spec=importlib.util.spec_from_file_location('fruitfly_sensor_canonical_dyn12',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod.update_dyn12


def canonical_dyn12(state, drive, step):
    return _dyn12_function()(state,drive,step=step)

ARMS=('real_wiring_learning','rewired_learning','no_propagation_learning','frozen_after_training','no_learning')
PHASES=('train','heldout_layout','reversal')
COUNTS=(36,18,22)
OUT=HERE/'sensor_quest_demo'


def trial_plan(seed: int, counts=COUNTS):
    rng=random.Random(935001+seed)
    rule=rng.randrange(2)
    for phase,count in zip(PHASES,counts):
        for index in range(count):
            if phase=='train':stations=((-2.62,1.65),(2.62,1.65))
            elif phase=='heldout_layout':stations=((2.68,1.45),(-2.56,1.45))
            else:stations=((2.56,-1.48),(-2.6,1.54))
            cue=rng.randrange(2)
            yield {'phase':phase,'phase_index':index, 'cue':cue,
                   'rewarded_station':cue^rule^int(phase=='reversal'),
                   'start':(rng.uniform(-.26,.26),-2.28+rng.uniform(-.09,.09)),
                   'heading':rng.uniform(-math.pi, math.pi),'stations':stations}


def encoded_stim(data, senses, choice):
    v=np.zeros(len(data['ids']),dtype=np.float64)
    chosen=senses['vision'][choice]
    visible=float(chosen['seen'])
    visual_bearing=float(chosen['bearing'] or 0.)
    scent=senses['odor'][choice]
    lateral=scent[2]-scent[1]
    for i,(role,side) in enumerate(zip(data['roles'],data['sides'])):
        s=1 if side=='left' else -1
        if role=='lplc2':v[i]=.28*visible*math.sin(visual_bearing)*s + .22*lateral*s
        elif role=='lc4':v[i]=.29*visible*math.cos(visual_bearing)+.16*float(senses['touch'])
    return v


def neural_motor(data, neural):
    steer=(channel(data,neural,'dna02','right')-channel(data,neural,'dna02','left')
           +.7*(channel(data,neural,'dna01','right')-channel(data,neural,'dna01','left'))
           +.5*(channel(data,neural,'escw','right')-channel(data,neural,'escw','left')))
    return float(np.clip(steer,-1,1))


def run_episode(data,W,trial,choice,trace=False, max_ticks=105):
    pos=list(trial['start']);heading=trial['heading'];neural=np.zeros(len(data['ids']))
    dyn12=[0.]*12;prev_touch=False; path=[]; arrived=False; collisions=0; visual_frames=0
    last_target_bearing=None
    for tick in range(max_ticks):
        sensor_pose=(round(pos[0],7),round(pos[1],7),round(heading,7))
        pixels=camera(pos,heading,trial['stations'])
        vision=interpret_camera(pixels)
        scents=odor(pos,heading,trial['stations'])
        sensors={'vision':vision,'odor':scents,'touch':prev_touch,'heading':round(heading,5)}
        stim=encoded_stim(data,sensors,choice)
        for _ in range(2):neural=np.tanh(.61*neural+2.15*(W@neural)+stim)
        pools=[float(np.mean(neural[i::12])) for i in range(12)]
        dyn12=canonical_dyn12(dyn12,pools,step=tick)
        motor=neural_motor(data,neural)
        detected=vision[choice]
        visual_frames+=int(detected['seen'])
        if detected['seen']:
            bearing=float(detected['bearing']);last_target_bearing=bearing
        else:
            # No direct landmark coordinate: scan until vision sees selected marker.
            # Lateral station-specific odor is a weak alternate steering channel.
            lateral=scents[choice][2]-scents[choice][1]
            bearing=(.34 if last_target_bearing is None else .19)* (1 if last_target_bearing is None or last_target_bearing>=0 else -1) + .5*lateral
        turn=np.clip(1.7*bearing+.18*motor,-1.5,1.5)
        heading=wrap(heading+float(turn)*.31)
        speed=.16*(.92+.08*math.tanh(channel(data,neural,'dnp09')))
        next_pos=[pos[0]+speed*math.cos(heading),pos[1]+speed*math.sin(heading)]
        contact=collision(pos,next_pos)
        if contact:
            collisions+=1
            heading=wrap(heading+.47)
        else:pos=next_pos
        prev_touch=contact
        # ONLY terminal contact with a visually neutral station reveals reward.
        dist=math.dist(pos,trial['stations'][choice]);arrived=dist<.38
        if trace:
            path.append({'tick':tick,'x':round(pos[0],5),'y':round(pos[1],5),
              'heading':round(heading,5),'speed':round(speed,5),'turn':round(float(turn),5),
              'sensor_pose':sensor_pose,
              'vision':vision,'odor':scents,'touch':contact,
              'motor':round(motor,5),'dyn12':[round(float(x),5) for x in dyn12],
              'neural':[round(float(x),4) for x in neural], 'dist_selected':round(dist,5)})
        if arrived:break
    reward=int(arrived and choice==trial['rewarded_station'])
    return {'reward':reward,'arrived':arrived,'ticks':tick+1,'terminal_distance':round(dist,5),
            'visual_frames':visual_frames,'collisions':collisions,'trace':path}


def run_arm(data,arm,seed,counts=COUNTS,trace=False):
    if arm not in ARMS:raise ValueError(arm)
    condition='weight_matched_rewire' if arm=='rewired_learning' else 'no_propagation' if arm=='no_propagation_learning' else 'published_subset'
    W,_=incoming_matrix(data,condition,seed)
    rng=random.Random(79100+seed)
    q=[[.5,.5],[.5,.5]]; episodes=[]
    for i,tr in enumerate(trial_plan(seed,counts)):
        phase=tr['phase'];cue=tr['cue']
        learning=arm!='no_learning' and not (arm=='frozen_after_training' and phase=='reversal')
        epsilon=(.18 if phase=='train' else .11 if phase=='reversal' else 0) if learning else 0
        if rng.random()<epsilon or abs(q[cue][0]-q[cue][1])<1e-12:choice=rng.randrange(2)
        else:choice=int(q[cue][1]>q[cue][0])
        result=run_episode(data,W,tr,choice,trace)
        old_q=[row[:] for row in q]
        if learning and phase!='heldout_layout' and result['arrived']:
            q[cue][choice]+=.48*(result['reward']-q[cue][choice])
        episodes.append({'episode':i,'phase':phase,'phase_index':tr['phase_index'],
           'cue':cue,'choice':choice,'rewarded_station':tr['rewarded_station'],
           'reward':result['reward'],'arrived':result['arrived'],'ticks':result['ticks'],
           'collisions':result['collisions'],'visual_frames':result['visual_frames'],
           'terminal_distance':result['terminal_distance'],'start':tr['start'],
           'heading':tr['heading'],'stations':tr['stations'],'q_before':old_q,
           'q_after':[row[:] for row in q], 'trace':result['trace']})
    metrics={}
    for phase in PHASES:
        rows=[e for e in episodes if e['phase']==phase]
        metrics[phase]={k:sum(float(e[k]) for e in rows)/len(rows) for k in ('reward','arrived','ticks','collisions','visual_frames')}
    return {'arm':arm,'seed':seed,'metrics':metrics,'episodes':episodes}


def experiment(seeds=4,counts=COUNTS,out=OUT):
    data=load_graph(); runs=[run_arm(data,arm,seed,counts,trace=(seed==0)) for seed in range(seeds) for arm in ARMS]
    summary={}
    for arm in ARMS:
        summary[arm]={}
        for phase in PHASES:
            ar=[r['metrics'][phase] for r in runs if r['arm']==arm]
            summary[arm][phase]={metric:{'mean':round(statistics.mean(r[metric] for r in ar),6),
                'sd':round(statistics.pstdev(r[metric] for r in ar),6)} for metric in ('reward','arrived','ticks','collisions','visual_frames')}
    out.mkdir(parents=True,exist_ok=True)
    with (out/'runs.jsonl').open('w') as f:
        for r in runs:f.write(json.dumps(r,sort_keys=True,allow_nan=False)+'\n')
    results={'classification':'REAL FlyWire-derived bounded graph + COMPUTATIONAL neural/vision/motor + SOFTWARE Q memory',
       'sensor_contract':'egocentric 96x64 RGB virtual camera segmented after rasterization; station odors; tactile contact; heading; no reward label before terminal station contact',
       'source_hash':sha256(DATA),'code_hash':sha256(Path(__file__)),
       'sensor_code_hash':sha256(HERE/'sandbox_sensors.py'), 'dyn12_hash':sha256(HERE.parent/'beastbox'/'dyn12.py'),
       'episode_log_hash':sha256(out/'runs.jsonl'), 'arms':ARMS,'phases':dict(zip(PHASES,counts)),
       'seeds':seeds,'summary':summary,'physical_authority':'none; virtual arena only',
       'source_license':'CC BY-NC 4.0; commercial use not granted'}
    (out/'results.json').write_text(json.dumps(results,sort_keys=True,indent=2,allow_nan=False)+'\n')
    return results


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--seeds',type=int,default=4);ap.add_argument('--output',type=Path,default=OUT)
    a=ap.parse_args();print(json.dumps(experiment(a.seeds,out=a.output)['summary'],indent=2))
