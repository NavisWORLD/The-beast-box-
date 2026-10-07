"""Main deploy contract for the connected Vercel project.

Commit 2da27a844881d0d2b98ce66c1b72bdd6d5647856 intentionally enabled Git
auto-deploys from main. Feature-branch auto-deploys stay off. This file does
not disable manual deploy hooks and cannot attest to remote ignore rules.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_main_git_auto_deployment_is_enabled_and_feature_holds_stay_off():
    config = json.loads((ROOT / "apps/beastbox-cloud/vercel.json").read_text(encoding="utf-8"))
    assert config["git"]["deploymentEnabled"].get("main") is True
    for branch in (
        "feature/cosmic-chaos-vercel-app-001",
        "feature/cosmos-trial-readonly-probe-001",
        "feature/cosmos-bio-permissioned-001",
    ):
        assert config["git"]["deploymentEnabled"].get(branch) is False
