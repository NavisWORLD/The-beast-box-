import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fly_movement import load_graph,incoming_matrix
from hard_mode import NOUNS, GLYPHS, INTENT_GLYPHS, expected_phrase, label_tables
from fusion_hard_mode import camera_observation
from audio_linked_fusion import load_linked
from neural_dependency import sensory_drive,raw_retina_code,neural_observation,LearnedReadout,run_one


def test_only_anatomical_sensory_population_directly_receives_camera():
    data=load_graph()
    _,_,_,im=camera_observation('food',0,0,0,2,False)
    stim=sensory_drive(data,im)
    assert np.count_nonzero(stim)>0
    assert all(stim[i]==0 for i,r in enumerate(data['roles']) if r not in ('lplc2','lc4'))


def test_pixel_change_changes_encoded_drive_without_named_class_lookup():
    data=load_graph();_,_,_,im=camera_observation('food',0,0,0,2,False)
    altered=im.copy();altered[39:49,43:53,:]=(0,0,0)
    assert not np.array_equal(raw_retina_code(im),raw_retina_code(altered))
    assert not np.array_equal(sensory_drive(data,im),sensory_drive(data,altered))


def test_original_has_downstream_signal_and_no_propagation_none():
    data=load_graph();packet,qpu=load_linked();_,_,_,im=camera_observation('food',0,0,0,2,False)
    real,_=incoming_matrix(data,'published_subset',0)
    off,_=incoming_matrix(data,'no_propagation',0)
    good,_=neural_observation(data,real,im,packet,qpu,0,2,'original_no_aux')
    gone,_=neural_observation(data,off,im,packet,qpu,0,2,'no_propagation_audio_qpu')
    assert np.linalg.norm(good)>0
    assert np.array_equal(gone,np.zeros(24))


def test_audio_qpu_modulates_downstream_but_does_not_reveal_teacher():
    data=load_graph();packet,qpu=load_linked();w,_=incoming_matrix(data,'published_subset',0)
    _,_,_,im=camera_observation('food',0,0,0,2,False)
    base,_=neural_observation(data,w,im,packet,qpu,0,2,'original_no_aux')
    fused,_=neural_observation(data,w,im,packet,qpu,0,2,'original_audio_qpu')
    assert np.max(np.abs(base-fused))>1.e-6


def test_target_not_used_for_inference_and_offspring_copy_is_independent():
    code=np.arange(24,dtype=float)/24
    m=LearnedReadout();gesture=tuple(GLYPHS[0]);intent=tuple(INTENT_GLYPHS[0])
    assert m.predict(code,gesture,intent)=='<UNK>'
    m.teach(code,'food',gesture,intent,'FOO VEE TOR')
    assert m.predict(code,gesture,intent)=='FOO VEE TOR'
    other=m.clone();other.labels['food']='BAR'
    assert m.predict(code,gesture,intent)=='FOO VEE TOR'
    assert other.predict(code,gesture,intent)=='BAR VEE TOR'
    assert m.predict(np.zeros(24),gesture,intent)=='<UNK>'


def test_matched_controls_gate_depends_on_propagation():
    real=run_one(0,'original_no_aux');off=run_one(0,'no_propagation_audio_qpu')
    assert real['phases']['novel_noise']['correct']>0
    assert off['phases']['novel_noise']['correct']==0
    assert real['nonzero_downstream']==168
    assert off['nonzero_downstream']==0


def test_denied_terminal_blocks_earned_reward_without_changing_prediction():
    baseline=run_one(0,'original_audio_qpu');denied=run_one(0,'original_typing_denied')
    assert baseline['phases']['novel_noise']['predicted']>0
    assert denied['phases']['novel_noise']['correct']==0
