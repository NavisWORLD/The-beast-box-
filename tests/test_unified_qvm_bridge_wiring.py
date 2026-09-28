"""Guard historical legacy hashes and explicit unified 12D transport contract."""
import math
import pytest
from beastbox.bridge import BridgePacket
from beastbox.cns import CNS
from beastbox.dyn12 import update_dyn12
from beastbox.state import MissionState
from beastbox.signal_fusion import source_from_soul_token, fuse_sources
from beastbox.soul.token import SoulToken

def test_legacy_packet_remains_unchanged_without_explicit_conditioning():
    p=BridgePacket(quantum_spark=[0.1,0.2])
    data=p.safe_dict()
    assert "conditioning_vector" not in data
    assert "conditioning_provenance" not in data

def test_full_typed_qvm_signal_enters_unified_cns_without_mixing_units():
    token=SoulToken.from_qbt({
        "normalized_vector":[0.6,0.0,0.0,0.4,0.45],
        "execution_mode":"ARCHIVED_SIMULATOR_ONLY","provider":"azure_quantum",
        "provenance":{"original_job":"synthetic-test-fake-id"}},source_type="SIMULATED_SHOT_COUNTS_NOT_PHYSICAL")
    source=source_from_soul_token(token)
    drive=fuse_sources([source],mode="pure_quantum")["vector"]
    pkt=BridgePacket(
        quantum_spark=[-0.9]*12,
        conditioning_vector=list(drive),
        conditioning_provenance={"fixture":"reconciliation-test","secret_data":"must-strip"})
    raw=pkt.safe_dict()
    assert raw["conditioning_vector"]==drive
    assert "secret_data" not in raw["conditioning_provenance"]
    mission=MissionState(mission_id="isolated-typed-control",objective="test")
    state=CNS().tick(mission,raw)
    expected=update_dyn12([0.0]*12,drive,step=1)
    assert len(state["dyn12"])==12
    assert all(math.isclose(a,b,rel_tol=0,abs_tol=1e-12) for a,b in zip(state["dyn12"],expected))
    assert state["awareness"]["conditioning"]["schema"]=="generic-model-control-C1..C12"

@pytest.mark.parametrize("value",[
    [0.0]*11,[float("nan")]+[0.0]*11,[float("inf")]+[0.0]*11,
    [2.0]+[0.0]*11,[True]+[0.0]*11,
])
def test_bad_conditioning_rejected(value):
    mission=MissionState(mission_id="invalid-control",objective="test")
    with pytest.raises(ValueError,match="conditioning_vector"):
        CNS().tick(mission,{"conditioning_vector":value})
