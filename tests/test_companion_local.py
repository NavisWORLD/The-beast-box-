"""Local companion personality, memory, senses, and simulated-run tests."""

from __future__ import annotations

import json
from pathlib import Path

from beastbox.companion_local.memory import CompanionMemory
from beastbox.companion_local.personality import birth, load_opt_in_chat, reply, violates_honesty
from beastbox.companion_local.pipeline import prepare
from beastbox.companion_local.senses import accept_hearing, accept_vision, simulate_live
from beastbox.companion_local.spark_bridge import load
from beastbox.companion_local.train import accelerator_status, run_full_qlora
from beastbox.cypher.gguf import inspect_gguf
from beastbox.cypher.registry import ModelRegistry


def test_voice_follows_recorded_seed_and_changes_with_signal():
    serene = birth("serene")
    sparky = birth("sparky")
    assert serene["card"]["seed"] != sparky["card"]["seed"]
    assert serene["card"]["quantum_run"].startswith("ibm_")
    assert serene["card"]["claims"]["conscious"] is False
    assert "not omniscient" in serene["card"]["honesty"]
    assert serene["card"]["name"] in reply(serene["card"], "Hello little one")
    assert not violates_honesty(reply(serene["card"], "Are you conscious?"))


def test_smoke_pipeline_scores_and_registers(tmp_path: Path):
    chat = tmp_path / "chat.json"
    chat.write_text(json.dumps({
        "opt_in": True,
        "messages": [{"role": "user", "content": "keeper nickname is Pebble"}],
    }), encoding="utf-8")
    report = prepare(tmp_path / "run", chat_export=chat, full=True, base=tmp_path / "missing-base")
    assert report["eval"]["personality_consistency"] == 1.0
    assert report["eval"]["lore_recall"] == 1.0
    assert report["eval"]["no_false_claims"] == 1.0
    assert report["eval"]["lora_preference"] == 1.0
    assert report["train"]["loss_end"] < report["train"]["loss_start"]
    assert report["full"]["status"] == "SKIPPED_NO_GPU"
    assert report["reload_preference"] == 1.0
    gguf = inspect_gguf(tmp_path / "run" / "companion-smoke.gguf")
    assert gguf["architecture"] == "companion"
    assert gguf["version"] == 3
    assert gguf["tensor_count"] == 2
    modelfile = (tmp_path / "run" / "Modelfile").read_text(encoding="utf-8")
    assert "FROM ./companion-smoke.gguf" in modelfile
    assert "SYSTEM" in modelfile
    assert "not omniscient" in modelfile
    catalog = json.loads((tmp_path / "run" / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["does_not_replace_cosmos_provider"] is True
    assert catalog["models"][0]["selectable"] is True
    registered = ModelRegistry(tmp_path / "run" / "cypher-models.json")
    spec = registered.get(catalog["models"][0]["alias"])
    assert spec.backend == "ollama"
    assert spec.base_url == "http://127.0.0.1:11434"
    train_lines = (tmp_path / "run" / "train.jsonl").read_text(encoding="utf-8").splitlines()
    eval_users = {
        json.loads(line)[1]["content"]
        for line in (tmp_path / "run" / "eval.jsonl").read_text(encoding="utf-8").splitlines()
    }
    train_users = {json.loads(line)[1]["content"] for line in train_lines}
    assert "keeper nickname is Pebble" not in eval_users
    assert any("Pebble" in line for line in train_lines)
    assert "Hello little one, what are you like?" in eval_users
    assert "Hello little one, what are you like?" not in train_users


def test_opt_in_chat_is_required(tmp_path: Path):
    path = tmp_path / "nope.json"
    path.write_text(json.dumps({"messages": [{"role": "user", "content": "secret"}]}), encoding="utf-8")
    try:
        load_opt_in_chat(path)
    except ValueError as exc:
        assert "opt_in" in str(exc)
    else:
        raise AssertionError("chat export without opt_in was accepted")


def test_memory_grows_searches_and_exports_qbeast(tmp_path: Path):
    born = birth()
    store = CompanionMemory(tmp_path / "memory.json")
    store.add("keeper nickname is Pebble", "note", "chat")
    store.add("a bright desk lamp", "vision", "moondream")
    reloaded = CompanionMemory(tmp_path / "memory.json")
    assert len(reloaded.records) == 2
    assert "Pebble" in reloaded.search("what nickname")[0]["text"]
    text = reloaded.export_qbeast(born["genome"])
    loaded = load()["load_qbeast"](text)
    assert len(loaded["snapshot"]["events"]) == 3
    assert "Pebble" in loaded["snapshot"]["events"][1]["payload"]["summary"]
    try:
        store.add("api_key sk-test", "note", "chat")
    except ValueError:
        pass
    else:
        raise AssertionError("private memory was stored")


def test_senses_keep_text_and_simulated_run_uses_recorded_counts():
    born = birth()
    try:
        accept_vision({"schema": "companion-vision-event-v1", "text": "desk", "model": "moondream", "image": "aaaa"})
    except ValueError as exc:
        assert "raw media" in str(exc)
    else:
        raise AssertionError("raw frame was accepted")
    scene = accept_vision({"schema": "companion-vision-event-v1", "text": "a bright fast bounce", "model": "llava"})
    assert scene["raw_frame_stored"] is False
    book = accept_vision({"schema": "companion-vision-event-v1", "text": "an open book on the desk", "model": "moondream"})
    heard = accept_hearing({
        "schema": "companion-hearing-event-v1",
        "transcript": "",
        "loudness": 0.9,
        "onset": True,
        "engine": "loudness-only",
    })
    assert heard["raw_audio_stored"] is False
    assert heard["on_device"] is True
    fallback = accept_hearing({
        "schema": "companion-hearing-event-v1",
        "transcript": "hello",
        "loudness": 0.1,
        "onset": False,
        "engine": "web-speech-fallback",
    })
    assert fallback["fallback"] is True
    quiet = simulate_live(born["traits"], [])
    bright = simulate_live(born["traits"], [scene])
    reading = simulate_live(born["traits"], [book])
    loud = simulate_live(born["traits"], [heard])
    assert quiet == simulate_live(born["traits"], [])
    assert quiet["label"] == "SIMULATED"
    assert quiet["quantum_hardware"] == "not_contacted"
    assert quiet["pipeline"] == "packets_to_dyn12+mirror_step+StateFamily"
    assert quiet["regge"] == "not_in_repo"
    assert quiet["animation"] == "rest"
    assert bright["animation"] == "orbit"
    assert reading["animation"] == "perch"
    assert loud["animation"] == "orbit"
    assert quiet["dyn12_0"] != bright["dyn12_0"]
    assert quiet["counts_sha256"] == born["card"]["counts_sha256"]


def test_full_command_does_not_download_without_a_gpu(tmp_path: Path):
    status = accelerator_status()
    assert "cuda" in status
    skipped = run_full_qlora(tmp_path / "missing", tmp_path / "train.jsonl", tmp_path)
    assert skipped["status"] in {"SKIPPED_NO_GPU", "SKIPPED_BASE_MISSING", "SKIPPED_DEPENDENCY"}
    assert "Qwen2.5-0.5B-Instruct" in skipped["command"]
