"""Merge-time no-production-git-deploy contract for the connected Vercel project.

The repository setting prevents Vercel main Git auto-deploys where this file
is the project's active root configuration. It does not disable external
manual deploy hooks and cannot attest to remotely configured ignored paths.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_main_git_auto_deployment_is_explicitly_disabled_during_release_hold():
    config = json.loads((ROOT / "apps/beastbox-cloud/vercel.json").read_text(encoding="utf-8"))
    assert config["git"]["deploymentEnabled"].get("main") is False
    for branch in (
        "feature/cosmic-chaos-vercel-app-001",
        "feature/cosmos-trial-readonly-probe-001",
        "feature/cosmos-bio-permissioned-001",
    ):
        assert config["git"]["deploymentEnabled"].get(branch) is False
