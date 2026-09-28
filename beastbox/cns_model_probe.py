"""One owner-approved bio-number -> CNS7 -> pinned native-model comparison.

Isolated experiment: does not open DurableRuntime, memories, models from vault,
tools or cloud providers, and never claims improved intelligence or fresh QPU data.
"""
from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request

from .bio_inputs import bio_event
from .bridge import BridgePacket
from .cns import CNS
from .events import normalize_event
from .hashutil import sha256_obj
from .providers import _local_opener
from .rawrphos_local import MODEL, SHA, STEP, status as native_status
from .state import MissionState


def cns_model_probe(data: dict) -> tuple[int, dict]:
    if os.environ.get("BEASTBOX_CNS_MODEL_PROBE_ENABLED", "no") != "yes":
        return 503, {"error": "CNS model-conditioning experiment is disabled"}
    if (not isinstance(data, dict)
        or set(data) != {"readings", "source", "consent", "model_probe_confirmed", "text"}
        or data.get("consent") is not True or data.get("model_probe_confirmed") is not True
        or not isinstance(data.get("text"), str) or not 1 <= len(data["text"].strip()) <= 220):
        return 400, {"error": "One bounded, separately approved sensor-model probe required"}
    try:
        event = bio_event(readings=data["readings"], source=data["source"], consent=True)
        normalized = normalize_event(event)
        features = normalized["features"]
        if len(features) != 12:
            raise ValueError("expected 12 bounded numeric sensor channels")
        mission = MissionState(mission_id="isolated-sensor-model-probe",
            objective="Compare numerical conditioning, not performance",
            dyn12=[0.0] * 12, provenance={"event_sha256": normalized["sha256"]})
        # No QPU job is run or claimed. The bounded software-event features
        # enter the existing seven-role controller by the existing bridge path.
        packet = BridgePacket(audio_features=list(features), metadata={"source": "owner-approved-unverified-numeric-event"})
        cns = CNS().tick(mission, packet.safe_dict())
        vector = cns["dyn12"]
        if len(vector) != 12 or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1 for v in vector):
            raise ValueError("invalid CNS control vector")
    except (ValueError, TypeError, KeyError, OverflowError):
        return 400, {"error": "Invalid or unverified numerical sensor event"}
    ready = native_status()
    if (ready.get("readiness") != "INSTALLED_AND_READY" or ready.get("loaded_step") != STEP
            or ready.get("checkpoint_sha256") != SHA):
        return 503, {"error": "Pinned local RAWRPHOS 14K is unavailable"}
    key = os.environ.get("RAWRPHOS_API_KEY", "")
    if len(key) < 32 or any(ch in key for ch in "\r\n"):
        return 503, {"error": "Private native-model authorization unavailable"}
    payload = {"model": MODEL, "prompt": data["text"].strip(), "control_vector": vector,
               "max_tokens": 24, "seed": 67}
    request = urllib.request.Request("http://127.0.0.1:8767/v1/condition-probe",
        data=json.dumps(payload, allow_nan=False).encode("utf-8"), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with _local_opener().open(request, timeout=44) as response:
            if response.status != 200 or int(response.headers.get("Content-Length", "0") or 0) > 24_000:
                return 502, {"error": "Native probe failed; no fallback"}
            raw = response.read(24_001)
        if len(raw) > 24_000:
            return 502, {"error": "Native probe exceeded response bound"}
        result = json.loads(raw)
        if (not isinstance(result, dict) or result.get("model_id") != MODEL
                or result.get("training_steps") != STEP or result.get("checkpoint_sha256") != SHA
                or result.get("model_weights_changed") is not False
                or result.get("performance_gain_proven") is not False
                or not isinstance(result.get("response_reference"), str)
                or not isinstance(result.get("response_conditioned"), str)
                or not isinstance(result.get("logit_l2"), dict)
                or any(not isinstance(v, (float, int)) or not math.isfinite(v) or v < 0
                    for v in result["logit_l2"].values())):
            return 502, {"error": "Unverified native conditioning result"}
        return 200, {"schema": "cosmos-cns7-model-probe-v1",
            "event_sha256": normalized["sha256"],
            "cns7_roles": sorted(k for k in cns if k not in {"dyn12", "phos"}),
            "cns_step": 1, "cns_state_sha256": sha256_obj(cns),
            "control_sha256": sha256_obj(vector),
            "model": MODEL, "training_steps": STEP, "checkpoint_sha256": SHA,
            "logit_l2": result["logit_l2"], "gate_by_layer": result.get("gate_by_layer"),
            "reference_response": result["response_reference"],
            "conditioned_response": result["response_conditioned"],
            "same_response": result.get("equal_fixed_seed"),
            "model_invoked": True, "weights_updated": False,
            "persistent_memory_updated": False, "owner_tools_used": False,
            "sensor_hardware_attested": False, "quantum_hardware_used": False,
            "quantum_advantage_proven": False, "intelligence_gain_proven": False,
            "experiment": "SINGLE_TURN_FIXED_WEIGHTS_NOT_HOSTED_DURABLE_CHAT"}
    except (OSError, ValueError, KeyError, TypeError, TimeoutError, urllib.error.HTTPError):
        return 502, {"error": "Native CNS-conditioned inference unavailable; no fallback"}
