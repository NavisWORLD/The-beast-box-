"""Longer *scripted-goal* sandbox cycle with active vision, 42-node neural adapter,
canonical dyn12, gated construction, growth, and software-agent reproduction.

No biological agency or biological reproduction is claimed. All decisions to
sequence objectives are authored by this experimenter; navigation is sensor-
driven. Each step is auditable; physical/host action capability is always NONE.
"""
from __future__ import annotations
import argparse, json, math, random, statistics
from pathlib import Path
import numpy as np
from sandbox_sensors import wrap, collision
from sandbox_ecology import (ACTIONS, POSITIONS, present, sense, retinal_image,
                             interpret_retina, apply_action)
from fly_movement import HERE, DATA, load_graph, incoming_matrix, channel, sha256
from run_sensor_quest import canonical_dyn12, neural_motor
from quantum_language import load_measurements, quantum_value, inject, type_event, DATA as QUANTUM_DATA

OUT = HERE/'build_grow_demo'
ARMS = ('real_wiring','rewired','no_propagation','build_disabled','reproduction_disabled')
GOALS = (('stick','pickup'),('nest','place'),('leaf','pickup'),('nest','place'),
         ('nest','build'),('seed','pickup'),('patch','plant'),('patch','grow'),
         ('food','feed'),('nest','reproduce'),('food','offspring_feed'))
DEFAULT_ENABLED = frozenset(ACTIONS)
MAX_TICKS_PER_GOAL = 155


def stimulus(data, obs, goal):
    ret=obs['objects'][goal]
    seen=float(ret['seen']); b=float(ret['bearing'] or 0.)
    lat=float(obs['odor'][2]-obs['odor'][1]); touch=float(obs['touch'])
    out=np.zeros(len(data['ids']),dtype=np.float64)
    for i,(role,side) in enumerate(zip(data['roles'],data['sides'])):
        sign=1 if side=='left' else -1
        if role=='lplc2': out[i]=.3*seen*math.sin(b)*sign+.18*lat*sign
        elif role=='lc4': out[i]=.35*seen*math.cos(b)+.12*touch
    return out


def initial_state():
    return {'inventory':[],'removed':set(),'deposited':set(), 'nest_built':False,
            'planted':False,'plant_tick':None,'grown':False,'energy':0,'offspring':None,'typed_words':[]}


def snapshot(state):
    return {'inventory':list(state['inventory']),'removed':sorted(state['removed']),
      'deposited':sorted(state['deposited']),'nest_built':state['nest_built'],
      'planted':state['planted'],'grown':state['grown'],'energy':state['energy'],
      'offspring': dict(state['offspring']) if state['offspring'] else None,
      'typed_words': list(state['typed_words'])}


def simulate(seed=0, arm='real_wiring', enabled=DEFAULT_ENABLED, trace=False,
             max_ticks_per_goal=MAX_TICKS_PER_GOAL, quantum_mode='off', typing=False):
    if arm not in ARMS: raise ValueError(arm)
    if not set(enabled) <= set(ACTIONS): raise ValueError('unknown action requested')
    data=load_graph()
    condition='weight_matched_rewire' if arm=='rewired' else 'no_propagation' if arm=='no_propagation' else 'published_subset'
    W,_=incoming_matrix(data,condition,seed)
    allowed=set(enabled)
    if arm=='build_disabled': allowed.discard('build')
    if arm=='reproduction_disabled': allowed.discard('reproduce')
    allowed=frozenset(allowed)
    quantum_records=load_measurements() if quantum_mode != 'off' else None
    rng=random.Random(50900+seed)
    pos=[-2.8,-1.91]
    heading=wrap(rng.uniform(-.28,.28))
    neural=np.zeros(42,dtype=np.float64)
    dyn12=[0.]*12
    state=initial_state()
    events=[]; frames=[];steps=0; collisions=0; success=[]
    prev_touch=False; energy_start=state['energy']
    quantum_total=0.0; quantum_steps=0; quantum_jobs=set(); typed_events=[]
    for goal_index,(goal,terminal_action) in enumerate(GOALS):
        completed=False
        last_bearing=None
        for local in range(max_ticks_per_goal):
            shown=present(state)
            if goal not in shown:
                events.append({'tick':steps,'event':'BLOCKED:GOAL_NOT_PRESENT', 'goal':goal})
                break
            sensor_pose=(round(pos[0],7),round(pos[1],7),round(heading,7))
            obs=sense(sensor_pose[:2],sensor_pose[2],shown,goal,prev_touch)
            stim=stimulus(data,obs,goal)
            q_value,q_job=quantum_value(quantum_records,steps,quantum_mode,seed) if quantum_records is not None else (0.0,None)
            stim=inject(stim,data['roles'],data['sides'],q_value) if q_value else stim
            quantum_total+=abs(q_value);quantum_steps+=1
            if q_job:quantum_jobs.add(q_job)
            for _ in range(2): neural=np.tanh(.61*neural+2.15*(W@neural)+stim)
            pools=[float(np.mean(neural[i::12])) for i in range(12)]
            dyn12=canonical_dyn12(dyn12,pools,step=steps)
            motor=neural_motor(data,neural)
            detected=obs['objects'][goal]
            near=math.dist(pos,POSITIONS[goal])<.31
            action='scan'; turn=0.; speed=0.
            # Script chooses a *goal name*, but movement uses ONLY visible
            # pixel-bearing + simulated antenna differential and touch.
            if near:
                if terminal_action=='grow' and state['planted'] and steps-state['plant_tick']<12:
                    action='rest'
                else:
                    action=terminal_action
            elif detected['seen']:
                b=float(detected['bearing']);last_bearing=b
                turn=float(np.clip(1.75*b+.10*motor,-1.5,1.5))
                speed=.105 if abs(b)>.33 else .19
                action='turn' if abs(b)>.33 else 'move'
            else:
                lateral=obs['odor'][2]-obs['odor'][1]
                # A scan searches for the visual target; nonreward odor nudges
                # scan direction, not a privileged goal coordinate.
                turn=.72 + .4*lateral
                if last_bearing is not None:
                    turn=.32*(1 if last_bearing>=0 else -1)+.35*lateral
                action='scan'
            heading=wrap(heading+turn*.35)
            next_pos=[pos[0]+speed*math.cos(heading),pos[1]+speed*math.sin(heading)]
            contact=collision(pos,next_pos)
            if contact and speed>0:
                collisions+=1; heading=wrap(heading+.28)
            else:pos=next_pos
            if goal_index==len(GOALS)-1 and state['offspring'] is not None:
                state['offspring']['pos']=list(pos)
                state['offspring']['age']+=1
            prev_touch=contact
            event=None
            if near:
                event=apply_action(state,action,pos,allowed,steps)
                if event.startswith('DENIED:') or event.startswith('FAILED:'):
                    events.append({'tick':steps,'event':event,'goal':goal})
                    if event.startswith('DENIED:'): break
                elif event not in ('REST',):
                    events.append({'tick':steps,'event':event,'goal':goal})
                    completed=True
            typed_event=type_event(state,event,allowed) if typing else None
            if typed_event is not None:
                typed_events.append({'tick':steps,'event':typed_event,'cause':event})
            if trace:
                frames.append({'tick':steps,'stage':goal_index,'goal':goal,'action':action,
                    'x':round(pos[0],5),'y':round(pos[1],5),'heading':round(heading,5),
                    'sensor_pose':sensor_pose,'shown':list(shown),'vision':obs['objects'],
                    'odor':obs['odor'],'touch':contact,'speed':round(speed,5),
                    'motor':round(motor,5),'quantum_value':q_value,'quantum_job':q_job,
                    'typed_event':typed_event,'dyn12':[round(float(x),5) for x in dyn12],
                    'neural':[round(float(x),5) for x in neural],
                    'world':snapshot(state),'event':event})
            steps+=1
            if completed and event=='REPRODUCE:SIMULATED_OFFSPRING':
                events.append({'tick':steps, 'event':'REGROW:FOOD_FOR_OFFSPRING', 'goal':'food'})
                neural=np.zeros(42,dtype=np.float64)
                dyn12=[0.]*12
                heading=wrap(heading+.17)
            if completed:break
        success.append(bool(completed))
        if not completed:
            events.append({'tick':steps,'event':'STAGE_FAILED:'+terminal_action,'goal':goal})
            # Explicit fail-closed: cannot skip a missing resource to spawn offspring.
            break
    result={'arm':arm,'seed':seed,'steps':steps,'collisions':collisions,
       'stage_success':success,'stages_completed':sum(success),
       'nest_built':state['nest_built'],'grown':state['grown'],
       'offspring_spawned':state['offspring'] is not None,
       'offspring_fed':bool(state['offspring'] and state['offspring']['fed']),
       'events':events,'final':snapshot(state),'trace':frames,
       'quantum_mode':quantum_mode,'quantum_jobs':sorted(quantum_jobs),
       'mean_abs_quantum_drive':round(quantum_total/max(1,quantum_steps),8),
       'neural_mean_abs': round(float(np.mean(np.abs(neural))),8),
       'typed_events':typed_events,'typed_word_count':len(state['typed_words']),
       'classification':'real source-derived anatomical subset; assumed dynamics, sensors, software goal policy and reproduction',
       'enabled_actions':sorted(allowed),'world':'closed sandbox; no host/network/shell/actuator authority'}
    return result


def experiment(seeds=4,out=OUT,max_ticks_per_goal=MAX_TICKS_PER_GOAL):
    out.mkdir(parents=True, exist_ok=True)
    runs=[simulate(s,arm,trace=(arm=='real_wiring'),max_ticks_per_goal=max_ticks_per_goal)
          for s in range(seeds) for arm in ARMS]
    with (out/'runs.jsonl').open('w') as f:
        for r in runs: f.write(json.dumps(r,sort_keys=True,allow_nan=False)+'\n')
    summary={arm: {k:{'mean':round(statistics.mean(float(r[k]) for r in runs if r['arm']==arm),6),
       'sd':round(statistics.pstdev(float(r[k]) for r in runs if r['arm']==arm),6)}
       for k in ('steps','stages_completed','nest_built','grown','offspring_spawned','offspring_fed','collisions')} for arm in ARMS}
    result={'source_data_sha256':sha256(DATA),'code_sha256':sha256(Path(__file__)),
       'sensor_code_sha256':sha256(HERE/'sandbox_ecology.py'),
       'dyn12_sha256':sha256(HERE.parent/'beastbox'/'dyn12.py'),
       'run_ledger_sha256':sha256(out/'runs.jsonl'), 'seeds':seeds,'arms':ARMS,
       'max_ticks_per_goal':max_ticks_per_goal,'summary':summary,
       'license':'FlyWire-derived input CC BY-NC 4.0: noncommercial, attribution required',
       'task_policy':'hand-authored sequential goals, pixel/odor-driven navigation; not emergent planning',
       'reproduction':'one simulated offspring object if gated; no biology or actual birth'}
    (out/'results.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seeds',type=int,default=4)
    p.add_argument('--output',type=Path,default=OUT)
    p.add_argument('--max-ticks',type=int,default=MAX_TICKS_PER_GOAL)
    a=p.parse_args()
    if a.seeds < 1 or a.max_ticks < 1: p.error('positive seeds and ticks required')
    print(json.dumps(experiment(a.seeds,a.output,a.max_ticks)['summary'],indent=2))
