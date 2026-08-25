from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from beastbox.bridge import BridgePacket
from beastbox.config import RuntimeConfig
from beastbox.runtime import CosmosRuntime


@dataclass
class CapturingProvider:
    prompts: list[str] = field(default_factory=list)

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "captured"


def _runtime(tmp_path: Path, provider: CapturingProvider) -> CosmosRuntime:
    return CosmosRuntime(
        RuntimeConfig(
            data_dir=str(tmp_path),
            memory_db=str(tmp_path / "memory.sqlite3"),
            evidence_dir=str(tmp_path / "evidence"),
            proposals_dir=str(tmp_path / "proposals"),
        ),
        provider=provider,
    )


def test_model_receives_complete_cns7_body_snapshot_every_turn(tmp_path: Path) -> None:
    provider = CapturingProvider()
    runtime = _runtime(tmp_path, provider)
    try:
        result = runtime.respond(
            "body integration check",
            bridge=BridgePacket(
                quantum_spark=[0.2, -0.1, 0.3],
                audio_features=[0.4, -0.2, 0.1],
                quantum_provenance={"source": "test"},
            ),
        )
    finally:
        runtime.close()

    body = result["body"]
    assert len(body["dyn12"]) == 12
    assert len(body["dyn42"]) == 42
    assert len(body["dyn54"]) == 54
    assert body["dyn54"] == body["dyn12"] + body["dyn42"]
    assert len(body["frame_sha256"]) == 64
    assert len(body["body_hash"]) == 64
    assert body["sensor_ids"] == [
        "quantum",
        "dark_matter",
        "emeth",
        "plasticity",
        "awareness",
        "daemons",
        "surgeon",
    ]

    prompt = provider.prompts[-1]
    assert "CNS7 BODY" in prompt
    assert body["body_hash"] in prompt
    assert body["frame_sha256"] in prompt
    assert "DYN42 SUMMARY" in prompt
    assert "DYN54 SUMMARY" in prompt


def test_body_persists_across_model_provider_swaps(tmp_path: Path) -> None:
    first_provider = CapturingProvider()
    runtime = _runtime(tmp_path, first_provider)
    try:
        first = runtime.respond("first mind", bridge=BridgePacket(quantum_spark=[0.1, 0.2]))
        runtime.provider = CapturingProvider()
        second = runtime.respond("second mind", bridge=BridgePacket(quantum_spark=[-0.1, 0.25]))

        assert first["body"]["epoch"] == 1
        assert second["body"]["epoch"] == 2
        assert first["body"]["body_hash"] != second["body"]["body_hash"]
        assert len(runtime.body.state_family.dyn54) == 54
    finally:
        runtime.close()
