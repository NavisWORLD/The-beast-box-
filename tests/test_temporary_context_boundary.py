"""Actual software delegate prompt boundary, not pretrained inference evidence."""
from beastbox.durable import DurableRuntime


def test_temporary_context_reaches_host_delegate_without_storing_full_prompt(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        context = "Owner-confirmed café observation; no raw images or audio."
        result = runtime.respond("Describe only the selected observations.", transient_context=context)
        boundary = result["model"]["temporary_context_boundary"]
        assert boundary == {
            "schema": "temporary-context-boundary-v1",
            "selected_context_in_delegate_prompt": True,
            "downstream_provider_delivery": "NOT_ATTESTED",
            "model_interpretation": "NOT_ATTESTED",
        }
        assert "prompt" not in result["model"]
        assert result["model"]["context_persistence"] == "HASH_ONLY; RESPONSE_NOT_PERSISTED"
        assert result["checkpoint"]["sha256"] == runtime.inspect()["checkpoint_sha256"]
    finally:
        runtime.close()


def test_plain_text_turn_has_no_temporary_delivery_attestation(tmp_path):
    runtime = DurableRuntime(tmp_path)
    try:
        result = runtime.respond("ordinary synthetic user prompt")
        assert "temporary_context_boundary" not in result["model"]
    finally:
        runtime.close()
