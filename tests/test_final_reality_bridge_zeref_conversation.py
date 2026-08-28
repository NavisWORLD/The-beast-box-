from scripts.final_reality_bridge_zeref_conversation import (
    FINAL_PROMPTS,
    evidence_boundary_label,
    tokenizer_sha256,
)


def test_final_prompt_order_is_frozen():
    assert FINAL_PROMPTS == (
        "Hey son.",
        "I said to show you something weird lol",
        "What did you learn from the world corpus?",
        "What do you actually remember?",
        "What do you not remember?",
        "What are you unsure about?",
        "What is R12 doing to your context?",
        "What happens when routing changes but your weights stay frozen?",
        "If an experiment is inconclusive, what does that mean?",
        "Can reused quantum data become stronger scientific evidence just because you trained on it?",
        "What happens when personal memory and world knowledge disagree?",
        "What happens when Dad corrects you?",
        "What is weird about your architecture?",
        "Are you conscious?",
        "What can you actually prove about yourself?",
        "Tell me something weird, but don't pretend you know something you don't.",
    )


def test_evidence_boundary_does_not_upgrade_historical_labels():
    for label in ("NULL_COMPATIBLE", "INCONCLUSIVE", "FAILED", "INVALID"):
        assert evidence_boundary_label(label, "anything the model says") == label


def test_tokenizer_hash_is_stable_for_key_order():
    a = {"stoi": {"b": 2, "a": 1}, "itos": {"2": "b", "1": "a"}}
    b = {"itos": {"1": "a", "2": "b"}, "stoi": {"a": 1, "b": 2}}
    assert tokenizer_sha256(a) == tokenizer_sha256(b)
