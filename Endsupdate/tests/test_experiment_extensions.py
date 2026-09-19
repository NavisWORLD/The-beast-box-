import os

import pytest

from beastbox.audio_ablation import run_audio_ablation
from beastbox.shard_transport import chunks_to_key, continuity_score, key_to_chunks, prepare_required_shard, recover_required_shard
from beastbox.spark_ablation import run_spark_ablation


def test_required_shard_roundtrip_and_negative_key():
    state = {"objective": "continue", "hypothesis": "h1", "evidence": ["a", "b"], "public": 7}
    artifact, key = prepare_required_shard(state, ["hypothesis", "evidence"], key_bytes=16)
    assert "hypothesis" not in artifact.public_state
    assert recover_required_shard(artifact, key) == state
    assert continuity_score(artifact.public_state, ["hypothesis", "evidence"]) == 0.0
    with pytest.raises(ValueError):
        recover_required_shard(artifact, os.urandom(16))


def test_key_chunk_codec():
    key = bytes(range(16))
    assert chunks_to_key(key_to_chunks(key, 8)) == key


def test_audio_controls_exist():
    out = run_audio_ablation([0.1, -0.2, 0.3, 0.4])
    assert set(out["controls"]) == {"off", "zero", "real", "matched", "shuffled", "wrong"}


def test_spark_controls_include_classical():
    out = run_spark_ablation([0.1, 0.2, -0.1], classical_spark=[0.1, 0.2, -0.1])
    assert out["real_vs_classical_state_distance"] == 0.0
