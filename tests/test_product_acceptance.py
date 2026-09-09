"""End-to-end product acceptance for the 0.7.0 candidate. No production claim."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from beastbox import __version__
from beastbox.cosmic_web import CosmicApp
from beastbox.desktop import RuntimeWorker, ProviderSettings, smoke
from beastbox.durable import DurableRuntime
from beastbox.portable_state import export_snapshot, import_snapshot
from beastbox.product_services import AuthoritySession, capability_inventory
from beastbox.providers import LocalOllamaProvider
from beastbox.sealed_storage import crypto_available, export_sealed_snapshot, import_sealed_snapshot


def test_01_fresh_installation_creates_validated_store(tmp_path: Path) -> None:
    root = tmp_path / "fresh"
    runtime = DurableRuntime(root)
    try:
        inspection = runtime.inspect()
    finally:
        runtime.close()
    assert inspection["valid"] is True
    assert inspection["turn"] == 0
    assert (root / "runtime.sqlite3").is_file()


def test_02_first_launch_is_cold_until_a_turn(tmp_path: Path) -> None:
    app = CosmicApp(tmp_path)
    conversation = app.dispatch("GET", "/api/conversation")
    assert conversation[0] == 200
    assert conversation[1]["first_run"] is True
    assert conversation[1]["turns"] == []
    app.dispatch("POST", "/api/chat", {"text": "hello substrate"})
    restored = CosmicApp(tmp_path).dispatch("GET", "/api/conversation")
    assert restored[0] == 200
    assert restored[1]["first_run"] is False
    assert any(turn["kind"] == "user_turn" and "hello substrate" in turn["text"] for turn in restored[1]["turns"])


def test_03_model_configuration_is_explicit(tmp_path: Path) -> None:
    app = CosmicApp(tmp_path)
    status, body = app.dispatch("POST", "/api/provider", {"kind": "reference", "model": "Brain A"})
    assert status == 200
    assert body["profile"]["model"] == "Brain A"
    dumped = json.dumps(body)
    assert '"api_key":' not in dumped
    assert body["profile"]["api_key_env"] is None


def test_04_conversation_and_05_history_persist(tmp_path: Path) -> None:
    runtime = DurableRuntime(tmp_path)
    try:
        runtime.respond("Remember the code word is SUNFLOWER")
    finally:
        runtime.close()
    restored = DurableRuntime(tmp_path)
    try:
        result = restored.respond("Recall the code word")
        assert any("SUNFLOWER" in hit["text"] for hit in result["memory_hits"])
    finally:
        restored.close()


def test_06_restart_and_07_model_swap_keep_substrate(tmp_path: Path) -> None:
    first = DurableRuntime(tmp_path)
    try:
        first.respond("Remember marigold")
        system = first.inspect()["system_id"]
    finally:
        first.close()
    from beastbox.providers import ReferenceTextProvider

    second = DurableRuntime(tmp_path, ReferenceTextProvider(prefix="Brain B"))
    try:
        after = second.respond("Recall marigold")
        assert second.inspect()["system_id"] == system
        assert after["model"]["model"] == "Brain B"
        assert "marigold" in after["model"]["prompt"]
    finally:
        second.close()


def test_08_09_10_portable_state_and_authority_isolation(tmp_path: Path) -> None:
    origin = tmp_path / "origin"
    runtime = DurableRuntime(origin)
    try:
        runtime.respond("Remember SUNFLOWER")
        before = runtime.inspect()
        runtime.policy.allowed.add("SIMULATED_MOVE")
        assert runtime.policy.allowed
    finally:
        runtime.close()
    bundle = tmp_path / "portable"
    receipt = export_snapshot(origin, bundle)
    assert receipt["authority"] == "NOT_TRANSFERRED"
    target = tmp_path / "imported"
    import_snapshot(bundle, target, receipt["manifest_sha256"])
    restored = DurableRuntime(target)
    try:
        assert restored.inspect()["system_id"] == before["system_id"]
        assert not restored.policy.allowed
    finally:
        restored.close()


@pytest.mark.skipif(not crypto_available(), reason="sealed extra missing")
def test_11_encrypted_storage_roundtrip(tmp_path: Path) -> None:
    origin = tmp_path / "origin"
    DurableRuntime(origin).close()
    runtime = DurableRuntime(origin)
    try:
        runtime.respond("sealed memory")
    finally:
        runtime.close()
    bundle = tmp_path / "sealed"
    receipt = export_sealed_snapshot(origin, bundle, "owner-pass-phrase")
    restored = tmp_path / "restored"
    import_sealed_snapshot(bundle, restored, receipt["manifest_sha256"], "owner-pass-phrase")
    assert (restored / "runtime.sqlite3").is_file()
    assert not (bundle / "runtime.sqlite3").exists()
    checked = DurableRuntime(restored)
    try:
        prompt = checked.respond("recall sealed")["model"]["prompt"]
        assert "sealed memory" in prompt
        assert not checked.policy.allowed
    finally:
        checked.close()


def test_12_unauthorized_user_access_is_denied(tmp_path: Path) -> None:
    from beastbox.profiles import MultiUserGateway, ProfileRegistry

    registry = ProfileRegistry(tmp_path)
    registry.create("A")
    registry.create("B")
    gateway = MultiUserGateway(registry)
    a = gateway.login(name="A")
    b = gateway.login(name="B")
    gateway.dispatch(a["token"], "POST", "/api/chat", {"text": "private to A"})
    denied = gateway.dispatch(b["token"], "POST", "/api/storage/export", {"destination": str(Path(a["profile"]["root"]) / "x")})
    assert denied[0] == 403


def test_13_desktop_packaging_smoke(tmp_path: Path) -> None:
    result = smoke(tmp_path)
    assert result["valid"] is True
    assert result["turn_after"] == result["turn_before"] + 1
    with RuntimeWorker(tmp_path) as worker:
        history = worker.submit("history", ProviderSettings()).result(timeout=10)
    assert any(item["kind"] == "user_turn" for item in history)


def test_14_15_mobile_release_files_are_present() -> None:
    root = Path(__file__).resolve().parents[1]
    android = (root / "apps/android/app/build.gradle.kts").read_text(encoding="utf-8")
    ios = (root / "apps/ios/project.yml").read_text(encoding="utf-8")
    assert 'versionName = "0.7.0"' in android
    assert "BEASTBOX_ANDROID_KEYSTORE" in android
    assert "MARKETING_VERSION: '0.7.0'" in ios
    assert (root / "apps/ios/BeastBox.entitlements").is_file()
    assert (root / "apps/ios/ExportOptions.plist").is_file()


def test_16_clean_installation_does_not_touch_foreign_state(tmp_path: Path) -> None:
    foreign = tmp_path / "other"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("keep")
    DurableRuntime(tmp_path / "mine").close()
    assert (foreign / "keep.txt").read_text() == "keep"


def test_17_plaintext_store_opens_without_migration_flag(tmp_path: Path) -> None:
    root = tmp_path / "legacy"
    DurableRuntime(root).close()
    runtime = DurableRuntime(root)
    try:
        assert runtime.inspect()["valid"] is True
    finally:
        runtime.close()
    assert (root / "runtime.sqlite3").is_file()


def test_18_bad_configuration_is_rejected() -> None:
    with pytest.raises(ValueError):
        LocalOllamaProvider(model="x", base_url="https://example.invalid")


def test_19_missing_model_name_is_rejected() -> None:
    with pytest.raises(ValueError):
        LocalOllamaProvider(model="", base_url="http://127.0.0.1:11434")


def test_20_provider_failure_does_not_fallback(tmp_path: Path) -> None:
    class Boom:
        def generate(self, prompt: str) -> str:
            raise RuntimeError("backend down")

    runtime = DurableRuntime(tmp_path, Boom())  # type: ignore[arg-type]
    try:
        with pytest.raises(RuntimeError, match="backend down"):
            runtime.respond("hello")
        assert runtime.inspect()["turn"] == 0
    finally:
        runtime.close()


def test_21_secret_handling_regression(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = "OPENAI_KEY_TEST_SENTINEL_DO_NOT_PERSIST_12345"
    monkeypatch.setenv("OPENAI_API_KEY", sentinel)
    runtime = DurableRuntime(tmp_path)
    try:
        runtime.respond("hello without the secret")
    finally:
        runtime.close()
    encoded = (tmp_path / "runtime.sqlite3").read_bytes()
    assert sentinel.encode() not in encoded
    authority = AuthoritySession()
    authority.grant("camera")
    bundle = tmp_path / "portable"
    from beastbox.product_services import ProductService

    receipt = ProductService(tmp_path, authority=authority).export_portable(bundle)
    assert receipt["authority"] == "NOT_TRANSFERRED"
    assert sentinel.encode() not in (bundle / "runtime.sqlite3").read_bytes()
    assert sentinel not in (bundle / "manifest.json").read_text(encoding="utf-8")


def test_22_ci_and_package_contract_files_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    assert __version__ == "0.7.0"
    for relative in (
        ".github/workflows/ci.yml",
        ".github/workflows/product-ci.yml",
        ".github/workflows/security-audit.yml",
        "pyproject.toml",
        ".env.example",
        "Makefile",
    ):
        assert (root / relative).is_file()
    inventory = capability_inventory()
    assert inventory["sealed_storage"]["status"] == "IMPLEMENTED_AND_TESTED"
    assert inventory["multi_profile_isolation"]["status"] == "IMPLEMENTED_AND_TESTED"
    assert inventory["custom_voice"]["status"] == "NOT_ESTABLISHED"
