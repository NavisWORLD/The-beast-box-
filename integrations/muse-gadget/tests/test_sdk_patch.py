"""Apply the patch to a real Muse Linux Device SDK checkout and drive it.

Needs the SDK (pinned in sdk_patch/SDK_COMMIT). Point MUSE_SDK_DIR at its
linux/ directory; CI clones it. Skipped when it is not available.
"""

import copy
import importlib
import json
import os
import shutil
import sys
import threading

import pytest

from browser_sim import FakeBrowser
from conftest import ROOT

from beastbox_musegadget import beast as b
from beastbox_musegadget import bridge

SDK = os.environ.get("MUSE_SDK_DIR")
pytestmark = pytest.mark.skipif(not SDK or not os.path.isdir(os.path.join(SDK or "", "src", "musegadget")),
                                reason="set MUSE_SDK_DIR to the Muse Gadget SDK's linux/ directory")


@pytest.fixture
def patched(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "sdk_patch"))
    import apply as patcher
    target = tmp_path / "linux"
    shutil.copytree(SDK, target, ignore=shutil.ignore_patterns(".venv", "__pycache__"))
    changed = patcher.apply(target)
    assert changed == ["src/musegadget/beastbox_commands.py", "src/musegadget/executor.py", "src/musegadget/service.py"]
    assert patcher.apply(target) == ["src/musegadget/beastbox_commands.py"]  # idempotent
    for name in list(sys.modules):
        if name == "musegadget" or name.startswith("musegadget."):
            del sys.modules[name]
    monkeypatch.syspath_prepend(str(target / "src"))
    yield importlib.import_module("musegadget.executor"), target
    for name in list(sys.modules):
        if name == "musegadget" or name.startswith("musegadget."):
            del sys.modules[name]


def test_patch_registers_commands_without_removing_any(patched):
    executor, _ = patched
    names = set(executor.COMMAND_SPECS)
    assert {"system.run", "file.read", "file.write", "device.health"} <= names
    assert {"beastbox.status", "beastbox.feed", "beastbox.play", "beastbox.talk", "beastbox.attack",
            "beastbox.moves", "beastbox.lost_cosmos", "beastbox.link", "beastbox.links"} <= names
    link_client = importlib.import_module("musegadget.link_client")
    device = link_client.DeviceDescription("homelink-abc123", "Beast Box", "0.1.0", executor.COMMAND_SPECS)
    params = device.register_params()
    assert params["display_name"] == "Beast Box" and "beastbox.talk" in params["commands_v2"]


def test_display_name_env(patched, monkeypatch):
    importlib.import_module("musegadget.executor")
    service = importlib.import_module("musegadget.service")
    identity = importlib.import_module("musegadget.identity")
    ident = identity.Identity("02:11:22:33:44:55")
    monkeypatch.setenv("MUSEGADGET_DISPLAY_NAME", "Beast Box")
    assert service.Service(identity=ident, executor=None).display_name == "Beast Box"
    monkeypatch.delenv("MUSEGADGET_DISPLAY_NAME")
    assert service.Service(identity=ident, executor=None).display_name == __import__("socket").gethostname()
    assert ident.ble_name == "MuseGadget334455"  # the BLE name is fixed by the SDK


def _executor(executor_mod, home, monkeypatch):
    original = executor_mod.Executor._child_options

    def options(self):
        opts = original(self)
        opts["env"]["PYTHONPATH"] = str(ROOT)  # on a device the package is installed in the venv
        return opts

    monkeypatch.setattr(executor_mod.Executor, "_child_options", options)
    account = executor_mod.Account.current()
    return executor_mod.Executor(executor_mod.Account(account.name, account.uid, account.gid, str(home)))


def _write_config(home, cfg):
    path = home / ".config" / "beastbox-musegadget" / "config.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"snapshot": cfg.snapshot, "state_dir": cfg.state_dir,
                                "ollama_host": cfg.ollama_host, "bridge_url": cfg.bridge_url,
                                "bridge_timeout_s": 5}))


def test_sdk_executor_runs_beastbox_commands_as_the_account(patched, cfg, tmp_path, monkeypatch):
    executor_mod, _ = patched
    home = tmp_path / "home"
    _write_config(home, cfg)
    ex = _executor(executor_mod, home, monkeypatch)
    out = ex.run("beastbox.status", {})
    assert out["ok"], out
    assert out["payload"]["beast"]["name"] == "Rimecoil"
    fed = ex.run("beastbox.feed", {"food": "frost apples"})
    assert fed["payload"]["beast"]["name"] == "Glacecoil"
    assert ex.run("beastbox.talk", {})["error"] == "message is required"
    assert ex.run("device.health", {})["ok"]  # SDK commands still work


def test_fake_muse_invoke_changes_the_browser_beast(patched, cfg, tmp_path, monkeypatch, fixture_session):
    """Muse -> SDK Executor -> gadget command -> bridge -> browser tab -> state back."""
    executor_mod, _ = patched
    store = bridge.BridgeStore(cfg.state_path)
    server = bridge.make_server(store, "127.0.0.1", 0, ["http://localhost:3000"])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    cfg.bridge_url = url
    home = tmp_path / "home"
    _write_config(home, cfg)
    ex = _executor(executor_mod, home, monkeypatch)
    tab = FakeBrowser(url, b.session_from_any(copy.deepcopy(fixture_session)))
    try:
        code = tab.pair("Cory laptop")
        assert ex.run("beastbox.link", {"code": code})["ok"]
        tab.claim()
        tab.start()
        assert tab.connected.wait(5)
        # The same message the Muse sends on /link-control, handled as LinkSession does.
        invoke = {"method": "link.invoke", "id": "inv-1", "command": "beastbox.feed", "params": {}}
        result = ex.run(invoke["command"], invoke["params"], invoke.get("timeout_ms"))
        assert result["ok"], result
        assert result["payload"]["source"].startswith("live browser beast")
        assert tab.session["beast"]["xp"] == 42 and b.shown_name(tab.session["beast"]) == "Glacecoil"
        links = ex.run("beastbox.links", {})["payload"]["links"]
        assert links[0]["label"] == "Cory laptop" and links[0]["connected"]
    finally:
        tab.stop()
        server.shutdown()
        server.server_close()
