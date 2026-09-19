from pathlib import Path
import importlib.util

WORKFLOW = Path(".github/workflows/zeref-memory-discontinuity.yml")
SCRIPT = Path("scripts/zeref_memory_discontinuity.py")
BASELINE = Path("scripts/zeref_continuity_baseline.py")
MODEL_SHA = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_memory_discontinuity_files_exist() -> None:
    assert SCRIPT.exists()
    assert WORKFLOW.exists()
    assert BASELINE.exists()


def test_only_behavioral_variable_is_turn3_continuity_omission() -> None:
    probe = _load(SCRIPT, "probe")
    baseline = _load(BASELINE, "baseline")
    assert tuple(probe.PROMPTS) == tuple(baseline.PROMPTS)
    assert probe.OMIT_CONTINUITY_TURN == 3
    assert probe.DEFAULT_SEED == 424242


def test_workflow_runs_paired_control_and_perturbation_with_same_seed() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "--omit-turn 0 --seed 424242" in workflow
    assert "--omit-turn 3 --seed 424242" in workflow
    assert "comparison.json" in workflow


def test_workflow_preserves_prime_lineage_and_native_context() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert REVISION in workflow
    assert MODEL_SHA in workflow
    assert "architecture/cosmos-arch.patch" in workflow
    assert "architecture/llama_cpp_cosmos.cpp" in workflow
    assert "cosmos-f16-kv-norm-f32.patch" in workflow
    assert "--chat-template chatml" in workflow
    assert "-c 128" in workflow
    assert "n_ctx_slot = 128" in workflow
    assert "--max-tokens 8" in workflow


def test_workflow_launch_is_append_only_marker_gated() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "run-021-memory-discontinuity-control.txt" in workflow
    assert "persist-credentials: false" in workflow
    assert "Upload memory-discontinuity evidence" in workflow
