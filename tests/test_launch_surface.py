import json

import pytest

from beastbox.durable import DurableRuntime
from beastbox.doctor import run_doctor
from beastbox.portable_state import export_snapshot, import_snapshot, verify_snapshot


def test_doctor_cold_then_recovered(tmp_path):
    root = tmp_path / "state"
    cold = run_doctor(data_dir=root)
    assert cold["ok"] and cold["recovery"]["status"] == "COLD_START"
    assert not root.exists()
    with_runtime = DurableRuntime(root)
    with_runtime.respond("SUNFLOWER")
    with_runtime.close()
    assert run_doctor(data_dir=root)["recovery"]["status"] == "VERIFIED"


def test_doctor_corruption_fails(tmp_path):
    (tmp_path / "runtime.sqlite3").write_bytes(b"corrupt")
    assert run_doctor(data_dir=tmp_path)["ok"] is False


def test_portable_roundtrip_authority_and_conflict(tmp_path):
    origin = tmp_path / "origin"
    runtime = DurableRuntime(origin, allow_simulated_tool=True)
    runtime.respond("Remember SUNFLOWER")
    before = runtime.inspect()
    runtime.close()
    (origin / "credentials.env").write_text("NEVER COPY THIS")
    bundle = tmp_path / "portable"
    manifest = export_snapshot(origin, bundle)
    assert set(p.name for p in bundle.iterdir()) == {"manifest.json", "runtime.sqlite3"}
    assert verify_snapshot(bundle, manifest["manifest_sha256"])["verified"]
    target = tmp_path / "new-machine"
    import_snapshot(bundle, target, manifest["manifest_sha256"])
    restored = DurableRuntime(target)
    assert restored.inspect() == before
    assert "SUNFLOWER" in restored.respond("Recall SUNFLOWER")["model"]["prompt"]
    assert not restored.policy.allowed
    restored.close()
    with pytest.raises(ValueError):
        import_snapshot(bundle, target, manifest["manifest_sha256"])


@pytest.mark.parametrize("corruption", ["database", "manifest", "extra", "wrong-hash"])
def test_portable_fail_closed(tmp_path, corruption):
    runtime = DurableRuntime(tmp_path / "state")
    runtime.close()
    bundle = tmp_path / "portable"
    receipt = export_snapshot(tmp_path / "state", bundle)
    if corruption == "database":
        (bundle / "runtime.sqlite3").write_bytes(b"bad")
    elif corruption == "manifest":
        p = bundle / "manifest.json"
        d = json.loads(p.read_text())
        d["permissions"] = ["shell"]
        p.write_text(json.dumps(d))
    elif corruption == "extra":
        (bundle / "credentials.env").write_text("bad")
    with pytest.raises((ValueError, RuntimeError)):
        import_snapshot(
            bundle, tmp_path / "restored", "0" * 64 if corruption == "wrong-hash" else receipt["manifest_sha256"]
        )
    assert not (tmp_path / "restored").exists()


def test_export_blocks_known_credentials(tmp_path, monkeypatch):
    token = "test-only-secret-abcdefghijklmnop"
    monkeypatch.setenv("IBM_QUANTUM_TOKEN", token)
    runtime = DurableRuntime(tmp_path / "state")
    runtime.respond(token)
    runtime.close()
    with pytest.raises(ValueError, match="credential"):
        export_snapshot(tmp_path / "state", tmp_path / "portable")
    assert not (tmp_path / "portable").exists()
