"""Language-neutral requests exercise the real durable runtime in fresh processes."""
import json
import subprocess
import sys

import pytest


def exchange(root, request, model="A"):
    return subprocess.run([sys.executable, "-m", "beastbox", "runtime", "exchange",
                           "--data-dir", str(root), "--model", model],
                          input=json.dumps(request), text=True, capture_output=True)


def test_exchange_restart_and_model_replacement(tmp_path):
    root = tmp_path / "state"
    for model in ("A", "B", "A"):
        r = exchange(root, {"schema": "beastbox-request-v1", "operation": "chat",
                            "text": "remember sunflower password lavender"}, model)
        assert r.returncode == 0, r.stderr
        body = json.loads(r.stdout)
        assert body["schema"] == "beastbox-response-v1"
        assert body["ok"] is True
    r = exchange(root, {"schema": "beastbox-request-v1", "operation": "inspect"})
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["result"]["turn"] == 3


@pytest.mark.parametrize("payload", [
    {"schema": "beastbox-request-v1", "operation": "shell", "text": "whoami"},
    {"schema": "beastbox-request-v1", "operation": "chat", "text": "hi", "authority": True},
    {"schema": "wrong", "operation": "inspect"},
    [],
])
def test_exchange_rejects_invalid_before_store_creation(tmp_path, payload):
    root = tmp_path / "absent"
    r = exchange(root, payload)
    assert r.returncode != 0
    assert not root.exists()


def test_exchange_missing_inspection_does_not_invent_store(tmp_path):
    root = tmp_path / "missing"
    r = exchange(root, {"schema": "beastbox-request-v1", "operation": "inspect"})
    assert r.returncode != 0
    assert not root.exists()


def test_exchange_rejects_oversized_request(tmp_path):
    r = exchange(tmp_path / "missing", {"schema": "beastbox-request-v1", "operation": "chat", "text": "x" * 20000})
    assert r.returncode != 0
    assert not (tmp_path / "missing").exists()
