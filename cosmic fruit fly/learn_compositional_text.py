"""Supervised symbol-composition experiment with a sandbox-only text actuator.

PRE-REGISTERED BOUNDARY: the communication template (NOUN VERB) and reward
labels are instructor-defined; the fly does not invent a grammar or learn
English. The real-data-derived FlyWire subset is a source of ASSUMED neural
activity, not an evidenced language mechanism. This program performs no host
keyboard events, network calls, or hardware access.
"""
from __future__ import annotations
import hashlib
import json
import math
import random
from functools import lru_cache
from collections import Counter
from pathlib import Path

import numpy as np
from fly_movement import HERE, DATA, load_graph, incoming_matrix, sha256
from quantum_language import load_measurements, quantum_value, inject, DATA as QDATA
from sandbox_ecology import PALETTE, POSITIONS, retinal_image
from sandbox_sensors import SKY_RGB, STONE_RGB
from importlib.util import spec_from_file_location, module_from_spec
_spec = spec_from_file_location("canonical_fruit_dyn12", HERE.parent / "beastbox" / "dyn12.py")
_dyn12_module = module_from_spec(_spec)
_spec.loader.exec_module(_dyn12_module)
canonical_dyn12 = _dyn12_module.update_dyn12

OUT = HERE / 'compositional_language_demo'
NOUNS = ('stick', 'leaf', 'seed', 'nest', 'patch', 'food')
GESTURES = ('notice', 'mark', 'remember')
# Colors are simulated action-sign glyphs, NOT labels or reward bits.
GLYPHS = ((210, 60, 80), (62, 169, 242), (244, 194, 63))
NOUN_TOKENS = ('AX', 'BEX', 'CIR', 'DOM', 'EL', 'FEN')
VERB_TOKENS = ('ZU', 'KA', 'MI')
ARMS = ('original_replay', 'original_off', 'shuffled_replay', 'rewired_replay',
        'no_propagation_replay', 'holistic_phrase_memory', 'no_learning', 'frozen_reversal', 'typing_denied')
BLOCKED = {tuple((i, i % 3)) for i in range(6)}  # 6 novel object x action pairs
BACKGROUND = {tuple(SKY_RGB), (26,65,59), tuple(STONE_RGB)}


def label_tables(seed: int):
    rng = random.Random(774010 + seed)
    nouns = list(NOUN_TOKENS); verbs = list(VERB_TOKENS)
    rng.shuffle(nouns); rng.shuffle(verbs)
    # Cyclic derangements of all six noun and three verb labels: no unchanged label.
    return ({k:v for k,v in zip(NOUNS,nouns)}, {k:v for k,v in zip(GESTURES,verbs)}), ({k:nouns[(i+1)%6] for i,k in enumerate(NOUNS)}, {k:verbs[(i+1)%3] for i,k in enumerate(GESTURES)})


def swatch(gesture_idx: int) -> np.ndarray:
    image = np.zeros((8,8,3), dtype=np.uint8)
    image[:] = GLYPHS[gesture_idx]
    return image


@lru_cache(maxsize=6000)
def sense_pixels(noun: str, pose: tuple[float,float], gesture_idx: int) -> tuple[np.ndarray, np.ndarray]:
    """Only simulated egocentric camera pixels and drawn gesture pixels are returned."""
    rgb = retinal_image(pose, 0.0, {noun:POSITIONS[noun]})
    return rgb, swatch(gesture_idx)


def extract_features(rgb: np.ndarray, glyph: np.ndarray):
    """No PALETTE lookup; image segmentation uses only background RGB exclusions."""
    flat = rgb.reshape(-1,3)
    fg = np.ones(flat.shape[0], dtype=bool)
    for bg in BACKGROUND:
        fg &= ~np.all(flat == bg, axis=1)
    if not np.any(fg):
        raise ValueError('NO_VISIBLE_OBJECT')
    colors,counts=np.unique(flat[fg],axis=0,return_counts=True)
    noun_rgb=tuple(int(x) for x in colors[int(np.argmax(counts))])
    gesture_rgb = tuple(int(x) for x in glyph[4,4])
    return tuple(int(x) for x in noun_rgb), gesture_rgb


class Learner:
    def __init__(self, mode: str):
        self.mode = mode
        self.nouns: dict[tuple[int,...],str] = {}
        self.verbs: dict[tuple[int,...],str] = {}
        self.phrases: dict[tuple[tuple[int,...],tuple[int,...]], str] = {}
        self.updates = 0

    def predict(self, obs: tuple[tuple[int,...],tuple[int,...]]) -> str:
        if self.mode == 'no_learning':
            return '<UNK>'
        if self.mode == 'holistic_phrase_memory':
            return self.phrases.get(obs,'<UNK>')
        a,b=obs
        if a not in self.nouns or b not in self.verbs:
            return '<UNK>'
        return self.nouns[a]+' '+self.verbs[b]

    def teach(self, obs, words: str, enabled: bool=True):
        if not enabled or self.mode == 'no_learning':
            return
        a,b=obs
        one,two=words.split()
        if self.mode == 'holistic_phrase_memory':
            self.phrases[(a,b)] = words
        else:
            self.nouns[a] = one
            self.verbs[b] = two
        self.updates+=1


class Terminal:
    def __init__(self, enabled: bool):
        self.enabled=enabled
        self.tokens=[]
    def emit(self, phrase: str):
        if not self.enabled:
            return 'DENIED:TYPE_TOKEN'
        tokens=phrase.split()
        if len(tokens)!=2 or tokens[0] not in NOUN_TOKENS or tokens[1] not in VERB_TOKENS:
            return 'DENIED:UNKNOWN_TOKEN'
        if len(self.tokens)>=128:
            return 'DENIED:CAPACITY'
        self.tokens.append(phrase)
        return 'TYPE:'+phrase


def trial_steps(data, W, records, noun, gesture_idx, seed, sample, qmode, trace):
    # The environment knows target placement; the learner receives raster bytes only.
    rng=random.Random(600019+seed*23099+sample*59)
    px,py=POSITIONS[noun]
    side=rng.uniform(-.065,.065)
    state=np.zeros(42,dtype=np.float64)
    dyn=[0.0]*12
    snapshots=[]
    qsum=0.0
    last=None
    for tick in range(7):
        pose=(round(px-1.18+(tick*.15),6),round(py+side,6))
        rgb,glyph=sense_pixels(noun,pose,gesture_idx)
        obs=extract_features(rgb,glyph)
        inp=np.zeros(42,dtype=np.float64)
        # Computation assumptions; does not encode truth label or teacher word.
        col=(sum(obs[0])/765.0)*2.-1.
        lat=(obs[0][0]-obs[0][2])/255.
        for i,(role,s) in enumerate(zip(data['roles'],data['sides'])):
            if role in ('lplc2','lc4'):
                inp[i]=(.16*col+.09*lat*(1 if s=='left' else -1))
        qval,job=quantum_value(records,tick+sample*7,qmode,seed) if qmode!='off' else (0.0,None)
        if qval: inp=inject(inp,data['roles'],data['sides'],qval)
        state=np.tanh(.61*state+2.15*(W@state)+inp)
        state=np.tanh(.61*state+2.15*(W@state)+inp)
        pools=[float(np.mean(state[i::12])) for i in range(12)]
        dyn=canonical_dyn12(dyn,pools,step=tick+sample*7)
        qsum+=abs(qval)
        last=obs
        if trace:
            snapshots.append({'tick':tick,'pose':pose,'neural':np.round(state,5).tolist(),
                'dyn12':[round(x,5) for x in dyn], 'quantum':qval,'job':job,
                'visible_pixels':int(np.count_nonzero(np.any(rgb != SKY_RGB,axis=2))),
                'color_rgb':obs[0], 'glyph_rgb':obs[1]})
    return last,qsum/7,round(float(np.mean(np.abs(state))),7),snapshots


def run_one(seed: int, arm: str, keep_trace: bool=False):
    if arm not in ARMS: raise ValueError(arm)
    data=load_graph()
    condition='weight_matched_rewire' if arm=='rewired_replay' else 'no_propagation' if arm=='no_propagation_replay' else 'published_subset'
    W,_=incoming_matrix(data,condition,seed)
    qmode='off' if arm=='original_off' else 'shuffled' if arm=='shuffled_replay' else 'replay'
    records=load_measurements() if qmode!='off' else None
    mode='holistic_phrase_memory' if arm=='holistic_phrase_memory' else 'no_learning' if arm=='no_learning' else 'factorized'
    learner=Learner(mode)
    terminal=Terminal(arm!='typing_denied')
    before,after=label_tables(seed)
    train=[(i,j) for i in range(6) for j in range(3) if (i,j) not in BLOCKED]
    test=sorted(BLOCKED)
    rng=random.Random(8088+seed)
    rng.shuffle(train);rng.shuffle(test)
    phase_lists=[('train',train,before,True),('retained',train,before,False),
                 ('novel',test,before,False),('reversal_train',train,after,arm!='frozen_reversal'),
                 ('reversal_retained',train,after,False),('reversal_novel',test,after,False)]
    tally={p:{'correct':0,'total':0,'unknown':0,'typed':0,'recognized':0} for p,_,_,_ in phase_lists}
    traces=[];qvals=[];nvals=[];trial_index=0
    for phase,pairs,labels,update in phase_lists:
        for i,j in pairs:
            noun,gesture=NOUNS[i],GESTURES[j]
            obs,q,n,frames=trial_steps(data,W,records,noun,j,seed,trial_index,qmode,keep_trace)
            expected=labels[0][noun]+' '+labels[1][gesture]
            # Predict BEFORE feedback. Testing gets NO feedback or update.
            prediction=learner.predict(obs)
            approved=terminal.emit(prediction) if prediction!='<UNK>' else 'DENIED:UNKNOWN_TOKEN'
            ok=prediction==expected and approved.startswith('TYPE:')
            tally[phase]['recognized']+=int(prediction==expected)
            tally[phase]['correct']+=int(ok)
            tally[phase]['total']+=1
            tally[phase]['unknown']+=int(prediction=='<UNK>')
            tally[phase]['typed']+=int(approved.startswith('TYPE:'))
            if update:
                learner.teach(obs,expected)
            if keep_trace:
                traces.append({'trial':trial_index,'phase':phase,'noun':noun,'gesture':gesture,
                    'target':expected,'prediction':prediction,'approved':approved,
                    'reward':int(ok),'features':obs,'teacher_feedback_provided':bool(update),
                    'snapshots':frames})
            qvals.append(q);nvals.append(n)
            trial_index+=1
    return {'seed':seed,'arm':arm,'phase_metrics':tally,'learned_nouns':len(learner.nouns),
            'learned_verbs':len(learner.verbs),'memorized_phrases':len(learner.phrases),
            'updates':learner.updates,'typed_count':len(terminal.tokens),
            'mean_abs_quantum_drive':round(float(np.mean(qvals)),8),
            'mean_abs_neural_state':round(float(np.mean(nvals)),8),
            'trace':traces if keep_trace else []}


def run_experiment(seeds=8,out=OUT):
    if not isinstance(seeds,int) or seeds<1:raise ValueError('seeds must be positive')
    out.mkdir(parents=True,exist_ok=True)
    rows=[run_one(s,a,keep_trace=(s==0 and a in ('original_replay','original_off')))
          for s in range(seeds) for a in ARMS]
    with (out/'runs.jsonl').open('w',encoding='utf8') as f:
        for row in rows:f.write(json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
    summary={}
    for a in ARMS:
        rs=[r for r in rows if r['arm']==a]
        summary[a]={phase:{'correct':sum(r['phase_metrics'][phase]['correct'] for r in rs),
                           'total':sum(r['phase_metrics'][phase]['total'] for r in rs),
                           'unknown':sum(r['phase_metrics'][phase]['unknown'] for r in rs),
                           'recognized':sum(r['phase_metrics'][phase]['recognized'] for r in rs)}
                    for phase in ('train','retained','novel','reversal_train','reversal_retained','reversal_novel')}
        summary[a]['mean_abs_neural_state']=round(float(np.mean([r['mean_abs_neural_state'] for r in rs])),7)
    first=next(r for r in rows if r['seed']==0 and r['arm']=='original_replay')['trace']
    off=next(r for r in rows if r['seed']==0 and r['arm']=='original_off')['trace']
    neural_delta=round(float(np.mean([abs(x-y) for a,b in zip(first,off)
        for fa,fb in zip(a['snapshots'],b['snapshots'])
        for x,y in zip(fa['neural'],fb['neural'])])),8)
    result={'classification':'software supervised factorized associative learning; virtual camera and artificial gesture pixels; no new grammar or biological language',
            'predeclared_holdout':sorted([list(v) for v in BLOCKED]), 'teacher':'two-token supervision on 12 of 18 combinations; no labels in test; all symbols seen in training',
            'reversal':'cyclic derangement of both six object labels and three gesture labels; retrain same 12 pairs',
            'seeds':seeds,'arms':list(ARMS),'summary':summary,
            'source_sha256':{'flywire_derived_subset':sha256(DATA),'ibm_nine_replay':sha256(QDATA)},
            'code_sha256':{x:sha256(HERE/x) for x in ('learn_compositional_text.py','quantum_language.py','fly_movement.py','run_sensor_quest.py','sandbox_ecology.py')},
            'ledger_sha256':sha256(out/'runs.jsonl'),'seed0_neural_delta_quantum_on_off':neural_delta,
            'authority':'terminal in local data only; no host keyboard, network, shell, or actuators',
            'license':'FlyWire-derived subset noncommercial CC BY-NC 4.0'}
    (out/'results.json').write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({'runs':len(rows),'summary':summary,'seed0_neural_delta':neural_delta,
        'ledger_sha256':result['ledger_sha256']},indent=2))
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--seeds',type=int,default=8);p.add_argument('--output',type=Path,default=OUT)
    a=p.parse_args();run_experiment(a.seeds,a.output)
