from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_lineage_manifest_preserves_authoritative_freezes_and_boundaries():
    path = ROOT / "experiments" / "zeref" / "LINEAGE_MANIFEST.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    talk4 = data["talk004"]
    assert talk4["checkpoint_sha256"] == "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
    assert talk4["canonical_ledger_records"] == 352
    assert talk4["canonical_ledger_sha256"] == "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
    assert talk4["heartbeat_sha256"] == "19ca6272546d651ff8f1bb0e0184a842f5444b048ff63df6ea12b0be72e030c7"
    assert talk4["immutable"] is True

    live = data["r12_live_loop"]
    assert live["execution_commit"] == "e54af749656e485266a0277e9acdee72ac356df5"

    rho = data["r12_rho_sweep"]
    assert rho["scientific_freeze_commit"] == "61747a940ed15312975684de7ca3ea93154d082f"
    assert rho["workflow_run_id"] == 32973615265
    assert rho["artifact_sha256"] == "c60e1bcee90064d99655e99dd70e37db1fb31631820ea92f1152a6eeaf5bb4a2"
    assert rho["branch_head_is_authoritative_scientific_result"] is False

    contracts = data["mathematical_contracts"]
    assert contracts["dyn12_dimensions"] == 12
    assert contracts["dyn42_dimensions"] == 42
    assert contracts["dyn54_dimensions"] == 54
    assert contracts["dyn54_definition"] == "dyn12 + dyn42 exact concatenation"
    assert contracts["r12_coordinate_12"] == "reality_coupling"
    assert contracts["neural_x54_is_cns7_dyn54"] is False

    boundaries = " ".join(data["claim_boundaries"]).lower()
    assert "consciousness" in boundaries
    assert "biological" in boundaries
    assert "quantum anomaly" in boundaries
