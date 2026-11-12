"""The promote path must write the served fingerprint, and the three pin files must agree.

Cory: a promotion that changes what the bridge serves writes that fingerprint into
the public pin in the same motion. Step equality alone is not in sync.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "zeref_promote_pin.py"
PIN_REL = Path("apps/beastbox-cloud/lib/rawrphos-public-pin.json")
BRAIN_RELS = (
    Path("apps/beastbox-cloud/lib/companion/brain.mjs"),
    Path("apps/beastbox-cloud/public/spark/shared/brain.mjs"),
)
WORKFLOW = ROOT / ".github/workflows/zeref-bridge-pin-sync-check.yml"


def load():
    spec = importlib.util.spec_from_file_location("zeref_promote_pin", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_pin_tree(tmp_path: Path) -> Path:
    for rel in (PIN_REL, *BRAIN_RELS):
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / rel).read_bytes())
    return tmp_path


def snapshot(root: Path) -> dict[Path, bytes]:
    return {root / rel: (root / rel).read_bytes() for rel in (PIN_REL, *BRAIN_RELS)}


def make_release(weights: bytes, step: int, metadata_sha: str | None = None, sidecar_sha: str | None = None):
    model_sha = hashlib.sha256(weights).hexdigest()
    recorded = model_sha if metadata_sha is None else metadata_sha
    meta = {
        "model_id": "rawrphos-native",
        "lineage": "native-from-scratch",
        "training_steps": step,
        "checkpoint_sha256": recorded,
    }
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        payload = json.dumps(meta).encode()
        for name, data in (
            ("accepted-checkpoint/model.safetensors", weights),
            ("accepted-checkpoint/metadata.json", payload),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    raw = buf.getvalue()
    asset = hashlib.sha256(raw).hexdigest()
    tag = f"zeref-006-cycle-59-{model_sha[:12]}"
    published = asset if sidecar_sha is None else sidecar_sha
    sidecar = f"{published}  {tag}.tar.gz\n".encode()
    return tag, raw, sidecar, model_sha, asset


def fetcher(tag: str, raw: bytes, sidecar: bytes):
    urls = {
        f"https://github.com/NavisWORLD/The-beast-box-/releases/download/{tag}/{tag}.tar.gz": raw,
        f"https://github.com/NavisWORLD/The-beast-box-/releases/download/{tag}/{tag}.tar.gz.sha256": sidecar,
    }

    def fetch(url: str) -> bytes:
        if url not in urls:
            raise OSError(url)
        return urls[url]

    return fetch


def served_fingerprint(mod, root: Path = ROOT) -> tuple[int, str]:
    """Step and sha written into both brain manifests by a promotion."""
    found = []
    for rel in BRAIN_RELS:
        matches = mod.BRAIN_RE.findall((root / rel).read_text(encoding="utf-8"))
        assert len(matches) == 1
        found.append((int(matches[0][1]), matches[0][3]))
    assert found[0] == found[1]
    return found[0]


def published_release(mod, pin: dict, dest: Path) -> tuple[int, str, dict]:
    """Download the release the pin names and return its real step, sha, and chat-eval."""
    promo = pin["promotion"]
    tag = promo["release_tag"]
    assert mod.TAG_RE.fullmatch(tag), tag
    url = mod.asset_url(tag)
    raw = mod.fetch_bytes(url, timeout=300)
    sidecar = mod.fetch_bytes(url + ".sha256", timeout=60)
    asset_sha = hashlib.sha256(raw).hexdigest()
    assert asset_sha == mod.parse_sidecar(sidecar, f"{tag}.tar.gz")
    assert asset_sha == promo["release_asset_sha256"]
    real_step, real_sha = mod.open_checkpoint(raw, dest)
    assert tag.endswith(real_sha[:12])
    report_path = dest / "chat-eval.json"
    assert report_path.is_file() and not report_path.is_symlink()
    report_bytes = report_path.read_bytes()
    assert hashlib.sha256(report_bytes).hexdigest() == promo["chat_eval_sha256"]
    return real_step, real_sha, json.loads(report_bytes)


def assert_gate_record(pin: dict, report: dict) -> None:
    """The published chat-eval is the gate record. Operators stay the eval's."""
    promo = pin["promotion"]
    baseline, candidate = report["baseline"], report["candidate"]
    assert report["chat_not_worse"] is True
    assert promo["chat_not_worse"] is True
    assert report["chat_not_worse"] is all(report["gate"].values())
    assert candidate["ref_nll"] <= baseline["ref_nll"]
    assert promo["candidate_ref_nll"] == candidate["ref_nll"]
    assert promo["baseline_ref_nll"] == baseline["ref_nll"]
    assert candidate["action_leaks"] <= baseline["action_leaks"]
    assert promo["candidate_leaks"] == candidate["action_leaks"]
    assert report["gate"]["ref_nll_not_worse"] is True
    assert report["gate"]["no_more_game_action_leaks"] is True


def test_checked_in_pin_matches_the_live_bridge_fingerprint(tmp_path):
    mod = load()
    pin = json.loads((ROOT / PIN_REL).read_text(encoding="utf-8"))
    step, sha = served_fingerprint(mod)
    assert pin["training_steps"] == step
    assert pin["checkpoint_sha256"] == sha
    assert pin["promotion"]["candidate_sha256"] == sha
    real_step, real_sha, report = published_release(mod, pin, tmp_path)
    assert real_step == step
    assert real_sha == sha
    assert_gate_record(pin, report)


def test_check_cli_passes_on_the_repo():
    ran = subprocess.run([sys.executable, str(SCRIPT), "--check"], cwd=ROOT, capture_output=True, text=True)
    assert ran.returncode == 0, ran.stderr
    assert "PIN_FILES_AGREE" in ran.stdout
    assert "ghp_" not in ran.stdout + ran.stderr
    assert "github_pat_" not in ran.stdout + ran.stderr


def test_check_fails_when_a_brain_sha_drifts(tmp_path):
    mod = load()
    root = copy_pin_tree(tmp_path)
    before = snapshot(root)
    brain = root / BRAIN_RELS[1]
    live_sha = json.loads((root / PIN_REL).read_text(encoding="utf-8"))["checkpoint_sha256"]
    brain.write_text(brain.read_text().replace(live_sha, "ab" * 32))
    with pytest.raises(mod.PromotePinError, match="disagrees"):
        mod.files_agree(root)
    assert (root / PIN_REL).read_bytes() == before[root / PIN_REL]
    assert (root / BRAIN_RELS[0]).read_bytes() == before[root / BRAIN_RELS[0]]


def test_promote_writes_the_served_fingerprint_and_leaves_gates(tmp_path):
    mod = load()
    root = copy_pin_tree(tmp_path)
    original = json.loads((root / PIN_REL).read_text())
    weights = b"served-weights-not-a-real-model"
    step = 37001
    tag, raw, sidecar, model_sha, asset = make_release(weights, step)
    result = mod.promote(tag, root, fetch=fetcher(tag, raw, sidecar))
    assert result == {
        "training_steps": step,
        "checkpoint_sha256": model_sha,
        "release_tag": tag,
        "release_asset_sha256": asset,
    }
    pin = json.loads((root / PIN_REL).read_text())
    assert pin["training_steps"] == step
    assert pin["checkpoint_sha256"] == model_sha
    assert pin["promotion"]["release_tag"] == tag
    assert pin["promotion"]["release_asset_sha256"] == asset
    assert pin["promotion"]["candidate_sha256"] == model_sha
    assert pin["gate_v2"] == original["gate_v2"]
    assert pin["promotion"]["chat_not_worse"] == original["promotion"]["chat_not_worse"]
    assert pin["promotion"]["baseline_ref_nll"] == original["promotion"]["baseline_ref_nll"]
    assert pin["promotion"]["candidate_ref_nll"] == original["promotion"]["candidate_ref_nll"]
    assert pin["promotion"]["decoding"] == original["promotion"]["decoding"]
    assert pin["promotion"]["baseline_sha256"] == original["promotion"]["baseline_sha256"]
    for rel in BRAIN_RELS:
        text = (root / rel).read_text()
        assert f"step: {step}, checkpoint_sha256: \"{model_sha}\"" in text
        base = 'step: 14000, checkpoint_sha256: "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5"'
        assert base in text
    mod.files_agree(root)
    assert not list(root.rglob("*.tmp"))


def test_promote_refuses_metadata_mismatch_without_writing(tmp_path):
    mod = load()
    root = copy_pin_tree(tmp_path)
    before = snapshot(root)
    weights = b"weights"
    tag, raw, sidecar, _model_sha, _asset = make_release(weights, 37002, metadata_sha="cd" * 32)
    with pytest.raises(mod.PromotePinError, match="metadata mismatch"):
        mod.promote(tag, root, fetch=fetcher(tag, raw, sidecar))
    assert snapshot(root) == before


def test_promote_refuses_sidecar_mismatch_without_writing(tmp_path):
    mod = load()
    root = copy_pin_tree(tmp_path)
    before = snapshot(root)
    tag, raw, sidecar, _model_sha, _asset = make_release(b"weights", 37003, sidecar_sha="ab" * 32)
    with pytest.raises(mod.PromotePinError, match="asset sha256 mismatch"):
        mod.promote(tag, root, fetch=fetcher(tag, raw, sidecar))
    assert snapshot(root) == before


def test_promote_refuses_a_tag_that_does_not_name_the_model(tmp_path):
    mod = load()
    root = copy_pin_tree(tmp_path)
    before = snapshot(root)
    tag, raw, sidecar, model_sha, _asset = make_release(b"weights", 37004)
    lied = "zeref-006-cycle-59-" + ("0" * 12)
    assert not lied.endswith(model_sha[:12])
    side = sidecar.replace(tag.encode(), lied.encode())
    with pytest.raises(mod.PromotePinError):
        mod.promote(lied, root, fetch=fetcher(lied, raw, side))
    assert snapshot(root) == before


def test_promote_refuses_path_escape_without_writing(tmp_path):
    mod = load()
    root = copy_pin_tree(tmp_path)
    before = snapshot(root)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = b"nope"
        info = tarfile.TarInfo("../outside.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    raw = buf.getvalue()
    asset = hashlib.sha256(raw).hexdigest()
    tag = "zeref-006-cycle-59-" + ("ab" * 6)
    sidecar = f"{asset}  {tag}.tar.gz\n".encode()
    with pytest.raises(mod.PromotePinError):
        mod.promote(tag, root, fetch=fetcher(tag, raw, sidecar))
    assert snapshot(root) == before
    assert not (tmp_path / "outside.txt").exists()


def test_partial_rename_restores_every_file(tmp_path, monkeypatch):
    mod = load()
    root = copy_pin_tree(tmp_path)
    before = snapshot(root)
    tag, raw, sidecar, _model_sha, _asset = make_release(b"weights", 37005)
    real = os.replace
    calls = {"n": 0}

    def boom(src, dst):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("disk")
        return real(src, dst)

    monkeypatch.setattr(mod.os, "replace", boom)
    with pytest.raises(OSError, match="disk"):
        mod.promote(tag, root, fetch=fetcher(tag, raw, sidecar))
    assert snapshot(root) == before


def test_bridge_serves_pin_requires_sha_and_serving_pin():
    mod = load()
    sha = "a" * 64
    other = "b" * 64
    assert mod.bridge_serves_pin({"serving_pin": True, "served_checkpoint_sha256": sha}, sha) is True
    served_but_not_ready = {"serving_pin": False, "served_checkpoint_sha256": sha, "served_step": 36784}
    same_step_old_model = {"serving_pin": True, "served_checkpoint_sha256": other, "served_step": 36784}
    assert mod.bridge_serves_pin(served_but_not_ready, sha) is False
    assert mod.bridge_serves_pin(same_step_old_model, sha) is False
    assert mod.bridge_serves_pin({"serving_pin": "true", "served_checkpoint_sha256": sha}, sha) is False
    assert mod.bridge_serves_pin({"served_step": 36784}, sha) is False


def test_poll_retries_then_fails_loudly_on_the_same_step_different_model():
    mod = load()
    pin_sha = "61" + "ff" * 31
    old_sha = "f8" + "f2" * 31
    sleeps: list[float] = []
    lines: list[str] = []
    health = {"serving_pin": True, "served_step": 36784, "served_checkpoint_sha256": old_sha}
    with pytest.raises(mod.PromotePinError, match="does not match") as caught:
        mod.poll_bridge(lambda: health, pin_sha, attempts=3, delay=0.5, sleep=sleeps.append, echo=lines.append)
    assert pin_sha in str(caught.value) and old_sha in str(caught.value)
    assert "serving_pin=True" in str(caught.value)
    assert sleeps == [0.5, 0.5]
    assert not any("BRIDGE_IN_SYNC" in line for line in lines)


def test_poll_accepts_the_matching_bridge_inside_the_window():
    mod = load()
    sha = "c" * 64
    seen = {"n": 0}

    def fetch():
        seen["n"] += 1
        if seen["n"] < 3:
            return {"serving_pin": False, "served_checkpoint_sha256": None}
        return {"serving_pin": True, "served_checkpoint_sha256": sha}

    sleeps: list[float] = []
    mod.poll_bridge(fetch, sha, attempts=5, delay=1, sleep=sleeps.append, echo=lambda _line: None)
    assert seen["n"] == 3
    assert sleeps == [1, 1]


def test_sync_workflow_delegates_to_the_sha_check():
    text = WORKFLOW.read_text()
    assert "python scripts/zeref_promote_pin.py --await-bridge" in text
    assert '[ "$got" = "$want" ]' not in text
    assert "training_steps" not in text
    assert "/api/guest" not in text
