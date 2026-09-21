"""Fail-closed hard-mode acceptance and reproducibility tests."""
import numpy as np
import pytest
from hard_mode import (NOUNS, COLORS, TRAIN, TEST, HELD, ARMS, Decoder, Terminal,
    WorldGate, expected_phrase, label_tables, raw_retina, observed, run_one,
    run_experiment, sha256, DATA, QDATA)


def test_preregistered_factor_coverage_and_disjoint():
    assert len(NOUNS)==8 and len(TRAIN)==48 and len(TEST)==24
    assert not (set(TRAIN)&set(TEST))
    assert len(set(TRAIN)|set(TEST))==72
    for i in range(8):
        assert sum(a==i for a,b,c in TRAIN)==6
    for j in range(3):
        assert sum(b==j for a,b,c in TRAIN)==16
    for k in range(3):
        assert sum(c==k for a,b,c in TRAIN)==16


def test_all_categories_reachable_from_camera_and_partial_occlusion():
    for noun in NOUNS:
        clean,_=observed(noun,0,0,'clean',0)
        for variant in range(3):
            noisy,rgb=observed(noun,0,0,'noisy',variant)
            assert noisy==clean
            assert rgb.shape==(64,96,3)
            assert tuple(clean[0])==COLORS[noun]
            assert not np.array_equal(rgb,raw_retina(noun))


def test_perception_no_teacher_tokens_or_labels():
    lab,_=label_tables(22)
    obs,_=observed('crystal',1,2,'noisy',1)
    assert len(obs)==3
    assert all(isinstance(c,int) for group in obs for c in group)
    assert lab[0]['crystal'] not in str(obs)
    assert lab[1]['mark'] not in str(obs)
    assert lab[2]['share'] not in str(obs)


def test_three_token_generalization_reversal_and_holistic_failure():
    obs1=((10,20,30),(40,50,60),(70,80,90))
    obs2=((90,100,110),(120,130,140),(150,160,170))
    novel=(obs1[0],obs2[1],obs1[2])
    d=Decoder();h=Decoder('holistic')
    for learner in (d,h):
        learner.teach(obs1,'AX ZU TOR');learner.teach(obs2,'BEX KA WUN')
    assert d.predict(novel)=='AX KA TOR'
    assert h.predict(novel)=='<UNK>'
    d.teach(obs1,'CIR MI VEX')
    assert d.predict(obs1)=='CIR MI VEX'


def test_terminal_rejects_unauthorized_and_gate_checks_truth():
    t=Terminal(False);assert t.emit('AX ZU TOR')=='DENIED:TYPE_TOKEN'
    assert Terminal(True).emit('HOST SHELL ACCESS')=='DENIED:UNKNOWN_TOKEN'
    t=Terminal(True);w=WorldGate()
    approved=t.emit('AX ZU TOR')
    assert w.apply('AX ZU TOR',approved,'BEX ZU TOR',True)=='LOCKED'
    assert w.apply('AX ZU TOR',approved,'AX ZU TOR',False)=='LOCKED'
    assert w.apply('AX ZU TOR',approved,'AX ZU TOR',True)=='UNLOCKED:RESOURCE'
    assert w.unlocked==['AX ZU TOR'] and w.denied==2


def test_all_message_controls_and_offspring_reset():
    primary=run_one(0,'original_replay',True)
    holistic=run_one(0,'holistic_memory')
    frozen=run_one(0,'frozen_reversal')
    denied=run_one(0,'typing_denied')
    blank=run_one(0,'offspring_blank')
    assert primary['phases']['novel_noise']['correct']==24
    assert primary['phases']['reversal_novel_noise']['correct']==24
    assert primary['phases']['offspring_transfer_noise']['correct']==24
    assert holistic['phases']['retained']['correct']==48
    assert holistic['phases']['novel_noise']['correct']==0
    assert frozen['phases']['reversal_novel_noise']['correct']==0
    assert denied['phases']['novel_noise']['recognized']==24
    assert denied['phases']['novel_noise']['correct']==0
    assert blank['phases']['offspring_transfer_noise']['correct']==0
    assert all('target' not in snap for tr in primary['trace'] for snap in tr['snapshots'])
    assert all(not tr['teacher_feedback_provided'] for tr in primary['trace'] if tr['phase'] in ('novel_noise','reversal_novel_noise','offspring_transfer_noise'))


def test_source_hash_and_independent_repeat(tmp_path):
    assert sha256(DATA)=='5b596574367d7e0e64489509a926a0305581f18568d12fef4339de5b49520cf4'
    assert len(sha256(QDATA))==64
    a=run_experiment(1,tmp_path/'a');b=run_experiment(1,tmp_path/'b')
    assert a['ledger_sha256']==b['ledger_sha256']
    assert (tmp_path/'a'/'runs.jsonl').read_bytes()==(tmp_path/'b'/'runs.jsonl').read_bytes()
