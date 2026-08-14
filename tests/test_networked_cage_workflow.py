from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "networked-cage.yml"


def test_live_workflow_uses_current_shipped_spark_subject() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "serving/spark_serve.py" in text
    assert "weights/cosmos_born.pt" in text
    assert "cosmos-spark:latest" in text
    assert "--backend ollama" in text
    assert 'SUBJECT_PORT: "11500"' in text
    assert 'http://127.0.0.1:${SUBJECT_PORT}' in text
    assert "bfb49099ef6be5584175ca9ef5ffe0e5509b5fc9be3a2c9ff3cbef2f16153906" in text


def test_live_workflow_does_not_silently_substitute_removed_or_base_models() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "cosmos-namebind-weights.gguf" not in text
    assert "Qwen/Qwen" not in text
    assert "llama-server" not in text
    assert "LLAMA_CPP_COMMIT" not in text


def test_publisher_credentials_exist_only_after_subject_shutdown_step() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    stop = text.index("Stop subject model server before publisher credentials exist")
    token = text.index("GITHUB_TOKEN: ${{ github.token }}")
    assert stop < token


def test_live_workflow_freezes_model_revision_checkpoint_and_server_hashes() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "hf_revision" in text
    assert "checkpoint_sha256" in text
    assert "server_sha256" in text
    assert "model_info" in text
    assert "files_metadata=True" in text
