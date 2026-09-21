"""Test causal-channel liveness without converting a numerical change to a task claim."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
import numpy as np
from fusion_hard_mode import (bio_sample, normalize_recorded_bio, camera_observation,
                              circuit_response, run_one, ARMS, MOCK_BIO_ID)
from hard_mode import NOUNS, GESTURES, INTENTS, raw_retina
from fly_movement import load_graph, incoming_matrix
from quantum_language import load_measurements


def test_real_bio_fail_closed():
    for packet in ({'origin_class':'mock','processed_value':.5}, {'origin_class':'verified_recorded_biosignal'}):
        with pytest.raises(ValueError):normalize_recorded_bio(packet,'f'*64)
    with pytest.raises(ValueError):normalize_recorded_bio({'origin_class':'verified_recorded_biosignal','source_sha256':'f'*64,'signal_type':'HRV','timestamp':'t','unit':'ms','processed_value':float('nan')},'f'*64)


def test_verified_schema_only_not_proof_of_live_recording():
    packet={'origin_class':'verified_recorded_biosignal','source_sha256':'f'*64,'signal_type':'HRV','timestamp':'2026-01-01T00:00:00Z','unit':'ms','processed_value':52.}
    assert normalize_recorded_bio(packet,'f'*64)==52.
    with pytest.raises(ValueError):normalize_recorded_bio(packet,'a'*64)


def test_mock_is_explicit_and_deterministic():
    assert 'SIMULATED' in MOCK_BIO_ID
    assert bio_sample(3,10,'off') == 0.
    assert bio_sample(3,10,'mock') == bio_sample(3,10,'mock')
    assert bio_sample(3,10,'shuffled_mock')!=bio_sample(3,10,'mock')
    with pytest.raises(ValueError):bio_sample(0,0,'real')


def test_camera_is_pixel_derived_and_traceable():
    a,margin,sha,pixels=camera_observation(NOUNS[0],1,2,2,7,True)
    b,margin2,sha2,pixels2=camera_observation(NOUNS[0],1,2,2,7,True)
    assert a==b and margin==margin2 and sha==sha2 and np.array_equal(pixels,pixels2)
    assert 0 <= margin <= 1
    assert sha!=camera_observation(NOUNS[0],1,2,2,7,False)[2]
    assert sha!=camera_observation(NOUNS[1],1,2,2,7,True)[2]


def test_42_topology_and_ablation_liveness():
    data=load_graph();assert len(data['roles'])==42
    W,_=incoming_matrix(data,'published_subset',0)
    feat,_,_,_=camera_observation(NOUNS[1],1,1,0,1,True)
    rec=load_measurements()
    a=circuit_response(data,W,rec,feat,0,1,'off','off',True)
    b=circuit_response(data,W,rec,feat,0,1,'replay','off',True)
    c=circuit_response(data,W,rec,feat,0,1,'off','mock',True)
    assert len(a[2])==4 and all(len(x['neural'])==42 and len(x['dyn12'])==12 for x in a[2])
    assert b[2][0]['job'] and b[2][0]['quantum']!=0
    assert all(s['bio']==0 for s in a[2]) and any(s['bio'] for s in c[2])
    assert any(x['neural']!=y['neural'] for x,y in zip(a[2],b[2]))
    assert any(x['neural']!=y['neural'] for x,y in zip(a[2],c[2]))


def test_replay_is_deterministic_and_no_future_teacher_leak():
    a=run_one(0,'mock_fusion',trace=True)
    b=run_one(0,'mock_fusion',trace=True)
    assert a==b
    assert a['trace'][0]['teacher_feedback_provided']
    assert not next(t for t in a['trace'] if t['phase']=='novel_noise')['teacher_feedback_provided']
    assert all(t['bio_source']==MOCK_BIO_ID for t in a['trace'])
    assert all(len(t['snapshots'])==4 for t in a['trace'])


def test_communication_authority_controls():
    r=run_one(0,'typing_denied')
    assert r['phases']['novel_noise']['correct']==0 and r['typed_count']==0
    frozen=run_one(0,'frozen_reversal')
    assert frozen['phases']['reversal_novel_noise']['correct']==0
    hol=run_one(0,'holistic_memory')
    assert hol['phases']['novel_noise']['correct']==0
    blank=run_one(0,'offspring_blank')
    assert blank['phases']['offspring_transfer_noise']['correct']==0


def test_hard_noisy_holdout_can_fail_without_intentional_control_sabotage():
    r=run_one(0,'baseline')
    assert r['phases']['novel_noise']['total']==24
    assert 0 < r['phases']['novel_noise']['correct'] < 24
    assert r['phases']['reversal_novel_noise']['correct'] < 24


def test_ablation_is_not_falsely_described_as_accuracy_advantage():
    a=run_one(0,'baseline');q=run_one(0,'quantum_only');bio=run_one(0,'mock_bio_only')
    assert a['mean_abs_neural']!=q['mean_abs_neural']
    assert a['mean_abs_neural']!=bio['mean_abs_neural']
    # This test checks benchmark design, not a permanent claim about future outcomes.
    assert a['phases']['novel_noise']['correct']==q['phases']['novel_noise']['correct']==bio['phases']['novel_noise']['correct']
