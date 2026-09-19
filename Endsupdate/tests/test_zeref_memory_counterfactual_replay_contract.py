from pathlib import Path

WORKFLOW = Path('.github/workflows/zeref-memory-counterfactual-replay.yml')
MODEL_SHA = 'b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6'
REVISION = 'b414724c627300c41b099dcc6853766d08fd27a4'


def test_run023_workflow_exists() -> None:
    assert WORKFLOW.exists()


def test_run023_changes_only_replay_fragment_identity() -> None:
    workflow = WORKFLOW.read_text(encoding='utf-8')
    assert '--omit-turn 0 --seed 424242' in workflow
    assert '--omit-turn 3 --seed 424242' in workflow
    assert '--replay-turn 4' in workflow
    assert 'control_turn3_fragment.txt' in workflow
    assert 'counterfactual_turn2_fragment.txt' in workflow
    assert 'counterfactual_replay_specificity.json' in workflow
    assert '--max-tokens 8' in workflow


def test_run023_preserves_exact_lineage_context_and_loopback_surface() -> None:
    workflow = WORKFLOW.read_text(encoding='utf-8')
    assert REVISION in workflow
    assert MODEL_SHA in workflow
    assert 'architecture/cosmos-arch.patch' in workflow
    assert 'architecture/llama_cpp_cosmos.cpp' in workflow
    assert 'cosmos-f16-kv-norm-f32.patch' in workflow
    assert '--chat-template chatml' in workflow
    assert '--host 127.0.0.1' in workflow
    assert '-c 128' in workflow
    assert 'n_ctx_slot = 128' in workflow


def test_run023_is_append_only_marker_gated() -> None:
    workflow = WORKFLOW.read_text(encoding='utf-8')
    assert 'run-023-memory-counterfactual-replay.txt' in workflow
    assert 'persist-credentials: false' in workflow
    assert 'Upload counterfactual-replay evidence' in workflow
