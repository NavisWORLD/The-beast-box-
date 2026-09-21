"""Acceptance tests for novel composition, label isolation, and sandbox authority."""
import json
from pathlib import Path

import numpy as np
import pytest

from learn_compositional_text import (BLOCKED, GESTURES, GLYPHS, NOUNS, NOUN_TOKENS, VERB_TOKENS,
    Learner, Terminal, extract_features, label_tables, run_one, run_experiment,
    sense_pixels, sha256, QDATA, DATA, HERE)


def test_no_reserved_pair_in_training():
    train = {(i,j) for i in range(6) for j in range(3)} - BLOCKED
    assert len(BLOCKED) == 6 and len(train) == 12
    assert all(sum(i==n for i,j in train)==2 for n in range(6))
    assert all(sum(j==v for i,j in train)==4 for v in range(3))


def test_derived_source_files_unchanged():
    assert sha256(DATA) == '5b596574367d7e0e64489509a926a0305581f18568d12fef4339de5b49520cf4'
    assert sha256(QDATA) and len(sha256(QDATA)) == 64


def test_perception_excludes_teacher_label_and_reward():
    frame, glyph=sense_pixels('stick',(-2.75,-1.91),0)
    feature=extract_features(frame,glyph)
    assert len(feature)==2 and len(feature[0])==3
    assert all(isinstance(x,int) for group in feature for x in group)
    assert NOUN_TOKENS[0] not in str(feature)
    assert VERB_TOKENS[0] not in str(feature)
    assert len(frame.shape)==3 and frame.shape==(64,96,3)


def test_vision_rejects_nonvisible_object():
    blank=np.zeros((64,96,3),dtype=np.uint8)
    blank[:]=(18,43,57)
    with pytest.raises(ValueError,match='NO_VISIBLE_OBJECT'):
        extract_features(blank,np.zeros((8,8,3),dtype=np.uint8))


def test_label_derangement_and_seed_variation():
    first,second=label_tables(3)
    other,_=label_tables(11)
    assert sorted(first[0].values()) == sorted(NOUN_TOKENS)
    assert sorted(first[1].values()) == sorted(VERB_TOKENS)
    assert all(first[0][k]!=second[0][k] for k in NOUNS)
    assert all(first[1][k]!=second[1][k] for k in GESTURES)
    assert first!=other


def test_composition_without_whole_phrase_memory():
    learner=Learner('factorized'); holistic=Learner('holistic_phrase_memory')
    original=((184,108,61),(210,60,80)); other=((86,229,110),(62,169,242))
    unseen=((184,108,61),(62,169,242))
    for agent in (learner,holistic):
        agent.teach(original,'AX ZU');agent.teach(other,'BEX KA')
    assert learner.predict(unseen)=='AX KA'
    assert holistic.predict(unseen)=='<UNK>'


def test_supervision_disabled_means_no_updates():
    m=Learner('factorized'); obs=((10,20,30),(40,50,60))
    m.teach(obs,'AX ZU',enabled=False)
    assert m.updates==0 and m.predict(obs)=='<UNK>'


def test_terminal_default_denies_unapproved_and_has_capacity():
    t=Terminal(False)
    assert t.emit('AX ZU')=='DENIED:TYPE_TOKEN'
    t=Terminal(True)
    assert t.emit('SEND PRIVATE KEY')=='DENIED:UNKNOWN_TOKEN'
    assert not t.tokens
    for _ in range(128): assert t.emit('AX ZU')=='TYPE:AX ZU'
    assert t.emit('AX ZU')=='DENIED:CAPACITY'


def test_full_novel_generalization_and_controls():
    original=run_one(0,'original_replay',keep_trace=True)
    holistic=run_one(0,'holistic_phrase_memory')
    frozen=run_one(0,'frozen_reversal')
    off=run_one(0,'original_off')
    denied=run_one(0,'typing_denied')
    assert original['phase_metrics']['novel']['correct']==6
    assert original['phase_metrics']['reversal_novel']['correct']==6
    assert holistic['phase_metrics']['retained']['correct']==12
    assert holistic['phase_metrics']['novel']['correct']==0
    assert frozen['phase_metrics']['reversal_novel']['correct']==0
    assert off['phase_metrics']['novel']['correct']==6
    assert denied['phase_metrics']['novel']['correct']==0
    assert denied['phase_metrics']['novel']['recognized']==6
    assert all(not r['teacher_feedback_provided'] for r in original['trace'] if r['phase'] in ('retained','novel','reversal_retained','reversal_novel'))
    assert all('target' not in snap for r in original['trace'] for snap in r['snapshots'])


def test_independent_two_seed_ledger_reproducible(tmp_path):
    a=run_experiment(2,tmp_path/'a')
    b=run_experiment(2,tmp_path/'b')
    assert a['ledger_sha256']==b['ledger_sha256']
    assert (tmp_path/'a'/'runs.jsonl').read_bytes()==(tmp_path/'b'/'runs.jsonl').read_bytes()
