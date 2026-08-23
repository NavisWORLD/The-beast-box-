from __future__ import annotations

import json
from pathlib import Path

from beastbox.cypher.easy_ollama import (
    DEFAULT_BASE_MODEL,
    build_parser,
    choose_startup_spec,
    ensure_plain_ollama_model,
    ensure_zeref_profile,
    load_zeref_runtime_config,
    make_zeref_modelfile,
    switch_runtime_backend,
)
from beastbox.cypher.models import ModelSpec
from beastbox.cypher.registry import ModelRegistry


def test_default_zeref_base_is_published_qc67_model():
    assert DEFAULT_BASE_MODEL == "hf.co/phera-ra/QC67_cosmo"
    assert "FROM hf.co/phera-ra/QC67_cosmo" in make_zeref_modelfile()


def test_registry_persists_active_model(tmp_path: Path):
    path = tmp_path / "models.json"
    reg = ModelRegistry(path)
    reg.register(ModelSpec(alias="small", backend="ollama", model="qwen2.5:1.5b"))
    reg.register(ModelSpec(alias="large", backend="ollama", model="qwen2.5:7b"))
    reg.set_active("small")

    reloaded = ModelRegistry(path)
    assert reloaded.active_alias() == "small"
    assert reloaded.active().model == "qwen2.5:1.5b"

    reloaded.set_active("large")
    assert ModelRegistry(path).active_alias() == "large"
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["version"] == 2


def test_removing_active_model_clears_pointer(tmp_path: Path):
    reg = ModelRegistry(tmp_path / "models.json")
    reg.register(ModelSpec(alias="a", backend="ollama", model="alpha"))
    reg.set_active("a")
    assert reg.remove("a") is True
    assert reg.active() is None


def test_zeref_modelfile_is_transparent_about_growth():
    text = make_zeref_modelfile("qwen2.5:1.5b")
    assert "FROM qwen2.5:1.5b" in text
    assert "PARAMETER num_ctx 8192" in text
    assert "weights are retrained by ordinary chat" in text
    assert "COSMOS memory/state layer" in text


def test_ensure_zeref_profile_pulls_base_builds_profile_and_activates(tmp_path: Path):
    reg = ModelRegistry(tmp_path / "models.json")
    installed: list[str] = []
    pulled: list[str] = []
    created: list[tuple[str, str]] = []

    def list_models(_url: str):
        return list(installed)

    def pull(model: str):
        pulled.append(model)
        installed.append(model)

    def create(name: str, modelfile: str):
        created.append((name, modelfile))
        installed.append(name)

    spec = ensure_zeref_profile(
        reg,
        base_model="qwen2.5:1.5b",
        list_models=list_models,
        pull=pull,
        create_profile=create,
    )

    assert pulled == ["qwen2.5:1.5b"]
    assert created and created[0][0] == "zeref"
    assert spec.model == "zeref"
    assert reg.active_alias() == "zeref"


def test_plain_model_switch_auto_registers_and_activates(tmp_path: Path):
    reg = ModelRegistry(tmp_path / "models.json")
    installed = ["llama3.2:3b"]
    spec = ensure_plain_ollama_model(
        reg,
        "llama3.2:3b",
        list_models=lambda _url: installed,
        pull=lambda _model: (_ for _ in ()).throw(AssertionError("should not pull")),
    )
    assert spec.model == "llama3.2:3b"
    assert reg.active_alias() == spec.alias


def test_switch_runtime_backend_preserves_runtime_memory_object():
    memory = object()

    class Runtime:
        def __init__(self):
            self.memory = memory
            self.provider = object()

    class FakeModel:
        def complete(self, prompt: str) -> str:
            return prompt

        def chat(self, messages):
            return "ok"

    runtime = Runtime()
    spec = ModelSpec(alias="next", backend="ollama", model="next")
    switch_runtime_backend(runtime, spec, factory=lambda _spec: FakeModel())

    assert runtime.memory is memory
    assert runtime.provider.backend.complete("hello") == "hello"


def test_parser_supports_easy_model_selection_and_setup_only():
    args = build_parser().parse_args(
        ["--model", "qwen2.5-coder:3b", "--base-model", "qwen2.5:1.5b", "--setup-only"]
    )
    assert args.model == "qwen2.5-coder:3b"
    assert args.base_model == "qwen2.5:1.5b"
    assert args.setup_only is True


def test_choose_startup_spec_reuses_active_alias(tmp_path: Path):
    reg = ModelRegistry(tmp_path / "models.json")
    spec = ModelSpec(alias="daily", backend="ollama", model="llama3.2:3b")
    reg.register(spec)
    reg.set_active("daily")
    chosen = choose_startup_spec(reg)
    assert chosen.alias == "daily"


def test_choose_startup_spec_uses_registered_requested_alias(tmp_path: Path):
    reg = ModelRegistry(tmp_path / "models.json")
    a = ModelSpec(alias="a", backend="ollama", model="alpha")
    b = ModelSpec(alias="b", backend="ollama", model="beta")
    reg.register(a)
    reg.register(b)
    reg.set_active("a")

    chosen = choose_startup_spec(reg, requested="b")
    assert chosen.model == "beta"
    assert reg.active_alias() == "b"


def test_existing_zeref_profile_does_not_redownload_base(tmp_path: Path):
    reg = ModelRegistry(tmp_path / "models.json")
    spec = ensure_zeref_profile(
        reg,
        base_model="qwen2.5:1.5b",
        list_models=lambda _url: ["zeref"],
        pull=lambda _model: (_ for _ in ()).throw(AssertionError("should not pull")),
        create_profile=lambda _name, _text: (_ for _ in ()).throw(AssertionError("should not rebuild")),
    )
    assert spec.model == "zeref"
    assert reg.active_alias() == "zeref"


def test_default_runtime_config_uses_stable_absolute_memory_path(tmp_path: Path):
    cfg_path = tmp_path / "user-home" / "beastbox.json"
    cfg = load_zeref_runtime_config(cfg_path)
    assert Path(cfg.memory_db).is_absolute()
    assert Path(cfg.memory_db).parent == cfg_path.parent.resolve()
    assert cfg.local_model_name == "zeref"
    assert cfg_path.exists()


def test_missing_active_zeref_profile_is_repaired(monkeypatch, tmp_path: Path):
    import beastbox.cypher.easy_ollama as easy

    reg = ModelRegistry(tmp_path / "models.json")
    reg.register(ModelSpec(alias="zeref", backend="ollama", model="zeref"))
    reg.set_active("zeref")
    replacement = ModelSpec(alias="zeref", backend="ollama", model="zeref")
    called = []

    def fake_ensure(registry, **kwargs):
        called.append(kwargs)
        registry.register(replacement, overwrite=True)
        registry.set_active("zeref")
        return replacement

    monkeypatch.setattr(easy, "ensure_zeref_profile", fake_ensure)
    chosen = easy.choose_startup_spec(reg, installed_models=set())
    assert chosen.model == "zeref"
    assert called and called[0]["rebuild"] is True
