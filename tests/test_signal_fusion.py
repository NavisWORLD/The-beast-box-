import math

from beastbox.bio_inputs import bio_event
from beastbox.bridge import BridgePacket
from beastbox.cns import CNS
from beastbox.dyn12 import update_dyn12
from beastbox.signal_fusion import (
    FUSION_SCHEMA,
    matched_classical_control,
    fuse_sources,
    source_from_bio_event,
    source_from_legacy_physics12,
    source_from_soul_token,
)
from beastbox.soul.token import SoulToken
from beastbox.state import MissionState


def test_bio_missing_mask_survives_fusion_and_is_not_midpoint_measurement():
    event = bio_event(
        readings={"heart_rate_bpm": 125.0, "spo2_pct": 85.0},
        source="manual",
        consent=True,
    )
    source = source_from_bio_event(event, source_id="bio-1")
    assert source.mask[0] is True
    assert source.mask[4] is True
    assert sum(source.mask) == 2
    # SpO2=85 is physically a measured midpoint of its declared input range,
    # whereas every omitted channel is only a placeholder. The mask preserves
    # that distinction even though both are numerically zero after normalization.
    assert source.vector[4] == 0.0
    assert source.vector[1] == 0.0
    assert source.mask[4] is True and source.mask[1] is False
    fused = fuse_sources([source], mode="pure_sensory")
    assert fused["schema"] == FUSION_SCHEMA
    assert fused["sources"][0]["mask"] == list(source.mask)
    assert len(fused["vector"]) == 12
    assert all(math.isfinite(v) and abs(v) <= 1 for v in fused["vector"])


def test_soul_adapter_preserves_two_x_minus_one_and_expansion_lineage():
    state = {
        "qbt_version": "1.0",
        "provider": "archive",
        "backend": "fixture",
        "execution_mode": "archive",
        "timestamp": "2026-03-12T07:26:04Z",
        "job_id": "fixture-job",
        "shots": 1024,
        "entropy": 0.5,
        "normalized_vector": [0.0, 0.25, 0.5, 1.0],
        "result_digest": "a" * 64,
        "provenance": {"source": "fixture"},
    }
    token = SoulToken.from_qbt(state, source_type="HARDWARE_ARCHIVE_REPLAY")
    source = source_from_soul_token(token)
    assert list(source.vector[:4]) == [-1.0, -0.5, 0.0, 1.0]
    assert list(source.vector[4:8]) == [-1.0, -0.5, 0.0, 1.0]
    assert source.provenance["normalized_source_width"] == 4
    assert source.provenance["expansion_map"] == [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]
    assert not any(token.authority.values())


def test_legacy_audio_placeholders_are_masked_not_reinterpreted():
    raw = [0.2, 1e-3, 0.3, 0.6, 0.0, 0.0, 0.0, 0.5, 0.4, 0.3, 0.7, 0.0]
    source = source_from_legacy_physics12(
        raw,
        modality="audio",
        source_id="historical-audio",
        source_commit="2bb40a0befd9b1023d91513eddd8447e730fce0b",
        source_path="cosmos/core/multimodal/audio_engine.py",
    )
    assert source.mask[4:7] == (False, False, False)
    assert source.mask[7] is False
    assert source.mask[11] is False
    assert source.provenance["placeholder_policy"]["audio_D5_D7_present"] is False


def test_fusion_is_deterministic_weighted_bounded_and_source_typed():
    bio = source_from_bio_event(
        bio_event(readings={"heart_rate_bpm": 100.0}, source="manual", consent=True),
        source_id="bio",
        weight=0.75,
        confidence=0.8,
        freshness=0.5,
    )
    token = SoulToken.from_qbt(
        {
            "qbt_version": "1.0",
            "provider": "simulator",
            "backend": "local",
            "execution_mode": "simulator",
            "normalized_vector": [0.2, 0.8],
            "result_digest": "b" * 64,
            "provenance": {"mode": "test"},
        },
        source_type="SIMULATOR",
    )
    quantum = source_from_soul_token(token, source_id="qbt", weight=0.25)
    one = fuse_sources([bio, quantum], mode="fused")
    two = fuse_sources([bio, quantum], mode="fused")
    assert one == two
    assert {row["family"] for row in one["sources"]} == {"sensory", "quantum"}
    assert all(abs(v) <= 1.0 for v in one["vector"])
    assert len(one["fusion_sha256"]) == 64
    assert fuse_sources([bio, quantum], mode="pure_sensory")["source_count"] == 1
    assert fuse_sources([bio, quantum], mode="pure_quantum")["source_count"] == 1


def test_classical_matched_control_preserves_exact_l2_strength():
    vector = [round((i - 5.5) / 10.0, 4) for i in range(12)]
    control = matched_classical_control(vector)
    assert control != vector
    assert math.isclose(sum(v * v for v in vector), sum(v * v for v in control), rel_tol=0, abs_tol=1e-12)
    assert sorted(abs(v) for v in vector) == sorted(abs(v) for v in control)


def test_cns_prefers_explicit_fused_drive_and_keeps_quantum_provenance_separate():
    fused = [0.05 * (i - 6) for i in range(12)]
    packet = BridgePacket(
        audio_features=[0.99, -0.99],
        quantum_spark=[0.8, -0.8],
        quantum_provenance={"source_type": "SIMULATOR"},
        conditioning_vector=fused,
        conditioning_provenance={"schema": FUSION_SCHEMA, "fusion_sha256": "c" * 64},
    )
    state = MissionState(mission_id="fusion-test", objective="verify typed drive")
    result = CNS().tick(state, packet.safe_dict())
    assert result["dyn12"] == update_dyn12([0.0] * 12, fused, step=1)
    assert result["quantum"]["spark_present"] is True
    assert result["quantum"]["spark_dim"] == 2
    assert result["quantum"]["provenance"]["source_type"] == "SIMULATOR"
    assert result["awareness"]["conditioning"]["sha256"]
    assert result["awareness"]["conditioning"]["provenance"]["schema"] == FUSION_SCHEMA


def test_bridge_legacy_packet_hash_shape_stays_legacy_without_conditioning():
    packet = BridgePacket(audio_features=[0.1])
    safe = packet.safe_dict()
    assert "conditioning_vector" not in safe
    assert "conditioning_provenance" not in safe
    assert len(safe["packet_sha256"]) == 64


def test_ibm_fez_published_summary_is_new_archive_replay_schema_not_fresh_hardware():
    from beastbox.soul.archive_summary import archive_manifest, soul_token_from_ibm_fez_summary
    token=soul_token_from_ibm_fez_summary(0)
    assert token.source_type=="HARDWARE_ARCHIVE_REPLAY"
    assert token.qbt_state["qbt_version"]=="ibm-fez-published-decode-summary-replay-v1"
    assert token.qbt_state["normalized_vector"]==[0.8387,0.0,0.0,0.0,0.0,0.0]
    provenance=token.qbt_state["provenance"]
    assert provenance["raw_runtime_payload_present"] is False
    assert provenance["full_counts_present"] is False
    assert provenance["fresh_provider_execution"] is False
    assert provenance["transform"]=="normalized_vector=[entropy]+left_to_right_top_state_bits"
    manifest=archive_manifest()
    assert len(manifest["records"])==9
    assert manifest["live_hardware"] is False
    source=source_from_soul_token(token)
    assert source.family=="quantum"
    assert source.execution_mode=="hardware_archive_summary_replay"
