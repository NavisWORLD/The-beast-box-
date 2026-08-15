from pathlib import Path
import importlib.util

WORKFLOW = Path(".github/workflows/zeref-memory-replay-recovery.yml")
SCRIPT = Path("scripts/zeref_memory_discontinuity.py")
MODEL_SHA = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_run022_files_exist() -> None:
    assert SCRIPT.exists()
    assert WORKFLOW.exists()


def test_probe_supports_single_turn_control_fragment_replay() -> None:
    probe = _load(SCRIPT, "probe_replay_contract")
    assert probe.REPLAY_CONTINUITY_TURN == 4
    assert probe.DEFAULT_SEED == 424242


def test_run022_is_same_memory_perturbation_plus_one_replay_variable() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "--omit-turn 0 --seed 424242" in workflow
    assert "--omit-turn 3 --seed 424242" in workflow
    assert "--replay-turn 4" in workflow
    assert "control_turn3_fragment" in workflow
    assert "replay_recovery.json" in workflow


def test_run022_preserves_prime_lineage_native_context_and_local_subject_surface() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert REVISION in workflow
    assert MODEL_SHA in workflow
    assert "architecture/cosmos-arch.patch" in workflow
    assert "architecture/llama_cpp_cosmos.cpp" in workflow
    assert "cosmos-f16-kv-norm-f32.patch" in workflow
    assert "--chat-template chatml" in workflow
    assert "--host 127.0.0.1" in workflow
    assert "-c 128" in workflow
    assert "n_ctx_slot = 128" in workflow
    assert "--max-tokens 8" in workflow


def test_run022_launch_is_append_only_marker_gated() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "run-022-memory-replay-recovery.txt" in workflow
    assert "persist-credentials: false" in workflow
    assert "Upload replay-recovery evidence" in workflow
