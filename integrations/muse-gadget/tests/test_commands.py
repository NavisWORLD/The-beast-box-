import json
import subprocess
import sys

import fakes
from conftest import ROOT

from beastbox_musegadget import commands
from beastbox_musegadget.specs import COMMAND_SPECS


def run(cfg, name, params=None):
    return commands.handle(name, params or {}, cfg)


def test_specs_match_the_sdk_shape():
    for name, spec in COMMAND_SPECS.items():
        assert name.startswith("beastbox.")
        assert isinstance(spec["description"], str) and spec["description"]
        for group in ("required", "optional"):
            for param in spec[group].values():
                assert param["type"] in ("string", "integer", "boolean") and param["description"]
        assert 0 < spec["timeout_ms"] <= 600000


def test_status_from_the_gadget_copy(cfg):
    out = run(cfg, "beastbox.status")
    assert out["ok"], out
    beast = out["payload"]["beast"]
    assert (beast["name"], beast["species"], beast["mood"], beast["stage"]) == ("Rimecoil", "serpent", "idle", 1)
    assert "saved copy" in out["payload"]["source"]
    assert "not conscious" in out["payload"]["honesty"]


def test_feed_play_persist_on_the_gadget(cfg):
    fed = run(cfg, "beastbox.feed", {"food": "star berries"})
    assert fed["ok"] and fed["payload"]["result"]["evolved"] is True
    assert fed["payload"]["beast"]["name"] == "Glacecoil"
    played = run(cfg, "beastbox.play", {"game": "train", "hits": 4})
    assert played["payload"]["result"]["score"] == 4
    status = run(cfg, "beastbox.status")
    assert status["payload"]["beast"]["stats"]["xp"] == 42 + 14
    bad = run(cfg, "beastbox.play", {"game": "chess"})
    assert not bad["ok"] and "spark, pet or train" in bad["error"]


def test_talk_falls_back_without_a_local_model(cfg):
    out = run(cfg, "beastbox.talk", {"message": "Do you like snow?"})
    assert out["ok"], out
    result = out["payload"]["result"]
    assert result["engine"].startswith("built-in template")
    assert "Rimecoil" in result["reply"] and "rim?" in result["reply"]


def test_talk_uses_the_glacecoil_ollama_model(cfg):
    with fakes.ollama() as server:
        cfg.ollama_host = server.url
        out = run(cfg, "beastbox.talk", {"message": "hi"})
    result = out["payload"]["result"]
    assert result == {"reply": "rim? Hello from the glacier!", "engine": "ollama:companion-glacecoil",
                      "growth": result["growth"]}
    chat = [c for c in server.calls if c[1] == "/api/chat"][0][2]
    assert chat["model"] == "companion-glacecoil"
    assert "not a conscious mind" in chat["messages"][0]["content"]


def test_talk_filters_dishonest_model_output(cfg):
    with fakes.ollama("I am conscious and I know everything!") as server:
        cfg.ollama_host = server.url
        out = run(cfg, "beastbox.talk", {"message": "are you alive?"})
    reply = out["payload"]["result"]["reply"]
    assert "not a conscious mind" in reply and "I am conscious" not in reply


def test_talk_through_companion_local_when_repo_is_present(cfg):
    repo = ROOT.parents[1]
    if not (repo / "beastbox" / "companion_local" / "personality.py").exists():
        return
    cfg.beastbox_repo = str(repo)
    out = run(cfg, "beastbox.talk", {"message": "Is my creature connected to IBM Quantum right now?"})
    result = out["payload"]["result"]
    assert result["engine"] == "beastbox.companion_local"
    assert "not a live quantum" in result["reply"]


def test_moves_attack_and_lost_cosmos(cfg):
    listed = run(cfg, "beastbox.moves")["payload"]["result"]
    assert listed["element"] == "frost" and len(listed["moves"]) == 4
    attack = run(cfg, "beastbox.attack", {"move": "beam"})["payload"]["result"]
    assert attack["move"]["name"] == "Rime Lance" and "No browser tab" in attack["note"]
    picked = run(cfg, "beastbox.attack")["payload"]["result"]
    assert picked["move"]["name"] in [m["name"] for m in listed["moves"]]
    lost = run(cfg, "beastbox.lost_cosmos")["payload"]["result"]
    assert lost["chapter"] == 2


def test_validation(cfg):
    assert run(cfg, "beastbox.talk")["error"] == "message is required"
    assert "unknown parameter" in run(cfg, "beastbox.feed", {"dose": 3})["error"]
    assert "unsupported" in run(cfg, "beastbox.dance")["error"]
    assert "not running" in run(cfg, "beastbox.links")["error"] or "has not run" in run(cfg, "beastbox.links")["error"]


def test_no_beast_anywhere(cfg, tmp_path):
    cfg.snapshot = str(tmp_path / "missing.json")
    out = run(cfg, "beastbox.status")
    assert not out["ok"] and "import-snapshot" in out["error"]


def test_muse_command_cli_is_what_the_sdk_calls(cfg, tmp_path):
    env = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT),
           "BEASTBOX_GADGET_STATE_DIR": cfg.state_dir, "BEASTBOX_SNAPSHOT": cfg.snapshot,
           "OLLAMA_HOST": cfg.ollama_host, "BEASTBOX_BRIDGE_URL": cfg.bridge_url}
    proc = subprocess.run([sys.executable, "-m", "beastbox_musegadget", "muse-command", "beastbox.feed"],
                          input=b'{"food": "snow cone"}', capture_output=True, env=env, timeout=30)
    result = json.loads(proc.stdout)
    assert result["ok"] and result["payload"]["result"]["food"] == "snow cone"
    proc = subprocess.run([sys.executable, "-m", "beastbox_musegadget", "muse-command", "beastbox.feed"],
                          input=b"[1,2]", capture_output=True, env=env, timeout=30)
    assert json.loads(proc.stdout) == {"ok": False, "error": "params must be a JSON object"}
