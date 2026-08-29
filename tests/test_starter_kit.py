import json
from pathlib import Path

from beastbox.config import RuntimeConfig
from beastbox.cypher.models import ModelSpec, create_model

ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "QUANTUM_BEAST_STARTER"


def test_runtime_example_matches_runtime_config_fields():
    raw = json.loads((STARTER / "config" / "beastbox.example.json").read_text(encoding="utf-8"))
    cfg = RuntimeConfig(**raw)
    assert cfg.local_model_url.startswith("http://127.0.0.1")
    assert cfg.quantum_heart_mode == "off"


def test_model_profiles_parse_and_stay_local():
    for name in ["ollama", "lm-studio", "llama-server", "gguf"]:
        raw = json.loads((STARTER / "models" / f"{name}.example.json").read_text(encoding="utf-8"))
        spec = ModelSpec.from_dict(raw)
        assert spec.alias
        if spec.base_url:
            assert spec.base_url.startswith(("http://127.0.0.1", "http://localhost"))
        if spec.backend != "gguf":
            create_model(spec)


def test_scientific_anchor_is_explicit_and_conservative():
    text = (STARTER / "SCIENTIFIC_ANCHOR.md").read_text(encoding="utf-8")
    assert "c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f" in text
    assert "ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED" in text
    assert "fresh_ibm_jobs_submitted: false" in text
