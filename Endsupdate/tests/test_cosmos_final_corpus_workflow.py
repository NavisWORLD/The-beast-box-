from pathlib import Path


WORKFLOW = Path(".github/workflows/cosmos-final-corpus.yml")
ISOLATED_BRANCH = "cory-davis-cosmos-reality-bridge-final-organism-001"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_restores_pinned_historical_source_instead_of_live_ingestion() -> None:
    text = _workflow_text()

    assert "33132925890" in text
    assert "zeref-world-r12-downstream-diagnostic-v2-33132925890" in text
    assert "cdbc84db988668894a476d51ee42faa591cace77631da7c7daa82831bb1201de" in text
    assert "9e2e6cf0965691db9a4ecd3affe9ccb8b33195f6cf7f2341ace1e1f43e549d3b" in text
    assert "scripts/build_zeref_world_knowledge.py" not in text
    assert "datasets>=" not in text


def test_workflow_runs_two_freezes_and_preserves_authenticated_source_outputs() -> None:
    text = _workflow_text()

    assert text.count("scripts/final_reality_bridge_corpus.py") >= 2
    assert "--world-summary" in text
    assert "--source-output-dir" in text
    assert "diff -qr" in text
    assert "canonical-world.jsonl" in text
    assert "canonical-record-hashes.txt" in text


def test_workflow_can_only_commit_back_to_the_isolated_organism_branch() -> None:
    text = _workflow_text()

    assert ISOLATED_BRANCH in text
    push_block = text.split("Commit verified corpus evidence", 1)[1]
    assert "GITHUB_REF_NAME" in push_block
    assert "cosmos-reality-bridge-final-001" not in push_block
