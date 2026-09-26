"""Real pinned-14K fixed-weight sensory/IBM-summary fusion acceptance.

Only synthetic manual numerical bio readings and published archive summaries are
used. Exercises the real authenticated local HTTP server, owner bridge, native
PyTorch control, and full matched arms. Never touches the owner volume, runs a
provider job, trains weights, or claims physical-source causality.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import urllib.request

from uvicorn import Config, Server

from beastbox.rawrphos_local import SHA, STEP
from beastbox.providers import _local_opener
from rawrphos.inference.server import create_app

MODES = ("pure_sensory", "pure_quantum", "fused")
SYNTHETIC_SENSOR = {
    "type": "bio", "source": "manual", "consent": True,
    "readings": {"heart_rate_bpm": 72.0, "hrv_rmssd_ms": 31.0},
}
ARCHIVE = {
    "type": "ibm_fez_published_summary", "index": 0,
    "archive_replay_confirmed": True,
}
KEY = "synthetic-ci-native-acceptance-key-0123456789"
OWNER_KEY = "synthetic-ci-bridge-acceptance-key-0123456789"
PROMPT = "Describe the supplied state without claiming its physical cause."


def _file_digests(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*") if p.is_file() and not p.is_symlink()
    }


def run(checkpoint: Path, report: Path) -> None:
    if not checkpoint.is_dir():
        raise AssertionError("pinned real 14K checkpoint was not installed")
    os.environ.update({
        "RAWRPHOS_CHECKPOINT_PATH": str(checkpoint),
        "RAWRPHOS_API_KEY": KEY,
        "BEASTBOX_SIGNAL_MODEL_PROBE_ENABLED": "yes",
        "BEASTBOX_BIO_INGEST_ENABLED": "yes",
        "BEASTBOX_BIO_PERSIST_ENABLED": "no",
        "BEASTBOX_BIO_REMOTE_ALLOWED": "no",
        "BEASTBOX_TINY_LOCAL_ENABLED": "no",
        "BEASTBOX_HF_MODEL_ID": "",
        "BEASTBOX_CONNECTION_VAULT_KEY": "",
    })
    app = create_app(
        checkpoint, KEY, max_new_tokens=64, threads=2, expected_sha256=SHA
    )
    assert app.state.engine.info()["training_steps"] == STEP
    server = Server(Config(
        app, host="127.0.0.1", port=8767, log_level="error",
        access_log=False,
    ))
    runner = threading.Thread(target=server.run, name="private-native-ci", daemon=True)
    runner.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(0.2)
        assert server.started, "real native server failed loopback startup"

        request = urllib.request.Request(
            "http://127.0.0.1:8767/model/info",
            headers={"Authorization": "Bearer " + KEY},
        )
        with _local_opener().open(request, timeout=5) as response:
            info = json.loads(response.read(16384))
        assert info["checkpoint_sha256"] == SHA
        assert info["training_steps"] == STEP
        assert info["model_id"] == "rawrphos-native"

        spec = importlib.util.spec_from_file_location(
            "stage011_ci_owner_bridge",
            "apps/beastbox-cloud/bridge/owner_bridge.py",
        )
        assert spec is not None and spec.loader is not None
        bridge_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge_mod)

        receipts = {}
        with tempfile.TemporaryDirectory(prefix="stage011-ephemeral-owner-") as tmp:
            ephemeral = Path(tmp)
            bridge = bridge_mod.OwnerBridge(ephemeral, OWNER_KEY)
            before = _file_digests(ephemeral)
            for mode in MODES:
                body = {
                    "text": PROMPT,
                    "mode": mode,
                    "conditioning_confirmed": True,
                    "sensory": SYNTHETIC_SENSOR if mode != "pure_quantum" else None,
                    "quantum": ARCHIVE if mode != "pure_sensory" else None,
                }
                started = time.perf_counter()
                status, response = bridge.dispatch(
                    "POST", "/api/signal-model-probe", "Bearer " + OWNER_KEY,
                    json.dumps(body, allow_nan=False).encode(),
                )
                assert status == 200, (mode, status, response)
                assert response["schema"] == "cosmos-sensory-quantum-native-probe-v1"
                assert response["checkpoint_sha256"] == SHA
                assert response["training_steps"] == STEP
                assert response["mode"] == mode
                assert response["weights_updated"] is False
                assert response["persistent_memory_updated"] is False
                assert response["live_quantum_hardware_used"] is False
                assert response["paid_provider_job_started"] is False
                assert response["source_causality_proven"] is False
                assert response["performance_gain_proven"] is False
                assert len(response["cns7_roles"]) == 7
                assert len(response["cns_dyn12"]) == 12
                assert len(response["fusion"]["vector"]) == 12
                assert len(response["fusion"]["fusion_sha256"]) == 64
                native = response["native_probe"]
                assert native["schema"] == "rawrphos-condition-probe-v2"
                assert native["checkpoint_sha256"] == SHA
                assert native["model_weights_changed"] is False
                assert native["persistent_memory_updated"] is False
                assert native["conditioned_cache_parity"] is True
                assert native["arms"]["conditioned"]["control_vector"] == response["cns_dyn12"]
                assert native["logit_l2_vs_reference"]["zero"] < 1e-6
                assert native["logit_l2_vs_reference"]["conditioned"] > 0
                assert "classical_matched" in native["arms"]
                assert "time_shifted" in native["arms"] if mode != "pure_sensory" else "time_shifted" not in native["arms"]
                telemetry = native["arms"]["conditioned"]["telemetry_by_layer"]
                assert telemetry and all(
                    set(row) == {"gate", "sigma", "state_norm", "omega_mean"}
                    and row["sigma"] > 0 for row in telemetry
                )
                receipts[mode] = {
                    "mode": mode,
                    "checkpoint_sha256": SHA,
                    "fusion_sha256": response["fusion"]["fusion_sha256"],
                    "bridge_packet_sha256": response["bridge_packet_sha256"],
                    "cns_state_sha256": response["cns_state_sha256"],
                    "cns_dyn12": response["cns_dyn12"],
                    "source_families": [s["family"] for s in response["sources"]],
                    "source_execution_modes": [s["execution_mode"] for s in response["sources"]],
                    "qbt_result_digest": response["qbt_result_digest"],
                    "control_sha256": native["arms"]["conditioned"]["control_sha256"],
                    "telemetry_by_layer": telemetry,
                    "logit_l2_vs_reference": native["logit_l2_vs_reference"],
                    "reference_text": native["response_reference"],
                    "conditioned_text": native["response_conditioned"],
                    "cache_parity": native["conditioned_cache_parity"],
                    "generation_metrics": native["generation_metrics"],
                    "resource_metrics": native["resource_metrics"],
                    "wall_end_to_end_ms": round((time.perf_counter() - started) * 1000, 3),
                    "classification": "FIXED_WEIGHT_NUMERICAL_COMPUTATIONAL_SENSITIVITY_ONLY",
                }
                print(
                    "REAL_14K_TYPED_FUSION_PASS", mode, SHA,
                    "conditioned_l2", native["logit_l2_vs_reference"]["conditioned"],
                    "zero_l2", native["logit_l2_vs_reference"]["zero"],
                    "cache_parity", native["conditioned_cache_parity"],
                    "end_to_end_ms", receipts[mode]["wall_end_to_end_ms"],
                    flush=True,
                )
            assert _file_digests(ephemeral) == before, "owner memory mutated during nonpersistent signal probe"
            assert bridge.dispatch("POST", "/api/signal-model-probe", "", b"{}")[0] == 401
            assert bridge.dispatch("GET", "/api/signal-model-probe", "Bearer " + OWNER_KEY)[0] == 404
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({
            "schema": "cosmos-signal-native-14k-acceptance-v1",
            "classification": "PUBLIC_ARCHIVE_SUMMARY_REPLAY_AND_SYNTHETIC_BIO_FIXTURE",
            "fresh_quantum_hardware_executed": False,
            "owner_volume_accessed": False,
            "checkpoint_sha256": SHA,
            "modes": receipts,
        }, indent=2, sort_keys=True) + "\n")
    finally:
        server.should_exit = True
        runner.join(timeout=15)


if __name__ == "__main__":
    if "RUNNER_TEMP" not in os.environ:
        raise SystemExit("RUNNER_TEMP required for isolated acceptance")
    root = Path(os.environ["RUNNER_TEMP"])
    run(root / "step-00014000", Path("build") / "cosmos-signal-native-14k-acceptance.json")
