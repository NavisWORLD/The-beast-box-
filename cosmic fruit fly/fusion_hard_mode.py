"""Isolated bio/IBM fusion ablation on the archived Cosmic Fruit Fly task.

Scientific boundaries: real-derived *anatomical subset*, modeled 42-node dynamics,
recorded nine-job IBM summary replay, and explicitly MOCK bio. The 42-node readout
modulates confidence/abstention but is not the learned linguistic decoder. No
personal physiological recording is available, no live QPU, no biological fly.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
from pathlib import Path
import numpy as np
from fly_movement import HERE, DATA, load_graph, incoming_matrix, sha256
from hard_mode import (NOUNS, GESTURES, INTENTS, COLORS, GLYPHS, INTENT_GLYPHS,
                       TRAIN, TEST, label_tables, expected_phrase, raw_retina,
                       Decoder, Terminal, WorldGate, canonical_dyn12)
from quantum_language import DATA as QDATA, load_measurements, quantum_value, inject
from sandbox_sensors import SKY_RGB

OUT = HERE/'fusion_demo'
ARMS = ('baseline', 'quantum_only', 'mock_bio_only', 'mock_fusion',
        'rewired_mock_fusion', 'no_propagation_mock_fusion', 'shuffle_quantum',
        'shuffle_mock_bio', 'holistic_memory', 'frozen_reversal',
        'typing_denied', 'offspring_blank')
PHASES = ('train', 'novel_noise', 'reversal_train', 'reversal_novel_noise',
          'offspring_transfer_noise')
MOCK_BIO_ID = 'SIMULATED_BIO_STREAM/SINE_FIXTURE_V1'
LABELS = ('source-derived-anatomy', 'historical-ibm-summary', 'mock-bio-only')
PROTOTYPES = np.array(list(COLORS.values()), dtype=np.int32)


def bio_sample(seed:int, tick:int, mode:str)->float:
    """Explicitly nonphysiological mock. Shuffling removes temporal alignment."""
    if mode not in ('off','mock','shuffled_mock'):
        raise ValueError('only mock fixtures are permitted without verified bio input')
    if mode=='off': return 0.0
    t = (tick * 37 + 19) % 797 if mode=='shuffled_mock' else tick
    return round(0.48*math.sin(.071*t + seed*.53)+.18*math.cos(.023*t+seed),7)


def normalize_recorded_bio(packet:dict, expected_sha:str):
    """Fail-closed typed input hook. Never generate or log raw personal signals."""
    if not isinstance(packet,dict) or packet.get('origin_class')!='verified_recorded_biosignal':
        raise ValueError('REAL_BIO_UNAVAILABLE: mock or unverified packet')
    if packet.get('source_sha256')!=expected_sha or len(expected_sha)!=64:
        raise ValueError('bio source hash mismatch')
    if packet.get('signal_type') not in ('HR','HRV','GSR','EEG','ECG') or not packet.get('timestamp') or not packet.get('unit'):
        raise ValueError('bio provenance/unit missing')
    x=float(packet['processed_value'])
    if not math.isfinite(x):raise ValueError('bio signal nonfinite')
    return x


def camera_observation(noun:str, j:int, k:int, seed:int, index:int, noisy:bool):
    """Derive classification and ambiguity from pixels; no reward/teacher labels."""
    im = raw_retina(noun).copy()
    # Environment knows physical object for raster occlusion, decoder does not.
    if noisy:
        rng = random.Random(910003 + seed*8807 + index*37)
        fg = np.all(im == COLORS[noun], axis=2)
        ys,xs=np.where(fg)
        candidates=list(range(len(xs))); rng.shuffle(candidates)
        occlusion=.30 + .10*(index%4)
        for ii in candidates[:int(len(xs)*occlusion)]:
            im[ys[ii],xs[ii]] = SKY_RGB
        others=[c for c in COLORS if c != noun]
        target = COLORS[others[rng.randrange(len(others))]]
        for _ in range(1+(index%3)):
            x=rng.randint(5,90);y=rng.randint(13,52)
            rad=rng.choice((2,3,4))
            yy,xx=np.ogrid[:64,:96]
            im[(xx-x)**2+(yy-y)**2 <= rad**2]=target
        for _ in range(10):
            x=rng.randrange(96);y=rng.randrange(64)
            im[y,x]=(170,174,171)
    rgb=im.reshape(-1,3).astype(np.int32)
    dist=np.sum((rgb[:,None,:]-PROTOTYPES[None,:,:])**2,axis=2)
    votes=np.bincount(np.argmin(dist,axis=1)[np.min(dist,axis=1)<23**2],minlength=len(COLORS))
    order=np.argsort(-votes,kind='stable')
    best,second=int(votes[order[0]]),int(votes[order[1]])
    color=tuple(map(int,PROTOTYPES[order[0]]))
    margin=(best-second)/(best+second+1) if best>=3 else 0.0
    feat=(color,tuple(GLYPHS[j]),tuple(INTENT_GLYPHS[k]))
    # GLYPHS are triple RGB tuples, not actual retina labels, and belong to the visible glyph channel.
    return feat, round(margin,7), hashlib.sha256(im.tobytes()).hexdigest(),im


def circuit_response(data:dict, W:np.ndarray, records:list, features:tuple,
                     seed:int, trial:int, qmode:str, bmode:str, keep:bool):
    rgb,gr,ir=features
    state=np.zeros(42,dtype=np.float64);dyn=[0.]*12; shots=[]
    drive=(sum(rgb)/765.)*2.-1.+(sum(gr)/765.-.5)*.10+(sum(ir)/765.-.5)*.06
    diff=(rgb[0]-rgb[2])/255.
    for t in range(4):
        tick=trial*4+t
        stim=np.zeros(42,dtype=np.float64)
        for i,(role,side) in enumerate(zip(data['roles'],data['sides'])):
            if role in ('lplc2','lc4'):
                stim[i]=.16*drive+.09*diff*(1 if side=='left' else -1)
        qval,job = quantum_value(records,tick,qmode,seed) if qmode!='off' else (0.,None)
        bval=bio_sample(seed,tick,bmode)
        if qval: stim=inject(stim,data['roles'],data['sides'],qval)
        # A bounded auxiliary drive into the same visual-role cells, before propagation.
        for i,(role,side) in enumerate(zip(data['roles'],data['sides'])):
            if role in ('lplc2','lc4'):
                stim[i]+=.024*bval*(1. if side=='left' else -1.)
        state=np.tanh(.61*state+2.15*(W@state)+stim)
        dyn=canonical_dyn12(dyn,[float(np.mean(state[i::12])) for i in range(12)],step=tick)
        if keep:
            shots.append({'tick':t,'neural':np.round(state,5).tolist(),
                'dyn12':[round(z,5) for z in dyn],'quantum':qval,'job':job,
                'bio':bval})
    # Neural readout enters confidence gate, never supplies noun/gesture/intent target.
    visual=np.array([state[i] for i,r in enumerate(data['roles']) if r in ('lplc2','lc4')])
    neu=float(np.tanh(np.mean(visual)*1.8))
    return round(neu,8),round(float(np.mean(np.abs(state))),8),shots


def run_one(seed:int, arm:str, trace=False):
    if arm not in ARMS:raise ValueError(arm)
    data=load_graph()
    condition=('weight_matched_rewire' if arm=='rewired_mock_fusion' else
               'no_propagation' if arm=='no_propagation_mock_fusion' else 'published_subset')
    W,_=incoming_matrix(data,condition,seed)
    qmode='off' if arm in ('baseline','mock_bio_only') else 'shuffled' if arm=='shuffle_quantum' else 'replay'
    bmode='off' if arm in ('baseline','quantum_only') else 'shuffled_mock' if arm=='shuffle_mock_bio' else 'mock'
    records=load_measurements() if qmode!='off' else None
    mode='holistic' if arm=='holistic_memory' else 'factorized'
    parent=Decoder(mode);terminal=Terminal(enabled=arm!='typing_denied')
    labels,rev=label_tables(seed)
    train=list(TRAIN); test=list(TEST)
    random.Random(44481+seed).shuffle(train);random.Random(44482+seed).shuffle(test)
    phases=(('train',train,labels,True,False),('novel_noise',test,labels,False,True),
            ('reversal_train',train,rev,arm!='frozen_reversal',False),
            ('reversal_novel_noise',test,rev,False,True),
            ('offspring_transfer_noise',test,rev,False,True))
    learner=parent; metrics={p:{'correct':0,'total':0,'unknown':0,'abstained':0} for p in PHASES}
    trials=[]; neural_sum=0.; trial_idx=0
    for phase,combos,table,update,noisy in phases:
        if phase=='offspring_transfer_noise':
            learner=Decoder(mode) if arm=='offspring_blank' else parent.clone()
        for i,j,k in combos:
            noun=NOUNS[i]
            feat,margin,cam_hash,cam=camera_observation(noun,j,k,seed,trial_idx,noisy)
            readout,neural,snaps=circuit_response(data,W,records,feat,seed,trial_idx,qmode,bmode,trace)
            # Disclosed fixed confidence policy: actual neural activity causally gates perception.
            confidence=max(0.,min(1.,margin+.17*readout))
            abstain=confidence<.18
            target=expected_phrase(table,(i,j,k))  # scoring/teacher only, AFTER observation
            predicted='<UNK>' if abstain else learner.predict(feat)
            approved=terminal.emit(predicted) if predicted!='<UNK>' else 'DENIED:UNKNOWN_TOKEN'
            world=WorldGate();gate=world.apply(predicted,approved,target,not abstain)
            m=metrics[phase];m['total']+=1;m['correct']+=int(gate=='UNLOCKED:RESOURCE')
            m['unknown']+=int(predicted=='<UNK>');m['abstained']+=int(abstain)
            if update:learner.teach(feat,target)
            neural_sum+=neural
            if trace:
                trials.append({'seed':seed,'arm':arm,'trial':trial_idx,'phase':phase,'object':noun,
                    'gesture':GESTURES[j],'intent':INTENTS[k],'pos':list(__import__('hard_mode').ALL_POS[noun]),
                    'features':[list(z) for z in feat], 'margin':margin, 'confidence':round(confidence,7),
                    'readout':readout,'bio_mode':bmode,'quantum_mode':qmode,'bio_source':MOCK_BIO_ID if bmode!='off' else 'DISABLED',
                    'predicted':predicted,'target':target,'typing':approved,'gate':gate,'reward':int(gate=='UNLOCKED:RESOURCE'),
                    'teacher_feedback_provided':update,'noisy_camera':noisy,'camera_sha256':cam_hash,'snapshots':snaps})
            trial_idx+=1
    return {'seed':seed,'arm':arm,'phases':metrics,'updates':parent.updates,
            'typed_count':len(terminal.log),'mean_abs_neural':round(neural_sum/trial_idx,8),
            'trace':trials if trace else []}


def run_experiment(seeds=8,out=OUT):
    if seeds<1:raise ValueError('seeds must be positive')
    out.mkdir(parents=True,exist_ok=True)
    # Checkpoint each matched seed atomically; restart never falsifies completed work.
    cache=out/'seed_cache';cache.mkdir(exist_ok=True)
    rows=[]
    for s in range(seeds):
        saved=cache/f'seed_{s:03d}.json'
        if saved.exists():
            group=json.loads(saved.read_text(encoding='utf8'))
            if len(group)!=len(ARMS) or [r['arm'] for r in group]!=list(ARMS) or any(r['seed']!=s for r in group):
                raise ValueError('invalid existing seed checkpoint')
        else:
            group=[run_one(s,arm,trace=s==0 and arm in ('baseline','quantum_only','mock_bio_only','mock_fusion','rewired_mock_fusion','no_propagation_mock_fusion','typing_denied')) for arm in ARMS]
            tmp=saved.with_suffix('.tmp')
            tmp.write_text(json.dumps(group,sort_keys=True,separators=(',',':'),allow_nan=False),encoding='utf8')
            tmp.replace(saved)
        rows.extend(group)
        print(f'CHECKPOINT seed {s+1}/{seeds} verified ({len(group)} conditions)',flush=True)
    with (out/'runs.jsonl').open('w',encoding='utf8') as f:
        for r in rows:f.write(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
    summaries={}
    for arm in ARMS:
        group=[r for r in rows if r['arm']==arm]
        summaries[arm]={p:{key:sum(row['phases'][p][key] for row in group)
               for key in ('correct','total','unknown','abstained')} for p in PHASES}
        summaries[arm]['mean_abs_neural']=round(sum(r['mean_abs_neural'] for r in group)/seeds,8)
        summaries[arm]['per_seed_novel']=[row['phases']['novel_noise']['correct'] for row in group]
        summaries[arm]['per_seed_reversal']=[row['phases']['reversal_novel_noise']['correct'] for row in group]
    primary={x:[r for r in rows if r['seed']==0 and r['arm']==x][0]['trace'] for x in ('baseline','quantum_only','mock_bio_only','mock_fusion')}
    delta={}
    for x in ('quantum_only','mock_bio_only','mock_fusion'):
        delta[x]=round(float(np.mean([abs(a-b) for t,u in zip(primary['baseline'],primary[x])
            for p,q in zip(t['snapshots'],u['snapshots']) for a,b in zip(p['neural'],q['neural'])])),8)
    means={a:sum(summaries[a]['per_seed_novel'])/(seeds*len(TEST)) for a in ('baseline','quantum_only','mock_bio_only','mock_fusion')}
    interaction=means['mock_fusion']-means['quantum_only']-means['mock_bio_only']+means['baseline']
    result={'experiment':'hard-mode perception / symbolic feedback with explicit neural confidence gate',
       'bio_status':'NO VERIFIED REAL BIOSIGNAL: real-bio experiments NOT EXECUTED; simulated development controls only',
       'quantum_status':'nine historic IBM summary replay; no live QPU; source-reported results not raw redecoded',
       'brain_status':'real-derived 42-node topology, ASSUMED dynamics and readout; software decoder',
       'visual_status':'virtual calibrated pixel input distinct from decorative world art',
       'source_sha256':{'flywire_subset':sha256(DATA),'ibm_replay':sha256(QDATA)},
       'code_sha256':{n:sha256(HERE/n) for n in ('fusion_hard_mode.py','hard_mode.py','quantum_language.py',
                     'sandbox_sensors.py','fly_movement.py')},
       'seeds':seeds,'arms':ARMS,'episodes_per_run':len(TRAIN)*2+len(TEST)*3,
       'runs':len(rows),'episodes':len(rows)*(len(TRAIN)*2+len(TEST)*3),
       'summary':summaries,'interaction_novel_mock_bio_not_real':round(interaction,8),
       'neural_delta_seed0':delta,'ledger_sha256':sha256(out/'runs.jsonl'),
       'license':'third-party FlyWire-derived subset CC BY-NC 4.0; never assume commercial rights',
       'authority':'sandbox in-memory terminal and resource gate, no host keyboard/actuator',
       'limitation':'task uses experimenter-defined grammar and near-field camera, not independent navigation or biological language'}
    (out/'results.json').write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({'runs':len(rows),'episodes':result['episodes'],'interaction':interaction,
        'neural_delta_seed0':delta,'novel':{a:f"{summaries[a]['novel_noise']['correct']}/{summaries[a]['novel_noise']['total']}" for a in ARMS},
        'reversal':{a:f"{summaries[a]['reversal_novel_noise']['correct']}/{summaries[a]['reversal_novel_noise']['total']}" for a in ARMS},
        'ledger':result['ledger_sha256']},indent=2),flush=True)
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--seeds',type=int,default=8);ap.add_argument('--output',type=Path,default=OUT)
    a=ap.parse_args();run_experiment(a.seeds,a.output)
