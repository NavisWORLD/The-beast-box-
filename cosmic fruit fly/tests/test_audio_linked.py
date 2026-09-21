"""Fail-closed provenance, bounded input, causal liveness, frozen-task controls."""
import sys,json
from pathlib import Path
import pytest,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audio_linked_fusion import (load_linked,audio_value,linked_count_value,circuit_response_audio,run_one,
       ARMS,sh,PKT_PATH,QPU_PATH,EXPECTED_PACKET,EXPECTED_COUNT,EXPECTED_ORIGIN)
from fly_movement import load_graph,incoming_matrix
from fusion_hard_mode import camera_observation
from hard_mode import NOUNS
from quantum_language import load_measurements

def test_source_reported_canonical_commitments_and_link():
    p,q=load_linked()
    assert p['packet_sha256']==EXPECTED_PACKET
    assert q['counts_sha256']==EXPECTED_COUNT
    assert q['origin_seed_sha256']==EXPECTED_ORIGIN
    assert q['job_id']=='da1mqfcdedkc73er87r0' and q['backend']=='ibm_marrakesh'
    assert q['source_packet_sha256']==p['packet_sha256']
    assert q['source_audio_sha256']==p['source_sha256']
    assert len(p['features'])==20 and sum(q['counts'].values())==4096

def test_one_feature_mutation_refused(tmp_path):
    p,q=load_linked();p['features'][0]['rms']+=0.0002
    a=tmp_path/'a.json';a.write_text(json.dumps(p))
    with pytest.raises(ValueError,match='packet commitment'):load_linked(a,QPU_PATH)

def test_counts_mutation_refused(tmp_path):
    p,q=load_linked();q['counts']['00000']+=1
    b=tmp_path/'b.json';b.write_text(json.dumps(q))
    with pytest.raises(ValueError,match='count distribution'):load_linked(PKT_PATH,b)

def test_cross_source_mismatch_refused(tmp_path):
    p,q=load_linked();q['source_audio_sha256']='f'*64
    b=tmp_path/'b.json';b.write_text(json.dumps(q))
    with pytest.raises(ValueError):load_linked(PKT_PATH,b)

def test_audio_stream_separate_and_bounded():
    p,_=load_linked();assert audio_value(p,0,'off',0)==(0.,None)
    seq=[audio_value(p,t,'ordered',0) for t in range(20)]
    assert [seg for _,seg in seq]==list(range(20))
    assert all(abs(v)<=.032 for v,_ in seq)
    assert seq==[audio_value(p,t,'ordered',0) for t in range(20)]
    assert [audio_value(p,t,'shuffled',0)[1] for t in range(20)]!=list(range(20))

def test_histogram_replay_preserves_provenance_but_does_not_fake_time_order():
    _,q=load_linked(); assert linked_count_value(q,0,0,'off')==(0.,None)
    a=[linked_count_value(q,t,0) for t in range(40)]
    assert a==[linked_count_value(q,t,0) for t in range(40)]
    assert all(abs(v)<=.032 and bits in q['counts'] for v,bits in a)
    assert [linked_count_value(q,t,1) for t in range(40)]!=a

def test_audio_and_qpu_numerical_ablation():
    p,q=load_linked();nine=load_measurements();d=load_graph()
    W,_=incoming_matrix(d,'published_subset',0)
    feat,_,_,_=camera_observation(NOUNS[1],1,1,0,1,True)
    a=circuit_response_audio(d,W,p,q,nine,feat,0,1,'baseline',True)
    b=circuit_response_audio(d,W,p,q,nine,feat,0,1,'audio_features',True)
    c=circuit_response_audio(d,W,p,q,nine,feat,0,1,'linked_counts',True)
    both=circuit_response_audio(d,W,p,q,nine,feat,0,1,'audio_linked_qpu',True)
    assert a[2]!=b[2] and a[2]!=c[2] and both[2]!=b[2]
    assert all(s['audio']==s['quantum']==s['bio']==0 for s in a[2])
    assert all(s['quantum']==0 and s['audio_segment'] is not None for s in b[2])
    assert all(s['audio']==0 and s['qpu_bits_histogram_surrogate'] in q['counts'] for s in c[2])
    assert all(len(s['neural'])==42 and len(s['dyn12'])==12 for s in both[2])

def test_matched_run_determinism_and_no_teacher_leak():
    a=run_one(0,'audio_linked_qpu',trace=True)
    assert a==run_one(0,'audio_linked_qpu',trace=True)
    assert len(a['trace'])==168
    assert all(not t['teacher_feedback_provided'] for t in a['trace'] if t['phase']=='novel_noise')
    assert all(t['audio_source_class']!='VERIFIED_PHYSIOLOGY' for t in a['trace'])
    assert a['phases']['novel_noise']['total']==24

def test_task_hardness_and_no_improvement_over_baseline():
    a=run_one(0,'baseline');b=run_one(0,'audio_linked_qpu')
    assert 0<a['phases']['novel_noise']['correct']<24
    assert a['phases']['novel_noise']['correct']==b['phases']['novel_noise']['correct']
    assert a['mean_abs_neural']!=b['mean_abs_neural']
