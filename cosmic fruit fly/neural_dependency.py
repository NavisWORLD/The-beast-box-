"""Causal neural-readout ablation for Cosmic Fruit Fly.

The learned noun-to-token mapping consumes ONLY non-sensory nodes of the 42-node
FlyWire-derived numerical simulation. This deliberately tests whether an active
sensory -> downstream channel is necessary under a fixed downstream decoder.
The role-based encoder, dynamics, nearest-centroid supervised decoder, grammar,
virtual world, and audio/QPU replay are all software assumptions, NOT measured
fly physiology or an independently evolved language mechanism.
"""
from __future__ import annotations
import argparse, hashlib, json, math, random
from pathlib import Path
import numpy as np
from fly_movement import HERE, DATA, load_graph, incoming_matrix, sha256
from hard_mode import (NOUNS, GESTURES, INTENTS, COLORS, ALL_POS, TRAIN, TEST,
                       GLYPHS, INTENT_GLYPHS, label_tables, expected_phrase,
                       Terminal, WorldGate, canonical_dyn12)
from fusion_hard_mode import camera_observation
from audio_linked_fusion import load_linked, audio_value, linked_count_value

OUT = HERE/'neural_dependency_demo'
PHASES = ('train','novel_noise','reversal_train','reversal_novel_noise','offspring_transfer_noise')
ARMS = ('original_no_aux','original_audio_qpu','original_shuffled_audio_qpu',
        'rewired_audio_qpu','no_propagation_audio_qpu','original_audio_only',
        'original_qpu_only','original_no_learning','original_typing_denied',
        'original_offspring_blank')


def raw_retina_code(image:np.ndarray)->np.ndarray:
    """Central sensor's RGB median; no named palette, label or expected code.

    A documented fixed camera fixation (target at center) is used on all arms.
    This is a limited perception task, not an arbitrary-layout detector.
    """
    patch=image[39:49,43:53,:].astype(np.float64)
    return (np.median(patch.reshape(-1,3),axis=0)/255.-.5).astype(np.float64)


def sensory_drive(data:dict, image:np.ndarray)->np.ndarray:
    """Assumed, fixed photoreceptor encoder; ONLY sensory-labeled nodes driven."""
    rgb=raw_retina_code(image)
    stim=np.zeros(42,dtype=np.float64)
    for i,(role,side) in enumerate(zip(data['roles'],data['sides'])):
        if role in ('lplc2','lc4'):
            # Different fixed tuning of three channels, not the target's class ID.
            c=i%3
            side_sign=1. if side=='left' else -1.
            stim[i]=.50*rgb[c]+.085*side_sign*(rgb[(c+1)%3]-rgb[(c+2)%3])
    return stim


def neural_observation(data,W,image,packet,qpu,seed,trial,arm,keep=False):
    """Downstream 24 nodes only; zero propagation -> zero decoder input."""
    stim=sensory_drive(data,image)
    sensory={i for i,r in enumerate(data['roles']) if r in ('lplc2','lc4')}
    downstream=[i for i in range(42) if i not in sensory]
    assert len(sensory)==18 and len(downstream)==24
    state=np.zeros(42,dtype=np.float64);dyn=[0.]*12;snaps=[]
    audio_mode='shuffled' if arm=='original_shuffled_audio_qpu' else ('off' if arm in ('original_no_aux','original_qpu_only') else 'ordered')
    qmode='off' if arm in ('original_no_aux','original_audio_only') else 'histogram'
    for t in range(4):
        tick=trial*4+t
        av,segment=audio_value(packet,tick,audio_mode,seed)
        qv,bits=linked_count_value(qpu,tick,seed,mode=qmode)
        drive=stim.copy()
        # Bounded, source-independent auxiliary values enter sensory nodes only.
        for i in sensory:
            drive[i]+=(av+qv)*(1. if data['sides'][i]=='left' else -1.)
        state=np.tanh(.61*state+2.15*(W@state)+drive)
        dyn=canonical_dyn12(dyn,[float(np.mean(state[i::12])) for i in range(12)],step=tick)
        if keep:
            snaps.append({'tick':t,'neural':np.round(state,5).tolist(),
                          'dyn12':[round(v,5) for v in dyn],
                          'audio':av,'audio_segment':segment,'quantum':qv,
                          'qpu_bits_histogram_surrogate':bits,'bio':0.0,
                          'job':qpu['job_id'] if qmode!='off' else None})
    return state[downstream].copy(),snaps


class LearnedReadout:
    """A small explicit teacher-trained nearest-prototype downstream neural decoder.

    No fixed class-coded weights, no direct camera/true noun at inference, and no
    target entering neural dynamics. Glyph channels are independently supervised.
    """
    def __init__(self):
        self.samples={};self.labels={};self.gestures={};self.intents={};self.updates=0
    def predict(self,hidden,gesture,intent):
        if np.max(np.abs(hidden))<1.e-10 or not self.samples:return '<UNK>'
        candidates=[]
        for noun,vectors in self.samples.items():
            centroid=np.mean(np.stack(vectors),axis=0)
            candidates.append((float(np.linalg.norm(hidden-centroid)),noun))
        noun=min(candidates)[1]
        if noun not in self.labels or gesture not in self.gestures or intent not in self.intents:return '<UNK>'
        return ' '.join((self.labels[noun],self.gestures[gesture],self.intents[intent]))
    def teach(self,hidden,noun,gesture,intent,target):
        if np.max(np.abs(hidden))<1.e-10:return
        n,g,k=target.split()
        self.samples.setdefault(noun,[]).append(hidden.copy())
        self.labels[noun]=n;self.gestures[gesture]=g;self.intents[intent]=k;self.updates+=1
    def clone(self):
        clone=LearnedReadout()
        clone.samples={n:[v.copy() for v in values] for n,values in self.samples.items()}
        clone.labels=self.labels.copy();clone.gestures=self.gestures.copy()
        clone.intents=self.intents.copy();clone.updates=self.updates
        return clone


def run_one(seed:int,arm:str,trace=False):
    if arm not in ARMS:raise ValueError(arm)
    packet,qpu=load_linked();data=load_graph()
    condition=('weight_matched_rewire' if arm=='rewired_audio_qpu' else
               'no_propagation' if arm=='no_propagation_audio_qpu' else 'published_subset')
    W,_=incoming_matrix(data,condition,seed)
    learner=LearnedReadout();parent=learner;terminal=Terminal(enabled=arm!='original_typing_denied')
    labels,rev=label_tables(seed)
    train=list(TRAIN);test=list(TEST)
    random.Random(44481+seed).shuffle(train);random.Random(44482+seed).shuffle(test)
    phases=(('train',train,labels,True,False),('novel_noise',test,labels,False,True),
            ('reversal_train',train,rev,True,False),
            ('reversal_novel_noise',test,rev,False,True),
            ('offspring_transfer_noise',test,rev,False,True))
    metrics={p:{'correct':0,'total':0,'predicted':0} for p in PHASES}
    traces=[];trial=0;nonzero=0
    for phase,combos,table,update,noisy in phases:
        if phase=='offspring_transfer_noise':
            learner=LearnedReadout() if arm=='original_offspring_blank' else parent.clone()
        for i,j,k in combos:
            noun=NOUNS[i]
            # Only virtual camera is supplied to the neural encoder.
            feat,margin,cam_hash,image=camera_observation(noun,j,k,seed,trial,noisy)
            hidden,snaps=neural_observation(data,W,image,packet,qpu,seed,trial,arm,trace)
            nonzero+=int(np.max(np.abs(hidden))>1e-10)
            # Gesture and intent arrive through independent, visible glyph channels.
            gesture=tuple(GLYPHS[j]);intent=tuple(INTENT_GLYPHS[k])
            target=expected_phrase(table,(i,j,k)) # teacher/scorer only
            pred='<UNK>' if arm=='original_no_learning' else learner.predict(hidden,gesture,intent)
            approval=terminal.emit(pred) if pred!='<UNK>' else 'DENIED:UNKNOWN_TOKEN'
            world=WorldGate();gate=world.apply(pred,approval,target,True)
            m=metrics[phase];m['total']+=1;m['correct']+=int(gate=='UNLOCKED:RESOURCE');m['predicted']+=int(pred==target)
            if update and arm!='original_no_learning':learner.teach(hidden,noun,gesture,intent,target)
            if trace:
                traces.append({'seed':seed,'arm':arm,'trial':trial,'phase':phase,'object':noun,
                    'gesture':GESTURES[j],'intent':INTENTS[k],'pos':list(ALL_POS[noun]),
                    'features':[list(f) for f in feat],'margin':margin,'camera_sha256':cam_hash,
                    'raw_retina_code':np.round(raw_retina_code(image),6).tolist(),
                    'hidden_nonzero':bool(np.max(np.abs(hidden))>1e-10),
                    'downstream':np.round(hidden,6).tolist(),'predicted':pred,'target':target,
                    'typing':approval,'gate':gate,'reward':int(gate=='UNLOCKED:RESOURCE'),
                    'teacher_feedback_provided':update,'noisy_camera':noisy,'snapshots':snaps})
            trial+=1
    return {'seed':seed,'arm':arm,'phases':metrics,'updates':parent.updates,
            'typed_count':len(terminal.log),'nonzero_downstream':nonzero,'trace':traces if trace else []}


def run_experiment(seeds=8,out=OUT):
    if seeds<1:raise ValueError('seeds')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for s in range(seeds):
        for arm in ARMS:rows.append(run_one(s,arm,trace=(s==0)))
        print(f'COMPLETE matched seed {s+1}/{seeds}',flush=True)
    ledger=out/'runs.jsonl'
    with ledger.open('w') as f:
        for row in rows:f.write(json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
    summary={}
    for arm in ARMS:
        group=[x for x in rows if x['arm']==arm]
        summary[arm]={p:{k:sum(row['phases'][p][k] for row in group) for k in ('correct','total','predicted')} for p in PHASES}
        summary[arm]['per_seed_novel']=[r['phases']['novel_noise']['correct'] for r in group]
        summary[arm]['per_seed_reversal']=[r['phases']['reversal_novel_noise']['correct'] for r in group]
        summary[arm]['active_neural_trials']=sum(r['nonzero_downstream'] for r in group)
    result={'schema':'cosmic-fruit-fly-neural-dependency-v1','seeds':seeds,'arms':list(ARMS),
        'runs':len(rows),'trials':len(rows)*168,'episodes_per_run':168,
        'summary':summary,'ledger_sha256':sha256(ledger),
        'source_file_sha256':{'flywire_subset':sha256(DATA),
           'audio_packet':sha256(HERE/'data'/'audio_source_feature_packet.json'),
           'qpu_counts':sha256(HERE/'data'/'linked_ibm_marrakesh_counts.json')},
        'mechanism':'Fixed camera fixation -> RGB median -> assumed sensory tuning -> four neural steps -> nonsensory-only nearest-centroid learned noun -> separately learned gesture/intent -> local resource gate',
        'interpretation':'Tests causal dependence on a designed neural relay, not that historical topology is uniquely effective; no biological language, real physiological data or quantum advantage.'}
    (out/'results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'runs':result['runs'],'trials':result['trials'],
        'heldout':{a:[summary[a]['novel_noise']['correct'],summary[a]['novel_noise']['total']] for a in ARMS},
        'ledger_sha256':result['ledger_sha256']},indent=2),flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seeds',type=int,default=8);p.add_argument('--output',type=Path,default=OUT)
    args=p.parse_args();run_experiment(args.seeds,args.output)
