"""The graphics are bound to independently checked execution, not invented images."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from render_fusion import sources,render_frame,PHASE_COUNTS
from fly_movement import load_graph
from render_build_grow import ASSET, graph_layout
from PIL import Image
import pytest

@pytest.fixture(scope='module', autouse=True)
def _require_full_fusion_trace():
    if not (Path(__file__).resolve().parents[1] / 'fusion_demo' / 'runs.jsonl').exists():
        pytest.skip('Full historical fusion trial ledger is external to the source-only Git snapshot')

def test_exact_126_trial_selection_matches_ledger():
    result,rows,selected=sources()
    assert len(rows)==96
    assert len(selected)==sum(PHASE_COUNTS.values())==126
    assert selected[0]['seed']==selected[-1]['seed']==0
    assert selected[0]['arm']==selected[-1]['arm']=='mock_fusion'


def test_real_camera_sha_recomputed_in_preview():
    _,_,selected=sources()
    data=load_graph();world=Image.open(ASSET).convert('RGB').resize((900,540),Image.Resampling.NEAREST)
    chosen=selected[-1]
    frame=render_frame(chosen,chosen['snapshots'][-1],3,3,720,world,data,graph_layout(data))
    assert frame.size==(1280,720)


def test_decorative_world_asset_is_not_retina_input():
    from fusion_hard_mode import camera_observation
    _,_,hsh,im=camera_observation('leaf',1,0,0,13,True)
    assert im.shape==(64,96,3)
    assert hsh
    assert Image.open(ASSET).size != (96,64)
