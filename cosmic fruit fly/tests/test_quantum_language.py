"""Source provenance, quantum liveness, sandbox text actuation and no-bio-fallback gates."""
import json, sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from quantum_language import load_measurements, quantum_value, inject, type_event, normalize_bio_packet, DATA
from run_build_grow import simulate, DEFAULT_ENABLED
from fly_movement import load_graph, incoming_matrix
import numpy as np


def test_ibm_summary_is_real_sourced_nine_distinct():
    rows=load_measurements()
    assert len(rows)==9 and sum(x['total_shots'] for x in rows)==38016
    assert rows[0]['job_id']=='d6p6l343pels73a3jvc0'
    source=json.loads(DATA.read_text())
    assert source['input_class']=='published_decode_summary_replay_not_live_quantum'


def test_replay_zero_shuffled_are_distinct_and_bounded():
    rows=load_measurements()
    for tick in range(80):
        val,job=quantum_value(rows,tick)
        assert job in {r['job_id'] for r in rows}
        assert abs(val)<=.035
        assert quantum_value(rows,tick,'off')==(0.,None)
    assert [quantum_value(rows,i,'shuffled') for i in range(9)]!=[quantum_value(rows,i) for i in range(9)]


def test_source_does_not_mutate_brain_injection_input():
    x=np.zeros(42)
    g=load_graph()
    y=inject(x,g['roles'],g['sides'],.027)
    assert not np.array_equal(x,y) and np.array_equal(x,np.zeros(42))


def test_typing_policy_denies_unexpected_events_and_host_commands():
    state={'typed_words':[]}
    assert type_event(state,'SYSTEM:rm -rf /',frozenset({'type_token'})) is None
    assert type_event(state,'BUILD:NEST',frozenset())=='DENIED:TYPE_TOKEN'
    assert not state['typed_words']
    assert type_event(state,'BUILD:NEST',frozenset({'type_token'}))=='TYPE:BUILT NEST'
    assert state['typed_words']==['BUILT','NEST']


def test_fake_or_missing_bio_packets_fail_closed():
    for fake in ({'origin_class':'mock','signal_type':'EEG','processed_value':1},
                 {'signal_type':'HRV','processed_value':.5},
                 {'origin_class':'verified_recorded_biosignal','signal_type':'EEG', 'source_sha256':'abc','processed_value':float('nan')}):
        with pytest.raises(ValueError):normalize_bio_packet(fake)


def test_legacy_baseline_preserved():
    r=simulate(0,typing=False,quantum_mode='off')
    assert r['stages_completed']==11 and not r['typed_events'] and r['mean_abs_quantum_drive']==0


def test_quantum_changes_neural_trajectory_not_stage_or_external_authority():
    a=simulate(0,typing=True,quantum_mode='replay',trace=True)
    b=simulate(0,typing=True,quantum_mode='off',trace=True)
    assert a['stages_completed']==b['stages_completed']==11
    assert a['typed_word_count']==b['typed_word_count']==24
    assert len(a['quantum_jobs'])==9 and not b['quantum_jobs']
    assert any(x['neural']!=y['neural'] for x,y in zip(a['trace'],b['trace']))
    assert 'no host/network/shell/actuator authority' in a['world']


def test_disabled_text_actuator_keeps_navigation():
    a=simulate(0,typing=True,quantum_mode='replay')
    b=simulate(0,typing=False,quantum_mode='replay')
    assert a['stages_completed']==b['stages_completed']==11
    assert a['typed_word_count']==24 and b['typed_word_count']==0
