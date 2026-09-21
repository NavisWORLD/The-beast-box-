"""Cosmic Fruit Fly: controlled three-token symbolic communication task.

Teacher specifies grammar and correct labels. Simulated camera + colored context glyphs
provide input; no labels/rewards enter neural dynamics or decoder before prediction.
The model-derived 42-node signal is measured, NOT the mechanism implementing the
symbol decoder. IBM values replay nine historical summaries, NOT live quantum.
The sandbox 'world gate' only unlocks an in-memory task resource; never host I/O.
"""
from __future__ import annotations
import argparse, hashlib, json, math, random
from functools import lru_cache
from pathlib import Path
import numpy as np
from fly_movement import HERE, DATA, load_graph, incoming_matrix, sha256
from learn_compositional_text import (NOUNS as OLD_NOUNS, GESTURES, GLYPHS, NOUN_TOKENS,
    VERB_TOKENS, sense_pixels, extract_features)
from quantum_language import load_measurements, quantum_value, inject, DATA as QDATA
from sandbox_ecology import POSITIONS, PALETTE
from sandbox_sensors import camera as stone_camera, in_view, FOV, WIDTH, HEIGHT, RANGE, SKY_RGB
from importlib.util import spec_from_file_location, module_from_spec
_s=spec_from_file_location('hard_mode_dyn12',HERE.parent/'beastbox'/'dyn12.py')
_d=module_from_spec(_s); _s.loader.exec_module(_d)
canonical_dyn12=_d.update_dyn12

OUT=HERE/'hard_mode_demo'
NOUNS=OLD_NOUNS+('crystal','water')
ALL_POS=dict(POSITIONS,crystal=(-.55,-1.91),water=(1.77,-1.91))
COLORS=dict(PALETTE,crystal=(224,111,253),water=(98,232,210))
NOUN_CODES=NOUN_TOKENS+('GOL','HIR')
VERB_CODES=VERB_TOKENS
INTENTS=('seek','carry','share')
INTENT_GLYPHS=((233,113,42),(61,234,215),(244,110,182))
INTENT_CODES=('TOR','VEX','WUN')
ARMS=('original_replay','original_off','shuffled_replay','rewired_replay',
      'no_propagation_replay','holistic_memory','no_learning',
      'frozen_reversal','typing_denied','offspring_blank')
# Withhold one context for every noun+gesture pair; factors all appear in training.
HELD=frozenset((i,j,(i+j)%3) for i in range(len(NOUNS)) for j in range(len(GESTURES)))
TRAIN=tuple((i,j,k) for i in range(len(NOUNS)) for j in range(len(GESTURES))
            for k in range(len(INTENTS)) if (i,j,k) not in HELD)
TEST=tuple(sorted(HELD))
assert len(TRAIN)==48 and len(TEST)==24


def label_tables(seed):
    r=random.Random(603019+seed)
    a=list(NOUN_CODES);b=list(VERB_CODES);c=list(INTENT_CODES)
    for group in (a,b,c):r.shuffle(group)
    first=(dict(zip(NOUNS,a)),dict(zip(GESTURES,b)),dict(zip(INTENTS,c)))
    second=(dict(zip(NOUNS,a[1:]+a[:1])),dict(zip(GESTURES,b[1:]+b[:1])),dict(zip(INTENTS,c[1:]+c[:1])))
    return first,second


def expected_phrase(labels,combo):
    i,j,k=combo
    return ' '.join((labels[0][NOUNS[i]],labels[1][GESTURES[j]],labels[2][INTENTS[k]]))


def glyph(rgb):
    out=np.empty((8,8,3),dtype=np.uint8);out[:]=rgb
    return out


@lru_cache(maxsize=64)
def raw_retina(noun):
    pos=ALL_POS[noun]
    pose=(round(pos[0]-1.18,6),round(pos[1],6))
    if noun in POSITIONS:
        rgb,_=sense_pixels(noun,pose,0)
    else:
        rgb=stone_camera(pose,0.,())
        visible,bearing,distance=in_view(pose,0.,pos)
        if not visible: raise RuntimeError('extra category invisible: '+noun)
        yy,xx=np.ogrid[:HEIGHT,:WIDTH]
        cx=round((.5+bearing/FOV)*WIDTH)
        cy=round(HEIGHT*(.52+.2*(1.-distance/RANGE)))
        rad=max(2,round(11/max(1.,distance)))
        rgb[(xx-cx)**2+(yy-cy)**2<=rad**2]=COLORS[noun]
    if not np.any(np.all(rgb==COLORS[noun],axis=2)):
        raise RuntimeError('object occluded before test: '+noun)
    rgb.setflags(write=False)
    return rgb


@lru_cache(maxsize=200)
def observed(noun,j,k,mode,pattern):
    """Reconstruct features from pixels, never from noun or teacher token.

    Partial occlusion and distractor speckles are applied only to the TEST camera.
    Palette prototypes are a documented fixed image-processing calibration, not a
    teacher-label mapping. The two unknown-to-old-project categories get few-shot
    labeled exemplars in TRAIN before held-out pair evaluation.
    """
    rgb=raw_retina(noun).copy()
    if mode=='noisy':
        color=np.array(COLORS[noun],dtype=np.uint8)
        ys,xs=np.where(np.all(rgb==color,axis=2))
        if len(xs):
            # Obscure roughly 20-28% of foreground object pixels without its label.
            rng=random.Random(22500+pattern*71+len(xs))
            indices=list(range(len(xs)));rng.shuffle(indices)
            n=max(1,int(len(xs)*(.20+.04*(pattern%3))))
            rgb[ys[indices[:n]],xs[indices[:n]]]=np.array(SKY_RGB,dtype=np.uint8)
        # Neutral, non-semantic speckles distract the image segmenter.
        rng=random.Random(43100+pattern)
        for _ in range(9):
            y=rng.randint(2,HEIGHT-3); x=rng.randint(2,WIDTH-3)
            rgb[y,x]=(182,182,180)
    # Extract the most supported calibrated object-color cluster from actual RGB.
    flat=rgb.reshape(-1,3).astype(np.int32)
    prototypes=np.array(list(COLORS.values()),dtype=np.int32)
    dist=np.sum((flat[:,None,:]-prototypes[None,:,:])**2,axis=2)
    nearest=np.argmin(dist,axis=1)
    valid=np.min(dist,axis=1)< 23**2
    counts=np.bincount(nearest[valid],minlength=len(COLORS))
    if max(counts)<3: raise ValueError('NO_VISIBLE_OBJECT')
    object_rgb=tuple(map(int,prototypes[np.argmax(counts)]))
    gr=tuple(int(v) for v in glyph(GLYPHS[j])[4,4]); ir=tuple(int(v) for v in glyph(INTENT_GLYPHS[k])[4,4])
    return (object_rgb,gr,ir),rgb


class Decoder:
    def __init__(self,mode='factorized'):
        self.mode=mode;self.maps=[{}, {}, {}]; self.phrases={};self.updates=0
    def predict(self,feat):
        if self.mode=='no_learning':return '<UNK>'
        if self.mode=='holistic':return self.phrases.get(feat,'<UNK>')
        if any(v not in t for t,v in zip(self.maps,feat)):return '<UNK>'
        return ' '.join(t[v] for t,v in zip(self.maps,feat))
    def teach(self,feat,target,enabled=True):
        if not enabled or self.mode=='no_learning':return
        words=target.split()
        if self.mode=='holistic':self.phrases[feat]=target
        else:
            for table,feature,word in zip(self.maps,feat,words):table[feature]=word
        self.updates+=1
    def clone(self):
        n=Decoder(self.mode);n.maps=[dict(m) for m in self.maps]
        n.phrases=dict(self.phrases);n.updates=self.updates
        return n


class Terminal:
    def __init__(self,enabled=True):self.enabled=enabled;self.log=[]
    def emit(self,phrase):
        if not self.enabled:return 'DENIED:TYPE_TOKEN'
        words=phrase.split()
        if len(words)!=3 or not all(w in vocab for w,vocab in zip(words,(NOUN_CODES,VERB_CODES,INTENT_CODES))):
            return 'DENIED:UNKNOWN_TOKEN'
        if len(self.log)>=512:return 'DENIED:CAPACITY'
        self.log.append(phrase);return 'TYPE:'+phrase


class WorldGate:
    """A correct allowed message alone authorizes a named local resource action."""
    def __init__(self):self.unlocked=[];self.denied=0
    def apply(self,request,approved,target,visible):
        if approved!='TYPE:'+request or request!=target or not visible:
            self.denied+=1;return 'LOCKED'
        self.unlocked.append(request)
        return 'UNLOCKED:RESOURCE'


def neural_steps(data,W,records,features,seed,trial_index,qmode,trace):
    state=np.zeros(42,dtype=np.float64);dyn=[0.]*12;shots=[];qval_sum=0.
    rgb,gr,ir=features
    drive=(sum(rgb)/765.)*2.-1.;diff=(rgb[0]-rgb[2])/255.
    drive+=(sum(gr)/765.-.5)*.10+(sum(ir)/765.-.5)*.06
    for t in range(4):
        stim=np.zeros(42,dtype=np.float64)
        for i,(role,side) in enumerate(zip(data['roles'],data['sides'])):
            if role in ('lplc2','lc4'):
                stim[i]=.16*drive+.09*diff*(1 if side=='left' else -1)
        qval,job=quantum_value(records,trial_index*4+t,qmode,seed) if qmode!='off' else (0.,None)
        if qval:stim=inject(stim,data['roles'],data['sides'],qval)
        state=np.tanh(.61*state+2.15*(W@state)+stim)
        pools=[float(np.mean(state[i::12])) for i in range(12)]
        dyn=canonical_dyn12(dyn,pools,step=trial_index*4+t)
        qval_sum+=abs(qval)
        if trace:shots.append({'tick':t,'neural':np.round(state,5).tolist(),
            'dyn12':[round(x,5) for x in dyn], 'quantum':qval,'job':job})
    return round(float(np.mean(np.abs(state))),7),round(qval_sum/4,7),shots


def run_one(seed,arm,keep_trace=False):
    if arm not in ARMS:raise ValueError(arm)
    data=load_graph(); condition=('weight_matched_rewire' if arm=='rewired_replay' else
        'no_propagation' if arm=='no_propagation_replay' else 'published_subset')
    W,_=incoming_matrix(data,condition,seed)
    qmode='off' if arm=='original_off' else 'shuffled' if arm=='shuffled_replay' else 'replay'
    records=load_measurements() if qmode!='off' else None
    mode=('holistic' if arm=='holistic_memory' else 'no_learning' if arm=='no_learning' else 'factorized')
    parent=Decoder(mode);terminal=Terminal(arm!='typing_denied')
    labels,reversed_labels=label_tables(seed)
    train=list(TRAIN);test=list(TEST)
    rng=random.Random(44481+seed);rng.shuffle(train);rng.shuffle(test)
    phases=(('train',train,labels,True,False),('retained',train,labels,False,False),
            ('novel_noise',test,labels,False,True),('reversal_train',train,reversed_labels,arm!='frozen_reversal',False),
            ('reversal_retained',train,reversed_labels,False,False),
            ('reversal_novel_noise',test,reversed_labels,False,True),
            ('offspring_transfer_noise',test,reversed_labels,False,True))
    learner=parent
    metrics={p:{'correct':0,'total':0,'recognized':0,'unlocked':0,'unknown':0} for p,_,_,_,_ in phases}
    traces=[];qvals=[];nvals=[];trial_index=0
    for phase,pairs,table,update,noisy in phases:
        if phase=='offspring_transfer_noise':learner=Decoder(mode) if arm=='offspring_blank' else parent.clone()
        for i,j,k in pairs:
            noun=NOUNS[i]; ob,pixels=observed(noun,j,k,'noisy' if noisy else 'clean',trial_index%3)
            neural,q,snap=neural_steps(data,W,records,ob,seed,trial_index,qmode,keep_trace)
            target=expected_phrase(table,(i,j,k))
            pred=learner.predict(ob)
            approved=terminal.emit(pred) if pred!='<UNK>' else 'DENIED:UNKNOWN_TOKEN'
            # A distinct environment checker enforces the consequence. Never used as a feature.
            world=WorldGate();gate=world.apply(pred,approved,target,True)
            correct=int(gate=='UNLOCKED:RESOURCE')
            metrics[phase]['total']+=1;metrics[phase]['correct']+=correct
            metrics[phase]['recognized']+=int(pred==target)
            metrics[phase]['unlocked']+=len(world.unlocked)
            metrics[phase]['unknown']+=int(pred=='<UNK>')
            if update:learner.teach(ob,target)
            if keep_trace:
                traces.append({'trial':trial_index,'phase':phase,'object':noun,'gesture':GESTURES[j],
                    'intent':INTENTS[k],'pos':list(ALL_POS[noun]), 'features':ob,
                    'predicted':pred,'target':target,'typing':approved,'gate':gate,
                    'reward':correct,'teacher_feedback_provided':update,'noisy_camera':noisy,
                    'camera_sha256':hashlib.sha256(pixels.tobytes()).hexdigest(),
                    'snapshots':snap})
            qvals.append(q);nvals.append(neural);trial_index+=1
    return {'seed':seed,'arm':arm,'phases':metrics,'updates':parent.updates,
        'offspring_inherited':arm!='offspring_blank','typed_count':len(terminal.log),
        'mean_abs_quantum_drive':round(float(np.mean(qvals)),8),
        'mean_abs_neural_state':round(float(np.mean(nvals)),8),
        'trace':traces if keep_trace else []}


def run_experiment(seeds=4,out=OUT):
    if seeds<1:raise ValueError('seeds')
    out.mkdir(parents=True,exist_ok=True)
    rows=[run_one(s,arm,keep_trace=(s==0 and arm in ('original_replay','original_off')))
          for s in range(seeds) for arm in ARMS]
    with (out/'runs.jsonl').open('w',encoding='utf-8') as f:
        for r in rows:f.write(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
    summary={}
    for arm in ARMS:
        chosen=[r for r in rows if r['arm']==arm]
        summary[arm]={phase:{key:sum(r['phases'][phase][key] for r in chosen)
               for key in ('correct','total','recognized','unlocked','unknown')}
               for phase in chosen[0]['phases']}
        summary[arm]['mean_abs_neural_state']=round(float(np.mean([r['mean_abs_neural_state'] for r in chosen])),8)
    t=next(r['trace'] for r in rows if r['seed']==0 and r['arm']=='original_replay')
    off=next(r['trace'] for r in rows if r['seed']==0 and r['arm']=='original_off')
    delta=round(float(np.mean([abs(v-w) for a,b in zip(t,off) for x,y in zip(a['snapshots'],b['snapshots'])
                     for v,w in zip(x['neural'],y['neural'])])),8)
    result={'experiment':'three-token teacher-supervised language task with in-memory resource gate',
        'classifier':'calibrated pixel-color segmenter; seen categories including two added few-shot classes',
        'language_boundary':'fixed three-token grammar and finite vocabulary; no open-ended dialogue',
        'sensory_boundary':'test-only partial sprite occlusion and distractor speckles; not natural photography',
        'brain_boundary':'FlyWire-derived subset computationally simulated, NOT causal input to decoder',
        'quantum_boundary':'nine historical IBM-summary records, replay only, not physiology or full archive',
        'offspring_boundary':'software copy of learned mapping; no inherited weights or biological inheritance',
        'train_count':len(TRAIN),'heldout_count':len(TEST),'seeds':seeds,'arms':ARMS,
        'summary':summary,'source_sha256':{'flywire_subset':sha256(DATA),'ibm_replay':sha256(QDATA)},
        'code_sha256':{name:sha256(HERE/name) for name in ('hard_mode.py','quantum_language.py',
                           'fly_movement.py','sandbox_ecology.py','learn_compositional_text.py')},
        'ledger_sha256':sha256(out/'runs.jsonl'),'seed0_neural_delta_replay_off':delta,
        'authority':'local in-memory terminal and resource gate only; no host keyboard/network/tools',
        'license':'FlyWire-derived subset CC BY-NC 4.0; no commercial release'}
    (out/'results.json').write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({'runs':len(rows),'trials':sum(sum(v['total'] for v in row['phases'].values()) for row in rows),
        'summary':summary,'ledger_sha256':result['ledger_sha256'],'neural_delta':delta},indent=2),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seeds',type=int,default=4)
    p.add_argument('--output',type=Path,default=OUT)
    a=p.parse_args();run_experiment(a.seeds,a.output)
