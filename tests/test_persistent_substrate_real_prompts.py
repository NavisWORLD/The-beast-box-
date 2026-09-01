from __future__ import annotations

import hashlib
import json
from pathlib import Path

from beastbox.persistent_substrate.real_protocol import load_real_protocol


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SEQUENCE = [
    "ZEREF-DAD-SON-TALK-004",
    "HuggingFaceTB/SmolLM2-135M",
    "ZEREF-DAD-SON-TALK-004",
]


def _battery_sha256() -> str:
    path = ROOT / "experiments/persistent-substrate-real-model-swap-001/prompt-battery.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_real_protocol_is_frozen_before_result() -> None:
    protocol = load_real_protocol()
    assert protocol["experiment_id"] == "persistent-substrate-real-model-swap-001"
    assert protocol["model_sequence"] == EXPECTED_SEQUENCE
    assert protocol["result_observed"] is False
    assert protocol["prompt_battery_sha256"] == _battery_sha256()
    assert len(protocol["success_gates"]) == 14


def test_nonce_pairs_are_mirrored() -> None:
    protocol = load_real_protocol()
    pairs = protocol["nonce_pairs"]
    assert len(pairs) == 2
    assert pairs[0]["preferred"] == pairs[1]["rejected"]
    assert pairs[0]["rejected"] == pairs[1]["preferred"]


def test_prompt_battery_has_fixed_families_and_no_observed_scores() -> None:
    path = ROOT / "experiments/persistent-substrate-real-model-swap-001/prompt-battery.json"
    battery = json.loads(path.read_text(encoding="utf-8"))
    families = {case["family"] for case in battery["cases"]}
    assert families == {
        "public_calibration",
        "canonical_memory",
        "a0_canary",
        "b1_canary",
        "world_knowledge",
        "nonce_adversarial",
    }
    assert all("score" not in case for case in battery["cases"])
    assert all("result" not in case for case in battery["cases"])


def test_model_identities_are_exact_and_immutable() -> None:
    protocol = load_real_protocol()
    model_a = protocol["models"]["A"]
    model_b = protocol["models"]["B"]
    assert model_a["checkpoint_sha256"] == "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
    assert model_a["architecture_commit"] == "147110b9a77a7f94ec48099eefcea4486eec79fa"
    assert model_a["architecture_sha256"] == "955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc"
    assert model_b["revision"] == "4e53fc185bca18936752489b411f92c471815853"
    assert model_b["model_safetensors_sha256"] == "c59bfe7af6dc69e91e2084050c8c5b4706bb7c681a4d2e869560134a74a441c9"
