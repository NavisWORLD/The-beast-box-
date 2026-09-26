#!/usr/bin/env bash
# Explicit opt-in: preserve stable 14K, add separate unpromoted experimental 18K on private loopback.
set -Eeuo pipefail
umask 077
BASE=/app/apps/beastbox-cloud/bridge/deploy
if [[ "${RAWRPHOS_LOCAL_ENABLED:-no}" != "yes" ]]; then
  exec "$BASE/start_tiny.sh"
fi
: "${RAWRPHOS_CHECKPOINT_PATH:?Stable checkpoint path is required}"
: "${RAWRPHOS_18K_CHECKPOINT_PATH:?Experimental checkpoint path is required}"
: "${RAWRPHOS_API_KEY:?Native loopback API key is required}"
if [[ ${#RAWRPHOS_API_KEY} -lt 32 ]]; then
  echo "Native host key must be at least 32 characters" >&2
  exit 70
fi
# The model itself verifies each manifest member and parameter hash on load.
PORT=8767 HOST=127.0.0.1 gosu beastbox python -m rawrphos.inference.server \
  --checkpoint "$RAWRPHOS_CHECKPOINT_PATH" --port 8767 \
  --expected-sha256 4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5 &
native_pid=$!
# Same host-only key, separate authenticated loopback port and model instance.
PORT=8768 HOST=127.0.0.1 gosu beastbox python -m rawrphos.inference.server \
  --checkpoint "$RAWRPHOS_18K_CHECKPOINT_PATH" --port 8768 \
  --expected-sha256 20932937afb3e0e1b62a4e5f38f92170046ae2928b437dc31b8a37d6538e701e &
experimental_pid=$!
bridge_pid=""
cleanup() {
  if [[ -n "$bridge_pid" ]]; then kill "$bridge_pid" 2>/dev/null || true; fi
  kill "$native_pid" 2>/dev/null || true
  kill "$experimental_pid" 2>/dev/null || true
  if [[ -n "$bridge_pid" ]]; then wait "$bridge_pid" 2>/dev/null || true; fi
  wait "$native_pid" 2>/dev/null || true
  wait "$experimental_pid" 2>/dev/null || true
}
trap cleanup EXIT
# Do not serve an unverified model label. Any failed start preserves the prior
# deployed image; this script neither writes weights nor starts training.
if ! python - <<'PY'
import os
import time
import urllib.request
import json
from beastbox.providers import _local_opener
key = os.environ["RAWRPHOS_API_KEY"]
url = "http://127.0.0.1:8767/model/info"
for _ in range(120):
    try:
        request = urllib.request.Request(url, headers={"Authorization": "Bearer " + key})
        with _local_opener().open(request, timeout=2) as response:
            info = json.loads(response.read(16384))
        if (info.get("ready") is True and info.get("model_id") == "rawrphos-native"
                and info.get("training_steps") == 14000
                and info.get("checkpoint_sha256") == "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5"):
            print("Verified RAWRPHOS native 14K on private loopback", flush=True)
            raise SystemExit(0)
    except (OSError, ValueError, TypeError):
        pass
    time.sleep(1)
raise SystemExit("Native checkpoint failed to load/verify; bridge not started")
PY
then
  exit 70
fi
# The additional research model must be real and must NOT replace stable 14K.
# A failed second model aborts this new image; the prior Railway deployment is the rollback.
if ! python - <<'PY'
import json,os,time,urllib.request
from beastbox.providers import _local_opener
key=os.environ["RAWRPHOS_API_KEY"]
request=urllib.request.Request("http://127.0.0.1:8768/model/info",
    headers={"Authorization":"Bearer "+key})
for _ in range(120):
    try:
        with _local_opener().open(request,timeout=2) as response:
            info=json.loads(response.read(16384))
        if (info.get("ready") is True and info.get("model_id")=="rawrphos-native"
            and info.get("training_steps")==18000
            and info.get("checkpoint_sha256")=="20932937afb3e0e1b62a4e5f38f92170046ae2928b437dc31b8a37d6538e701e"):
            print("Verified separate unpromoted RAWRPHOS 18K on private loopback",flush=True)
            raise SystemExit(0)
    except (OSError,ValueError,TypeError):
        pass
    time.sleep(1)
raise SystemExit("Experimental 18K failed identity check; refusing new bridge deployment")
PY
then
  exit 70
fi
# Explicitly gated real in-container smoke before exposing the owner bridge.
# Uses only synthetic numerical data, pinned 14K, and private loopback; neither
# the source reading nor the native token nor any text response is logged.
if [[ "${BEASTBOX_CNS_MODEL_PROBE_ENABLED:-no}" == "yes" ]]; then
  if ! python - <<'PY'
import json,os,urllib.request
from beastbox.bio_inputs import bio_event
from beastbox.events import normalize_event
from beastbox.bridge import BridgePacket
from beastbox.cns import CNS
from beastbox.state import MissionState
from beastbox.providers import _local_opener
from beastbox.rawrphos_local import SHA,STEP
event=normalize_event(bio_event(readings={"heart_rate_bpm":72.0},source="manual",consent=True))
mission=MissionState(mission_id="startup-synthetic-acceptance",objective="one numeric software-state control")
cns=CNS().tick(mission,BridgePacket(audio_features=event["features"]).safe_dict())
payload=json.dumps({"model":"rawrphos-native","prompt":"Hello, Beast.",
                    "control_vector":cns["dyn12"],"max_tokens":12,"seed":67}).encode()
key=os.environ["RAWRPHOS_API_KEY"]
req=urllib.request.Request("http://127.0.0.1:8767/v1/condition-probe",data=payload,
    method="POST",headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
with _local_opener().open(req,timeout=42) as response:
    if response.status!=200:raise SystemExit("CNS native smoke rejected")
    raw=response.read(24001)
if len(raw)>24000:raise SystemExit("CNS native smoke exceeds bound")
result=json.loads(raw)
delta=result.get("logit_l2",{})
if (result.get("training_steps")!=STEP or result.get("checkpoint_sha256")!=SHA
    or result.get("model_weights_changed") is not False
    or result.get("performance_gain_proven") is not False
    or not isinstance(delta,dict) or
    not 0<=delta.get("zero_vs_reference",float("inf"))<1e-6 or
    not delta.get("conditioned_vs_reference",0)>0):
    raise SystemExit("CNS native numeric conditioning not verified")
print("REAL_PINNED_14K_CNS7_NATIVE_CONDITIONING_VERIFIED",
      "zero_l2",delta["zero_vs_reference"],
      "conditioned_l2",delta["conditioned_vs_reference"],flush=True)
PY
  then
    echo "Owner CNS model probe preflight failed; keeping previous deployment" >&2
    exit 70
  fi
fi
# Explicit one-deployment managed-host acceptance. The private subprocess
# enables the probe only in its own environment; the serving owner bridge stays
# feature-OFF until the separate public flag is deliberately enabled.
# No physical sensor data, archive histogram reconstruction, or provider jobs.
if [[ "${BEASTBOX_SIGNAL_ACCEPTANCE_ON_START:-no}" == "yes" ]]; then
  if ! BEASTBOX_SIGNAL_MODEL_PROBE_ENABLED=yes python - <<'PY'
import math
from beastbox.signal_model_probe import signal_model_probe
from beastbox.rawrphos_local import SHA, STEP
sensory={"type":"bio","source":"manual","consent":True,
         "readings":{"heart_rate_bpm":72.0,"hrv_rmssd_ms":31.0}}
archive={"type":"ibm_fez_published_summary","index":0,
         "archive_replay_confirmed":True}
for mode in ("pure_sensory","pure_quantum","fused"):
    packet={
        "text":"Describe the supplied state without claiming its physical cause.",
        "mode":mode,
        "conditioning_confirmed":True,
        "sensory":sensory if mode!="pure_quantum" else None,
        "quantum":archive if mode!="pure_sensory" else None,
    }
    status, receipt=signal_model_probe(packet)
    if status!=200:
        raise SystemExit("Managed-host typed fusion acceptance failed: "+mode)
    native=receipt.get("native_probe",{})
    metrics=native.get("logit_l2_vs_reference",{})
    resources=native.get("resource_metrics",{})
    generation=native.get("generation_metrics",{})
    if (
        receipt.get("checkpoint_sha256")!=SHA
        or receipt.get("training_steps")!=STEP
        or receipt.get("weights_updated") is not False
        or receipt.get("persistent_memory_updated") is not False
        or receipt.get("live_quantum_hardware_used") is not False
        or receipt.get("paid_provider_job_started") is not False
        or native.get("conditioned_cache_parity") is not True
        or native.get("arms",{}).get("conditioned",{}).get("control_vector")!=receipt.get("cns_dyn12")
        or not 0<=metrics.get("zero",float("inf"))<1e-6
        or not math.isfinite(metrics.get("conditioned",float("nan")))
        or metrics["conditioned"]<=0
        or not all(math.isfinite(resources.get(k,float("nan"))) and resources[k]>=0
                   for k in ("process_cpu_ms","wall_ms"))
        or not all(generation.get(k,{}).get("first_token_ms") is not None
                   and generation[k]["first_token_ms"]>=0
                   for k in ("reference","conditioned_cache","conditioned_no_cache"))
    ):
        raise SystemExit("Managed-host typed fusion numeric or safety gate failed: "+mode)
    print("REAL_MANAGED_14K_TYPED_FUSION_ACCEPTANCE_PASS",
          "mode",mode,
          "model_sha",SHA,
          "fusion_sha",receipt["fusion"]["fusion_sha256"],
          "cns_sha",receipt["cns_state_sha256"],
          "control_sha",native["arms"]["conditioned"]["control_sha256"],
          "zero_l2",metrics["zero"],
          "conditioned_l2",metrics["conditioned"],
          "cpu_ms",resources["process_cpu_ms"],
          "wall_ms",resources["wall_ms"],
          "cache_parity",native["conditioned_cache_parity"],
          flush=True)
print("REAL_MANAGED_14K_TYPED_FUSION_ALL_MODES_ACCEPTED",flush=True)
PY
  then
    echo "Managed-host typed fusion acceptance failed; do not expose new owner endpoint" >&2
    exit 70
  fi
fi
"$BASE/start_tiny.sh" &
bridge_pid=$!
wait -n "$native_pid" "$experimental_pid" "$bridge_pid"
echo "Native inference or existing bridge stopped; shutting down service" >&2
exit 1
