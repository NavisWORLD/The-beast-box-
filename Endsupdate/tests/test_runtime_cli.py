import hashlib
import json
import subprocess
import sys

from beastbox import providers

import pytest


def cli(*args, ok=True):
    result = subprocess.run([sys.executable, "-m", "beastbox", "runtime", *map(str, args)], capture_output=True, text=True)
    assert (result.returncode == 0) == ok, result.stderr
    return json.loads(result.stdout) if ok else result


def test_cli_restart_backup_and_verified_restore(tmp_path):
    root = tmp_path / "runtime"
    first = cli("chat", "sunflower code marigold", "--data-dir", root)
    second = cli("chat", "sunflower code", "--data-dir", root, "--model", "B")
    assert second["checkpoint"]["sequence"] == 2
    assert any("marigold" in m["text"] for m in second["memory_hits"])
    backup = tmp_path / "backup.sqlite3"
    receipt = cli("backup", backup, "--data-dir", root)
    assert receipt["sha256"] == hashlib.sha256(backup.read_bytes()).hexdigest()
    restored = tmp_path / "restored"
    cli("restore", backup, "--data-dir", restored, "--sha256", "0" * 64, ok=False)
    assert not restored.exists()
    cli("restore", backup, "--data-dir", restored, "--sha256", receipt["sha256"])
    inspection = cli("inspect", "--data-dir", restored)
    assert inspection["system_id"] == first["checkpoint"]["system_id"]
    assert inspection["turn"] == 2
    cli("restore", backup, "--data-dir", restored, "--sha256", receipt["sha256"], ok=False)


def test_inspect_missing_source_does_not_create_store(tmp_path):
    cli("inspect", "--data-dir", tmp_path / "absent", ok=False)
    assert not (tmp_path / "absent").exists()


@pytest.mark.parametrize("url", ["file://localhost/etc/passwd", "http://user:password@localhost:11434", "https://example.com", "http://localhost:11434/#secret"])
def test_provider_rejects_non_http_or_credential_urls(url):
    with pytest.raises(ValueError):
        providers.LocalOllamaProvider(base_url=url)
    from beastbox.cypher.models import assert_loopback
    with pytest.raises(ValueError):
        assert_loopback(url)


def test_provider_does_not_follow_redirect_or_environment_proxy(monkeypatch):
    # Verify the actual opener contract without contacting an external service.
    assert hasattr(providers, "_local_opener"), "local opener must reject redirects and proxies"
    monkeypatch.setenv("HTTP_PROXY", "http://example.com:9999")
    opener = providers._local_opener()
    from urllib.request import Request
    from urllib.error import HTTPError
    for handler in opener.handlers:
        if hasattr(handler, "redirect_request"):
            with pytest.raises(HTTPError):
                handler.redirect_request(Request("http://localhost/"), None, 302, "redirect", {}, "http://example.com/")
    assert not any(getattr(h, "proxies", {}) for h in opener.handlers)


def test_symlink_store_rejected(tmp_path):
    from beastbox.runtime import DurableRuntime
    target = tmp_path / "target"
    target.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        DurableRuntime(linked)


def test_restore_rejects_live_wal_database(tmp_path):
    from beastbox.runtime import DurableRuntime
    from beastbox.runtime_cli import file_sha256, restore_database
    source = tmp_path / "live"
    runtime = DurableRuntime(source)
    runtime.respond("memory is still in WAL")
    db = source / "runtime.sqlite3"
    try:
        with pytest.raises((RuntimeError, ValueError), match="WAL|checkpoint"):
            restore_database(db, tmp_path / "restored", file_sha256(db))
    finally:
        runtime.close()
