"""Owner-approved typed sensory/quantum -> CNS7 -> RAWRPHØS probe.

Isolated fixed-weight experiment: no DurableRuntime, memory write, provider job,
weight training, tool authority, actuator authority, or credential transport.
"""
from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
from typing import Any

from .bio_inputs import bio_event
from .bridge import BridgePacket
from .cns import CNS
from .providers import _local_opener
from .quantum_heart import HeartMode, QuantumHeart
from .rawrphos_local import MODEL, SHA, STEP, status as native_status
from .signal_fusion import (
    FUSION_MODES,
    fuse_sources,
    matched_classical_control,
    source_from_bio_event,
    source_from_soul_token,
)
from .soul.adapter import bridge_from_soul
from .soul.archive_summary import soul_token_from_ibm_fez_summary
from .state import MissionState

SCHEMA = "cosmos-sensory-quantum-native-probe-v1"
QUANTUM_SOURCE = "ibm_fez_published_summary"


def _validate_request(data: Any) -> tuple[str, str, dict[str, Any] | None, dict[str, Any] | None]:
    if (
        not isinstance(data, dict)
        or set(data) != {"text", "mode", "conditioning_confirmed", "sensory", "quantum"}
        or data.get("conditioning_confirmed") is not True
    ):
        raise ValueError("explicit bounded conditioning request required")
    text = data.get("text")
    mode = data.get("mode")
    sensory = data.get("sensory")
    quantum = data.get("quantum")
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 220:
        raise ValueError("probe text must be 1..220 characters")
    if mode not in FUSION_MODES:
        raise ValueError("unsupported signal fusion mode")
    if mode == "pure_sensory":
        if not isinstance(sensory, dict) or quantum is not None:
            raise ValueError("pure sensory mode accepts sensory input only")
    elif mode == "pure_quantum":
        if sensory is not None or not isinstance(quantum, dict):
            raise ValueError("pure quantum mode accepts one replay source only")
    else:
        if not isinstance(sensory, dict) or not isinstance(quantum, dict):
            raise ValueError("fused mode requires sensory and quantum replay sources")
    return text.strip(), mode, sensory, quantum


def _sensory_source(spec: dict[str, Any]):
    if set(spec) != {"type", "source", "readings", "consent"} or spec.get("type") != "bio":
        raise ValueError("only bounded bio measurement adapter is enabled")
    event = bio_event(readings=spec["readings"], source=spec["source"], consent=spec["consent"])
    return source_from_bio_event(event, source_id="owner-current-bio"), event


def _quantum_source(spec: dict[str, Any]):
    if (
        set(spec) != {"type", "index", "archive_replay_confirmed"}
        or spec.get("type") != QUANTUM_SOURCE
        or spec.get("archive_replay_confirmed") is not True
        or type(spec.get("index")) is not int
    ):
        raise ValueError("explicit archive replay selection required")
    token = soul_token_from_ibm_fez_summary(spec["index"])
    return source_from_soul_token(token), token


def _cns_vector(fusion: dict[str, Any], *, quantum_token=None, mission_id: str) -> tuple[list[float], dict[str, Any], dict[str, Any]]:
    quantum_bridge = bridge_from_soul(quantum_token) if quantum_token is not None else BridgePacket()
    packet = BridgePacket(
        quantum_spark=list(quantum_bridge.quantum_spark),
        quantum_provenance=dict(quantum_bridge.quantum_provenance),
        conditioning_vector=list(fusion["vector"]),
        conditioning_provenance={
            "schema": fusion["schema"],
            "mode": fusion["mode"],
            "fusion_sha256": fusion["fusion_sha256"],
            "projection_schema": fusion["projection_schema"],
            "source_ids": [source["source_id"] for source in fusion["sources"]],
        },
        metadata={"purpose": "isolated-fixed-weight-native-conditioning-probe"},
    )
    safe = packet.safe_dict()
    mission = MissionState(
        mission_id=mission_id,
        objective="Matched fixed-weight signal-conditioning comparison",
        dyn12=[0.0] * 12,
        provenance={
            "fusion_sha256": fusion["fusion_sha256"],
            "packet_sha256": safe["packet_sha256"],
        },
    )
    cns = CNS().tick(mission, safe)
    vector = cns["dyn12"]
    if (
        len(vector) != 12
        or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1 for v in vector)
    ):
        raise ValueError("CNS7 produced invalid model control vector")
    return list(vector), cns, safe


def _time_shifted_quantum_control(
    *,
    selected_index: int,
    sensory_source,
    mode: str,
) -> tuple[list[float], dict[str, Any]]:
    shifted_index = selected_index - 1 if selected_index > 0 else selected_index + 1
    shifted_token = soul_token_from_ibm_fez_summary(shifted_index)
    shifted_source = source_from_soul_token(
        shifted_token, source_id=f"archive-time-control-{shifted_index}"
    )
    sources = [shifted_source] if mode == "pure_quantum" else [sensory_source, shifted_source]
    fusion = fuse_sources(sources, mode=mode)
    vector, _, _ = _cns_vector(
        fusion,
        quantum_token=shifted_token,
        mission_id="isolated-time-shifted-control",
    )
    return vector, {
        "selected_index": selected_index,
        "shifted_index": shifted_index,
        "relation": "previous_record" if selected_index > 0 else "next_record",
        "shifted_timestamp": shifted_token.qbt_state.get("timestamp"),
        "shifted_result_digest": shifted_token.qbt_state.get("result_digest"),
        "fusion_sha256": fusion["fusion_sha256"],
        "classification": "ADJACENT_ARCHIVE_TIMESTAMP_CONTROL_NOT_FRESH_HARDWARE",
    }


def signal_model_probe(data: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if os.environ.get("BEASTBOX_SIGNAL_MODEL_PROBE_ENABLED", "no") != "yes":
        return 503, {"error": "Typed sensory-quantum model probe is disabled"}
    try:
        text, mode, sensory_spec, quantum_spec = _validate_request(data)
        sources = []
        sensory_source = None
        sensory_event = None
        quantum_token = None

        if sensory_spec is not None:
            sensory_source, sensory_event = _sensory_source(sensory_spec)
            sources.append(sensory_source)
        if quantum_spec is not None:
            quantum_source, quantum_token = _quantum_source(quantum_spec)
            sources.append(quantum_source)

        fusion = fuse_sources(sources, mode=mode)
        vector, cns, packet_safe = _cns_vector(
            fusion,
            quantum_token=quantum_token,
            mission_id="isolated-sensory-quantum-model-probe",
        )

        quantum_spark = bridge_from_soul(quantum_token).quantum_spark if quantum_token is not None else []
        heart = QuantumHeart(mode=HeartMode.SHADOW).update(list(quantum_spark), [])
        classical = matched_classical_control(vector)
        rotated = list(vector[1:]) + list(vector[:1])

        arms: dict[str, dict[str, Any]] = {
            "reference": {"control_vector": None, "attention_mode": "dyn12"},
            "zero": {"control_vector": [0.0] * 12, "attention_mode": "dyn12"},
            "conditioned": {"control_vector": list(vector), "attention_mode": "dyn12"},
            "source_shuffled": {"control_vector": rotated, "attention_mode": "dyn12"},
            "classical_matched": {"control_vector": classical, "attention_mode": "dyn12"},
            "zero_gate": {"control_vector": list(vector), "attention_mode": "zero_gate"},
            "frozen_state": {"control_vector": list(vector), "attention_mode": "frozen_state"},
            "shuffled_state": {"control_vector": list(vector), "attention_mode": "shuffled_state"},
        }

        time_control = None
        if quantum_spec is not None:
            shifted, time_control = _time_shifted_quantum_control(
                selected_index=quantum_spec["index"],
                sensory_source=sensory_source,
                mode=mode,
            )
            arms["time_shifted"] = {"control_vector": shifted, "attention_mode": "dyn12"}
    except (ValueError, TypeError, KeyError, OverflowError, json.JSONDecodeError):
        return 400, {"error": "Invalid, unconsented, or unsupported typed signal request"}

    ready = native_status()
    if (
        ready.get("readiness") != "INSTALLED_AND_READY"
        or ready.get("loaded_step") != STEP
        or ready.get("checkpoint_sha256") != SHA
    ):
        return 503, {"error": "Pinned local RAWRPHOS 14K is unavailable"}

    key = os.environ.get("RAWRPHOS_API_KEY", "")
    if len(key) < 32 or any(ch in key for ch in "\r\n"):
        return 503, {"error": "Private native-model authorization unavailable"}

    payload = {
        "model": MODEL,
        "prompt": text,
        "arms": arms,
        "max_tokens": 24,
        "seed": 67,
    }
    request = urllib.request.Request(
        "http://127.0.0.1:8767/v1/condition-probe-v2",
        data=json.dumps(payload, allow_nan=False, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        },
    )
    try:
        with _local_opener().open(request, timeout=44) as response:
            if response.status != 200 or int(response.headers.get("Content-Length", "0") or 0) > 96_000:
                return 502, {"error": "Native typed signal probe failed; no fallback"}
            raw = response.read(96_001)
        if len(raw) > 96_000:
            return 502, {"error": "Native typed signal probe exceeded response bound"}

        result = json.loads(raw)
        if (
            not isinstance(result, dict)
            or result.get("schema") != "rawrphos-condition-probe-v2"
            or result.get("model_id") != MODEL
            or result.get("training_steps") != STEP
            or result.get("checkpoint_sha256") != SHA
            or result.get("model_weights_changed") is not False
            or result.get("persistent_memory_updated") is not False
            or result.get("performance_gain_proven") is not False
            or result.get("conditioned_cache_parity") is not True
            or not isinstance(result.get("arms"), dict)
            or not isinstance(result.get("logit_l2_vs_reference"), dict)
            or any(
                not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0
                for value in result["logit_l2_vs_reference"].values()
            )
            or result["arms"].get("conditioned", {}).get("control_vector") != list(vector)
        ):
            return 502, {"error": "Unverified native typed conditioning result"}

        roles = sorted(key for key in cns if key not in {"dyn12", "phos"})
        if roles != sorted(["quantum", "dark_matter", "emeth", "plasticity", "awareness", "daemons", "surgeon"]):
            return 502, {"error": "CNS7 role contract mismatch"}

        source_receipts = []
        for source in sources:
            source_receipts.append(
                {
                    "source_id": source.source_id,
                    "family": source.family,
                    "kind": source.kind,
                    "execution_mode": source.execution_mode,
                    "channel_contract": source.channel_contract,
                    "mask": list(source.mask),
                    "weight": source.weight,
                    "confidence": source.confidence,
                    "freshness": source.freshness,
                    "captured_at": source.captured_at,
                    "provenance": dict(source.provenance or {}),
                }
            )

        return 200, {
            "schema": SCHEMA,
            "mode": mode,
            "model": MODEL,
            "training_steps": STEP,
            "checkpoint_sha256": SHA,
            "fusion": {
                "schema": fusion["schema"],
                "equation": fusion["equation"],
                "conditioning_contract": fusion["conditioning_contract"],
                "projection_schema": fusion["projection_schema"],
                "fusion_sha256": fusion["fusion_sha256"],
                "vector": fusion["vector"],
                "saturated_indices": fusion["saturated_indices"],
            },
            "sources": source_receipts,
            "sensor_event_sha256": None if sensory_event is None else __import__("beastbox.events", fromlist=["normalize_event"]).normalize_event(sensory_event)["sha256"],
            "soul_token_id": None if quantum_token is None else quantum_token.token_id,
            "qbt_result_digest": None if quantum_token is None else quantum_token.qbt_state.get("result_digest"),
            "bridge_packet_sha256": packet_safe["packet_sha256"],
            "cns7_roles": roles,
            "cns_state_sha256": __import__("beastbox.hashutil", fromlist=["sha256_obj"]).sha256_obj(cns),
            "cns_dyn12": vector,
            "quantum_heart": heart,
            "time_shift_control": time_control,
            "native_probe": result,
            "weights_updated": False,
            "persistent_memory_updated": False,
            "owner_tools_used": False,
            "live_quantum_hardware_used": False,
            "paid_provider_job_started": False,
            "source_causality_proven": False,
            "performance_gain_proven": False,
            "interpretation": "NUMERICAL_MODEL_SENSITIVITY_EXPERIMENT_ONLY",
        }
    except (OSError, ValueError, KeyError, TypeError, TimeoutError, urllib.error.HTTPError, json.JSONDecodeError):
        return 502, {"error": "Native typed sensory-quantum probe unavailable; no fallback"}
