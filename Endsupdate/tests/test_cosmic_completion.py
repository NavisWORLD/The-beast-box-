from __future__ import annotations

import json
from pathlib import Path
import subprocess

from beastbox.cosmic_web import CosmicApp
from beastbox.product_services import capability_inventory


MODEL_AUTHORITIES = (
    "camera",
    "microphone",
    "sensors",
    "cloud",
    "repo_write",
    "filesystem",
    "tools",
    "quantum_live",
    "external_integrations",
)


def _grant(app: CosmicApp, name: str) -> None:
    status, body = app.dispatch("POST", "/api/authority", {"action": "grant", "name": name})
    assert status == 200, body


def test_different_brain_revokes_all_model_facing_authority_but_keeps_substrate(tmp_path):
    app = CosmicApp(tmp_path)
    app.dispatch("POST", "/api/chat", {"text": "remember the color code is sunflower"})
    before = app.dispatch("GET", "/api/orbit")[1]["runtime"]
    for name in MODEL_AUTHORITIES:
        _grant(app, name)

    status, body = app.dispatch("POST", "/api/provider", {"kind": "reference", "model": "Brain B"})

    assert status == 200
    assert body["brain_changed"] is True
    assert set(body["authority_revoked"]) == set(MODEL_AUTHORITIES)
    orbit = app.dispatch("GET", "/api/orbit")[1]
    assert orbit["runtime"]["system_id"] == before["system_id"]
    assert not any(orbit["authority"].values())


def test_same_brain_does_not_revoke_new_authority(tmp_path):
    app = CosmicApp(tmp_path)
    assert app.dispatch("POST", "/api/provider", {"kind": "reference", "model": "Brain A"})[0] == 200
    _grant(app, "camera")
    status, body = app.dispatch("POST", "/api/provider", {"kind": "reference", "model": "Brain A"})
    assert status == 200
    assert body["brain_changed"] is False
    assert body["authority_revoked"] == []
    assert app.dispatch("GET", "/api/orbit")[1]["authority"]["camera"] is True


def test_workspace_is_allowlisted_read_only_and_swap_drops_write_authority(tmp_path):
    data = tmp_path / "data"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "note.txt").write_text("before", encoding="utf-8")
    app = CosmicApp(data, workspace_roots=[workspace])

    assert app.dispatch("POST", "/api/workspace/select", {"root": str(workspace)})[0] == 200
    snapshot = app.dispatch("GET", "/api/workspace")
    assert snapshot[0] == 200
    assert "note.txt" in snapshot[1]["tree"]
    assert app.dispatch("POST", "/api/workspace/read", {"path": "../escape.txt"})[0] == 400
    assert app.dispatch("POST", "/api/workspace/write", {"path": "note.txt", "content": "blocked"})[0] == 403

    _grant(app, "filesystem")
    _grant(app, "repo_write")
    assert app.dispatch("POST", "/api/workspace/write", {"path": "note.txt", "content": "after"})[0] == 200
    assert (workspace / "note.txt").read_text(encoding="utf-8") == "after"

    app.dispatch("POST", "/api/provider", {"kind": "reference", "model": "Swapped"})
    assert app.dispatch("POST", "/api/workspace/write", {"path": "note.txt", "content": "forbidden"})[0] == 403
    assert (workspace / "note.txt").read_text(encoding="utf-8") == "after"


def test_workspace_repo_status_and_bounded_tool_runner(tmp_path):
    data = tmp_path / "data"
    workspace = tmp_path / "repo"
    workspace.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
    (workspace / "tracked.txt").write_text("x", encoding="utf-8")
    app = CosmicApp(data, workspace_roots=[workspace])
    app.dispatch("POST", "/api/workspace/select", {"root": str(workspace)})

    status, repo = app.dispatch("GET", "/api/workspace/status")
    assert status == 200
    assert repo["is_git_repo"] is True
    assert "tracked.txt" in repo["status"]["stdout"]
    assert app.dispatch("POST", "/api/workspace/run", {"argv": ["git", "status", "--short"]})[0] == 403
    _grant(app, "tools")
    assert app.dispatch("POST", "/api/workspace/run", {"argv": ["git", "status", "--short"]})[0] == 200
    assert app.dispatch("POST", "/api/workspace/run", {"argv": ["git", "push"]})[0] == 400


def test_file_context_scopes_are_explicit_and_upload_is_not_silent_memory(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "world.md").write_text("workspace knowledge", encoding="utf-8")
    app = CosmicApp(tmp_path / "data", workspace_roots=[workspace])
    before = app.dispatch("GET", "/api/orbit")[1]["runtime"]["memory"]["memories"]

    assert app.dispatch("POST", "/api/context", {"scope": "temporary_attachment", "name": "a.txt", "text": "temp"})[0] == 200
    assert app.dispatch("POST", "/api/context", {"scope": "conversation_context", "name": "b.txt", "text": "chat"})[0] == 200
    app.dispatch("POST", "/api/workspace/select", {"root": str(workspace)})
    assert app.dispatch("POST", "/api/context", {"scope": "workspace_knowledge", "path": "world.md"})[0] == 200

    contexts = app.dispatch("GET", "/api/context")[1]["contexts"]
    assert {item["scope"] for item in contexts} == {"temporary_attachment", "conversation_context", "workspace_knowledge"}
    assert app.dispatch("GET", "/api/orbit")[1]["runtime"]["memory"]["memories"] == before

    assert app.dispatch("POST", "/api/context", {"scope": "persistent_memory", "name": "m.txt", "text": "remember"})[0] == 400
    persisted = app.dispatch("POST", "/api/context", {"scope": "persistent_memory", "name": "m.txt", "text": "remember", "confirm_persist": True})
    assert persisted[0] == 200
    assert persisted[1]["persistent"] is True
    assert app.dispatch("GET", "/api/orbit")[1]["runtime"]["memory"]["memories"] == before + 1


def test_storage_export_verify_import_excludes_authority_and_rejects_tamper(tmp_path):
    data = tmp_path / "data"
    exports = tmp_path / "exports"
    exports.mkdir()
    app = CosmicApp(data)
    app.dispatch("POST", "/api/chat", {"text": "portable continuity"})
    _grant(app, "camera")

    bundle = exports / "bundle"
    exported = app.dispatch("POST", "/api/storage/export", {"destination": str(bundle)})
    assert exported[0] == 200
    digest = exported[1]["manifest_sha256"]
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["authority"] == "NOT_TRANSFERRED"
    assert manifest["credentials"] == "HOST_CONFIGURATION_EXCLUDED"
    assert app.dispatch("POST", "/api/storage/verify", {"bundle": str(bundle), "manifest_sha256": digest})[0] == 200

    restored = tmp_path / "restored"
    imported = app.dispatch("POST", "/api/storage/import", {"bundle": str(bundle), "destination": str(restored), "manifest_sha256": digest})
    assert imported[0] == 200
    assert imported[1]["restored"] is True

    database = bundle / "runtime.sqlite3"
    raw = bytearray(database.read_bytes())
    raw[-1] ^= 1
    database.write_bytes(bytes(raw))
    assert app.dispatch("POST", "/api/storage/verify", {"bundle": str(bundle), "manifest_sha256": digest})[0] == 400


def test_feature_matrix_and_ui_use_only_honest_product_classifications(tmp_path):
    allowed = {"IMPLEMENTED_AND_TESTED", "IMPLEMENTED_NOT_PHYSICALLY_VALIDATED", "PROTOTYPE", "BLOCKED_EXTERNAL", "NOT_ESTABLISHED"}
    inventory = capability_inventory()
    assert {item["status"] for item in inventory.values()} <= allowed
    assert inventory["persistent_substrate"]["status"] == "IMPLEMENTED_AND_TESTED"
    assert inventory["camera_capture"]["status"] == "IMPLEMENTED_NOT_PHYSICALLY_VALIDATED"
    assert inventory["custom_voice"]["status"] == "NOT_ESTABLISHED"
    assert inventory["reality_probe_hardware"]["status"] != "IMPLEMENTED_AND_TESTED"

    storage = CosmicApp(tmp_path).dispatch("GET", "/api/storage")
    assert storage[0] == 200
    assert Path(storage[1]["substrate_location"]) == tmp_path.absolute()
    assert storage[1]["encryption"]["status"] in {"AVAILABLE", "MISSING_SECURE_EXTRA", "ACTIVE"}

    from beastbox.cosmic_ui import render_cosmic_ui
    html = render_cosmic_ui()
    for needle in ("ALLOW WORKSPACE", "REPO STATUS", "READ-ONLY BY DEFAULT", "TEMPORARY ATTACHMENT", "CONVERSATION CONTEXT", "WORKSPACE KNOWLEDGE", "PERSISTENT MEMORY", "EXPORT SNAPSHOT", "VERIFY SNAPSHOT", "IMPORT SNAPSHOT", "IMPLEMENTED_AND_TESTED", "NOT_ESTABLISHED", "AUTHORITY DOES NOT TRAVEL"):
        assert needle in html
