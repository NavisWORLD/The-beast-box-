"""Isolated audio-derived/QPU-source-linked replay of the existing Cosmic Fruit Fly.

No physiology: source is memorial music/audio with source-reported provenance.
Original audio unavailable; packet's canonical commitment and QPU histogram hashes
are checked, but raw audio-to-feature extraction cannot be independently rerun.
Histogram HAS NO temporal shot ordering; a deterministic, explicitly artificial
sampling schedule makes it usable as a reproducible computational perturbation.
No audio/QPU time alignment or scientific/semantic pairing is claimed.
"""
from __future__ import annotations
import argparse,hashlib,json,math,random
from pathlib import Path
import numpy as np
from fly_movement import HERE,DATA,load_graph,incoming_matrix,sha256
from hard_mode import (NOUNS,GESTURES,INTENTS,TRAIN,TEST,label_tables,expected_phrase,
                       Decoder,Terminal,WorldGate,canonical_dyn12)
from fusion_hard_mode import camera_observation,bio_sample
from quantum_language import load_measurements,quantum_value,inject

PKT_PATH=HERE/'data'/'audio_source_feature_packet.json'
QPU_PATH=HERE/'data'/'linked_ibm_marrakesh_counts.json'
OUT=HERE/'audio_linked_demo'
ARMS=('baseline','nine_summary','audio_features','linked_counts',
      'audio_linked_qpu','audio_shuffled_qpu','audio_nine_unlinked','audio_linked_qpu_mock_bio')
PHASES=('train','novel_noise','reversal_train','reversal_novel_noise','offspring_transfer_noise')
EXPECTED_PACKET='d6e44478b9b6045907014515c3ac565e635443250d199979ab909fc1d2734fc0'
EXPECTED_COUNT='dfddf5366961cab837ae614750efb1dd60121ac3b3f6b7506d39346e3fd7bdce'
EXPECTED_ORIGIN='f21afbac49e798730974e37ed1a1bb7ce15f326660a9dbe3f848ee6b1f865c2f'

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sh(obj):return hashlib.sha256(canonical(obj)).hexdigest()

def load_linked(packet_path=PKT_PATH,qpu_path=QPU_PATH):
    packet=json.loads(Path(packet_path).read_text());qpu=json.loads(Path(qpu_path).read_text())
    body=dict(packet);supplied=body.pop('packet_sha256',None)
    if sh(body)!=EXPECTED_PACKET or supplied!=EXPECTED_PACKET:raise ValueError('audio feature packet commitment mismatch')
    if len(packet['features'])!=20 or [r['i'] for r in packet['features']]!=list(range(20)):raise ValueError('invalid feature order')
    if any(not all(math.isfinite(float(r[key])) for key in ('rms','zcr','centroid_nyquist','ry','rz','rx')) for r in packet['features']):
        raise ValueError('nonfinite input')
    counts=qpu['counts']
    if sh(counts)!=EXPECTED_COUNT or sum(counts.values())!=4096 or qpu['counts_sha256']!=EXPECTED_COUNT:raise ValueError('invalid count distribution')
    if any(len(k)!=5 or any(c not in '01' for c in k) or not isinstance(v,int) or v<0 for k,v in counts.items()):raise ValueError('invalid histogram')
    fields=('schema','lineage','source_class','source_packet_sha256','source_audio_sha256','backend','job_id',
            'shot_count','counts','counts_sha256','tags','job_tag_verified','waveform_quantum_entropy','claim_boundary')
    if qpu['origin_seed_sha256']!=EXPECTED_ORIGIN or sh({k:qpu[k] for k in fields})!=EXPECTED_ORIGIN:raise ValueError('origin seed mismatch')
    if qpu['source_packet_sha256']!=supplied or qpu['source_audio_sha256']!=packet['source_sha256'] or qpu['job_id']!='da1mqfcdedkc73er87r0':
        raise ValueError('audio/QPU source binding mismatch')
    return packet,qpu

def audio_value(packet,tick,mode,seed):
    if mode=='off':return 0.0,None
    if mode not in ('ordered','shuffled'):raise ValueError(mode)
    order=list(range(20))
    if mode=='shuffled':random.Random(6412+seed).shuffle(order)
    row=packet['features'][order[tick%20]]
    # bounded software transfer function, not a measurement of brain physiology
    value=.018*math.sin(row['ry'])+.008*math.cos(row['rz'])+.006*math.sin(row['rx'])
    return round(max(-.032,min(.032,value)),8),int(row['i'])

def linked_count_value(qpu,tick,seed,mode='histogram'):
    if mode=='off':return 0.0,None
    if mode!='histogram':raise ValueError(mode)
    # Raw shot sequence unavailable. Deterministic pseudorandom CDF sampling of
    # the REAL reported 4096-shot histogram. Never call this measured time order.
    digest=hashlib.sha256(f'audio-qpu-histogram-v1:{seed}:{tick}'.encode()).digest()
    index=int.from_bytes(digest[:8],'big')%4096
    cumulative=0
    for bits,n in sorted(qpu['counts'].items()):
        cumulative+=n
        if index<cumulative:break
    balance=(bits.count('1')-2.5)/2.5
    # Explicit bounded computational gain; do not encode task/teacher targets.
    return round(.032*balance,8),bits

def circuit_response_audio(data,W,packet,qpu,nine,features,seed,trial,arm,keep):
    rgb,gr,ir=features
    state=np.zeros(42,dtype=np.float64);dyn=[0.]*12;snaps=[]
    drive=(sum(rgb)/765.)*2.-1.+(sum(gr)/765.-.5)*.10+(sum(ir)/765.-.5)*.06
    diff=(rgb[0]-rgb[2])/255.
    audio_mode=('shuffled' if arm=='audio_shuffled_qpu' else 'ordered' if arm in
               ('audio_features','audio_linked_qpu','audio_nine_unlinked','audio_linked_qpu_mock_bio') else 'off')
    qmode=('histogram' if arm in ('linked_counts','audio_linked_qpu','audio_shuffled_qpu','audio_linked_qpu_mock_bio') else
           'nine' if arm in ('nine_summary','audio_nine_unlinked') else 'off')
    bmode='mock' if arm=='audio_linked_qpu_mock_bio' else 'off'
    for t in range(4):
        tick=trial*4+t;stim=np.zeros(42,dtype=np.float64)
        for i,(role,side) in enumerate(zip(data['roles'],data['sides'])):
            if role in ('lplc2','lc4'):stim[i]=.16*drive+.09*diff*(1 if side=='left' else -1)
        av,seg=audio_value(packet,tick,audio_mode,seed)
        if qmode=='histogram':qv,bits=linked_count_value(qpu,tick,seed);job=qpu['job_id']
        elif qmode=='nine':qv,job=quantum_value(nine,tick,'replay',seed);bits=None
        else:qv,bits,job=0.,None,None
        bio=bio_sample(seed,tick,bmode)
        # Same visual-role cells for independent bounded numerical contributions.
        for i,(role,side) in enumerate(zip(data['roles'],data['sides'])):
            if role in ('lplc2','lc4'):
                polarity=1 if side=='left' else -1
                stim[i]+=(av+qv+.024*bio)*polarity
        state=np.tanh(.61*state+2.15*(W@state)+stim)
        dyn=canonical_dyn12(dyn,[float(np.mean(state[i::12])) for i in range(12)],step=tick)
        if keep:
            snaps.append({'tick':t,'neural':np.round(state,5).tolist(),
              'dyn12':[round(z,5) for z in dyn],'quantum':qv,'job':job,'bio':bio,
              'audio':av,'audio_segment':seg,'qpu_bits_histogram_surrogate':bits,
              'source_class':'AUDIO_FEATURE_PACKET+ARCHIVED_QPU_HISTOGRAM' if audio_mode!='off' and qmode=='histogram' else 'CONTROL'})
    visual=np.array([state[i] for i,r in enumerate(data['roles']) if r in ('lplc2','lc4')])
    neu=float(np.tanh(np.mean(visual)*1.8))
    return round(neu,8),round(float(np.mean(np.abs(state))),8),snaps

def run_one(seed,arm,trace=False):
    if arm not in ARMS:raise ValueError(arm)
    packet,qpu=load_linked();nine=load_measurements();data=load_graph()
    W,_=incoming_matrix(data,'published_subset',seed)
    parent=Decoder('factorized');terminal=Terminal(enabled=True)
    labels,rev=label_tables(seed);train=list(TRAIN);test=list(TEST)
    random.Random(44481+seed).shuffle(train);random.Random(44482+seed).shuffle(test)
    phases=(('train',train,labels,True,False),('novel_noise',test,labels,False,True),
            ('reversal_train',train,rev,True,False),('reversal_novel_noise',test,rev,False,True),
            ('offspring_transfer_noise',test,rev,False,True))
    learner=parent;metrics={p:{'correct':0,'total':0,'unknown':0,'abstained':0} for p in PHASES}
    trials=[];neural_sum=0.;trial_idx=0
    for phase,combos,table,update,noisy in phases:
        if phase=='offspring_transfer_noise':learner=parent.clone()
        for i,j,k in combos:
            noun=NOUNS[i]
            feat,margin,cam_hash,cam=camera_observation(noun,j,k,seed,trial_idx,noisy)
            readout,neural,snaps=circuit_response_audio(data,W,packet,qpu,nine,feat,seed,trial_idx,arm,trace)
            conf=max(0.,min(1.,margin+.17*readout));abstain=conf<.18
            target=expected_phrase(table,(i,j,k)) # teacher/scorer only
            pred='<UNK>' if abstain else learner.predict(feat)
            approved=terminal.emit(pred) if pred!='<UNK>' else 'DENIED:UNKNOWN_TOKEN'
            world=WorldGate();gate=world.apply(pred,approved,target,not abstain)
            m=metrics[phase];m['total']+=1;m['correct']+=int(gate=='UNLOCKED:RESOURCE')
            m['unknown']+=int(pred=='<UNK>');m['abstained']+=int(abstain)
            if update:learner.teach(feat,target)
            neural_sum+=neural
            if trace:
                trials.append({'seed':seed,'arm':arm,'trial':trial_idx,'phase':phase,'object':noun,
                  'gesture':GESTURES[j],'intent':INTENTS[k],'pos':list(__import__('hard_mode').ALL_POS[noun]),
                  'features':[list(z) for z in feat],'margin':margin,'confidence':round(conf,7),
                  'readout':readout,'bio_mode':'mock' if arm=='audio_linked_qpu_mock_bio' else 'off',
                  'audio_source_class':'MEMORIAL_AUDIO_FEATURES_NOT_VERIFIED_PHYSIOLOGY',
                  'predicted':pred,'target':target,'typing':approved,'gate':gate,
                  'reward':int(gate=='UNLOCKED:RESOURCE'),'teacher_feedback_provided':update,
                  'noisy_camera':noisy,'camera_sha256':cam_hash,'snapshots':snaps})
            trial_idx+=1
    return {'seed':seed,'arm':arm,'phases':metrics,'updates':parent.updates,'typed_count':len(terminal.log),
            'mean_abs_neural':round(neural_sum/trial_idx,8),'trace':trials if trace else []}

def run_experiment(seeds=8,out=OUT):
    packet,qpu=load_linked()
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for seed in range(seeds):
        group=[run_one(seed,arm,trace=(seed==0)) for arm in ARMS]
        rows.extend(group)
        print(f'COMPLETE matched seed {seed+1}/{seeds} ({len(group)} arms)',flush=True)
    with (out/'runs.jsonl').open('w') as f:
        for r in rows:f.write(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
    summaries={}
    for arm in ARMS:
        group=[r for r in rows if r['arm']==arm]
        summaries[arm]={p:{k:sum(row['phases'][p][k] for row in group) for k in ('correct','total','unknown','abstained')} for p in PHASES}
        summaries[arm]['per_seed_novel']=[r['phases']['novel_noise']['correct'] for r in group]
        summaries[arm]['per_seed_reversal']=[r['phases']['reversal_novel_noise']['correct'] for r in group]
        summaries[arm]['mean_abs_neural']=round(sum(r['mean_abs_neural'] for r in group)/seeds,8)
    seed0={r['arm']:r['trace'] for r in rows if r['seed']==0}
    deltas={a:round(float(np.mean([abs(x-y) for t,u in zip(seed0['baseline'],seed0[a])
                       for s,v in zip(t['snapshots'],u['snapshots']) for x,y in zip(s['neural'],v['neural'])])),8)
            for a in ARMS if a!='baseline'}
    results={'schema':'cosmic-fruit-fly-audio-linked-qpu-v1','seeds':seeds,'arms':list(ARMS),'runs':len(rows),
             'episodes_per_run':len(TRAIN)*2+len(TEST)*3,'episodes':len(rows)*(len(TRAIN)*2+len(TEST)*3),
             'input_status':'source-reported memorial audio feature packet, linked historical IBM job histogram; original MP3 and true sampled shot order absent',
             'physiology_status':'NO VERIFIED PERSONAL PHYSIOLOGICAL RECORDING; REAL BIO NOT EXECUTED',
             'quantum_status':'offline histogram-surrogate replay; not live IBM; no actual temporal correspondence to source audio windows',
             'source_provenance':{'audio_mp3_sha256_source_reported':packet['source_sha256'],'feature_packet_commitment':packet['packet_sha256'],
                                  'ibm_job':qpu['job_id'],'ibm_backend':qpu['backend'],'ibm_shots':qpu['shot_count'],
                                  'ibm_counts_commitment':qpu['counts_sha256'],'ibm_origin_commitment':qpu['origin_seed_sha256']},
             'source_file_sha256':{k:sha256(v) for k,v in {'audio_packet':PKT_PATH,'linked_qpu':QPU_PATH,'nine_summary':HERE/'data'/'ibm_fez_nine_reported_summary.json','flywire_subset':DATA}.items()},
             'summary':summaries,'seed0_neural_delta':deltas,'ledger_sha256':sha256(out/'runs.jsonl'),
             'claim_limit':'Source linking is descriptive; authored grammar, symbolic software learner and modeled neural state; no demonstrated bio or quantum advantage.'}
    (out/'results.json').write_text(json.dumps(results,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'runs':len(rows),'episodes':results['episodes'],'novel':{a:f"{summaries[a]['novel_noise']['correct']}/{summaries[a]['novel_noise']['total']}" for a in ARMS},'neural_delta':deltas,'ledger':results['ledger_sha256']},indent=2),flush=True)
    return results
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--seeds',type=int,default=8);ap.add_argument('--output',type=Path,default=OUT)
    a=ap.parse_args();run_experiment(a.seeds,a.output)
