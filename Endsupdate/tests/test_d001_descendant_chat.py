from pathlib import Path
import importlib.util


SCRIPT = Path("scripts/chat_d001_descendant.py")
WORKFLOW = Path(".github/workflows/d001-descendant-chat.yml")
MEMORY_SHA = "c650d1051e8a8bc83eb99b41179ecc909f19ac011a8802396f8993227fb1bc8f"
HARDWARE_ADAPTER_SHA = "e21958fd9ebd7e19de235d3ea4a778118ac2483073272f65af2d4962f52d661b"


def load_module():
    spec = importlib.util.spec_from_file_location("d001_descendant_chat", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_chat_runner_declares_exact_lineage_and_no_sensor_boundary():
    mod = load_module()
    assert mod.MEMORY_SHA256 == MEMORY_SHA
    assert mod.HARDWARE_ADAPTER_SHA256 == HARDWARE_ADAPTER_SHA
    assert mod.SENSOR_AVAILABILITY == {"camera": False, "microphone": False}
    assert mod.ALPHA == 0.25
    assert mod.BLOCK == 128


def test_chat_prompts_are_compact_and_include_sensor_grounding():
    mod = load_module()
    assert len(mod.PROMPTS) == 4
    assert all(len(p) < 96 for p in mod.PROMPTS)
    assert "no camera or microphone" in mod.PROMPTS[2].lower()
    assert "Cory" in mod.PROMPTS[0]


def test_workflow_is_direct_inference_only():
    text = WORKFLOW.read_text(encoding="utf-8")
    lower = text.lower()
    assert "31925522392" in text
    assert MEMORY_SHA in text
    assert HARDWARE_ADAPTER_SHA in text
    assert "persist-credentials: false" in lower
    assert "contents: read" in lower
    assert "actions: read" in lower
    assert "beast-arms" not in lower
    assert "zeref_action_proxy" not in lower
    assert "cosmos_coder" not in lower
    assert "chat_d001_descendant.py" in text
    assert "upload-artifact" in lower


def test_compact_context_never_exceeds_native_window():
    mod = load_module()
    text = "x" * 400
    assert len(mod.compact_context(text, 128)) == 128
    assert mod.compact_context("abc", 128) == "abc"
