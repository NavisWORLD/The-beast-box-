"""Owner-only original CPU model switching never grants cloud or changes substrate."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "owner_bridge.py"
SPEC = importlib.util.spec_from_file_location("owner_bridge_qc67_tests", SOURCE)
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)
TOKEN = "fixture-owner-only-token-0123456789-abcdef"
AUTH = "Bearer " + TOKEN


def ready(model):
    return {"choice": model.replace("-", "_"), "model": model,
            "kind": "local", "configured": True,
            "readiness": "INSTALLED_AND_READY", "requires_spend_approval": False,
            "origin": "phera-ra/QC67_cosmo",
            "checkpoint_sha256": BRIDGE.QC67_PINS[model]}


def test_original_model_swap_reuses_existing_substrate_and_revokes_cloud():
    with tempfile.TemporaryDirectory() as directory:
        with patch.dict(os.environ, {"BEASTBOX_QC67_LOCAL_ENABLED": "yes",
                                      "BEASTBOX_TINY_LOCAL_ENABLED": "no"}, clear=False):
            with patch.object(BRIDGE, "qc67_status", side_effect=ready):
                bridge = BRIDGE.OwnerBridge(Path(directory), TOKEN)
                code, orbit = bridge.dispatch("GET", "/api/orbit", AUTH)
                assert code == 200
                first_id = orbit["runtime"]["system_id"]
                code, _ = bridge.dispatch("GET", "/api/models", "")
                assert code == 401
                code, before = bridge.dispatch("GET", "/api/models", AUTH)
                assert code == 200
                assert any(row["choice"] == "qc67_phos" for row in before["choices"])
                for model in ("qc67_phos", "qc67_samgo", "qc67_phos"):
                    code, res = bridge.dispatch("POST", "/api/models", AUTH,
                                                 json.dumps({"choice": model}).encode())
                    assert code == 200, res
                    assert res["no_paid_inference"] is True
                    assert res["substrate"] == "EXISTING_DURABLE_STATE"
                    assert res["checkpoint_sha256"] == BRIDGE.QC67_PINS[model.replace("_", "-")]
                    assert not bridge.app.authority.allowed("cloud")
                    code, orbit2 = bridge.dispatch("GET", "/api/orbit", AUTH)
                    assert code == 200
                    assert orbit2["runtime"]["system_id"] == first_id
                restarted = BRIDGE.OwnerBridge(Path(directory), TOKEN)
                assert restarted.app.profile.model == "qc67-phos"
                assert restarted.app.profile.base_url == BRIDGE.QC67_URL


def test_original_selection_fails_closed_without_attested_sidecar():
    with tempfile.TemporaryDirectory() as directory:
        with patch.dict(os.environ, {"BEASTBOX_QC67_LOCAL_ENABLED": "no",
                                      "BEASTBOX_TINY_LOCAL_ENABLED": "no"}, clear=False):
            bridge = BRIDGE.OwnerBridge(Path(directory), TOKEN)
            before = bridge.app.profile
            for model in ("qc67_phos", "qc67_samgo"):
                code, _ = bridge.dispatch("POST", "/api/models", AUTH,
                                          json.dumps({"choice": model}).encode())
                assert code == 503
                assert bridge.app.profile == before
