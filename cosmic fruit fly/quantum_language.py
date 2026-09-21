"""Fail-closed historical IBM-summary neuromodulation and sandbox typing.

These 9 recorded historical job summaries are a deliberately bounded replay, NOT
live quantum hardware, not full IBM workload history, not biometric recordings.
Typing is a deterministic event-to-allowlisted-token actuator, NOT language
acquisition, a real keyboard, an LLM, or a host capability.
"""
from __future__ import annotations
import json, math, random
from pathlib import Path

HERE=Path(__file__).resolve().parent
DATA=HERE/'data'/'ibm_fez_nine_reported_summary.json'
VOCAB={
    'PICKUP:stick':'FOUND STICK', 'PLACE:stick':'PLACED STICK',
    'PICKUP:leaf':'FOUND LEAF','PLACE:leaf':'PLACED LEAF',
    'BUILD:NEST':'BUILT NEST','PICKUP:seed':'FOUND SEED',
    'PLANT:SEED':'PLANTED SEED','GROW:PATCH':'GROWN FOOD',
    'FEED:FOOD':'ATE FOOD',
    'REPRODUCE:SIMULATED_OFFSPRING':'HELLO LITTLE FLY',
    'OFFSPRING:FOOD_FOUND':'CHILD FOUND FOOD',
}
MAX_WORDS=36


def load_measurements(path=DATA):
    j=json.loads(Path(path).read_text(encoding='utf-8'))
    assert j['input_class']=='published_decode_summary_replay_not_live_quantum'
    assert j['backend']=='ibm_fez'
    m=j['measurements']
    if len(m)!=9 or len({r['job_id'] for r in m})!=9:
        raise ValueError('expected exactly nine distinct sourced jobs')
    for r in m:
        if not 0. <= r['entropy'] <= 1. or len(r['top_state']) != 5 or any(c not in '01' for c in r['top_state']) or r['total_shots'] != 4224:
            raise ValueError('unverified quantum record')
    return m


def quantum_value(records, tick, mode='replay', seed=0):
    if mode not in ('replay','off','shuffled'):
        raise ValueError('unknown quantum mode')
    if mode=='off':return 0.0,None
    # A fixed seed permutation keeps the same nine records, not fake samples.
    order=list(range(len(records)))
    if mode=='shuffled':random.Random(8200+seed).shuffle(order)
    r=records[order[tick%len(records)]]
    balance=(2*r['top_state'].count('1')-5)/5
    # Difference from 0.839 anchor is a COMPUTATIONAL scaling assumption.
    value=max(-.035,min(.035, .024*balance + .004*((r['entropy']-.839)*100)))
    return round(value,7),r['job_id']


def inject(stim, roles, sides, value):
    out=stim.copy()
    for i,(role,side) in enumerate(zip(roles,sides)):
        if role in ('lplc2','lc4'):
            out[i] += value * (1 if side=='left' else -1)
    return out


def type_event(state, event, enabled):
    """Append bounded words to sandbox-only state AFTER an observed event."""
    if event not in VOCAB:return None
    if 'type_token' not in enabled:return 'DENIED:TYPE_TOKEN'
    text=VOCAB[event]
    if any(w not in {'FOUND','STICK','PLACED','LEAF','BUILT','NEST','SEED','PLANTED',
                     'GROWN','FOOD','ATE','HELLO','LITTLE','FLY','CHILD'} for w in text.split()):
        raise RuntimeError('typed vocabulary denied')
    words=state.setdefault('typed_words',[])
    if len(words)+len(text.split())>MAX_WORDS:return 'DENIED:TEXT_CAPACITY'
    words.extend(text.split())
    return 'TYPE:'+text


def normalize_bio_packet(packet):
    """Reject mock or unproven bio packets; never auto-create physiology."""
    if not isinstance(packet,dict) or packet.get('origin_class')!='verified_recorded_biosignal' or not packet.get('source_sha256'):
        raise ValueError('real recorded biological evidence required; mock stream refused')
    if packet.get('signal_type') not in ('EEG','HRV','GSR','ECG'):
        raise ValueError('unsupported biological signal')
    value=packet.get('processed_value')
    if not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('invalid measured value')
    return float(value)
