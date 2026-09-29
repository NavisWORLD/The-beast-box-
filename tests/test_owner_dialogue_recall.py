"""Owner-only bounded recent dialogue: restart, archive and transient privacy."""
from __future__ import annotations

import json

import pytest

from beastbox.durable import DurableRuntime
from beastbox.providers import ReferenceTextProvider
from beastbox.retrieval_snapshot import recent_dialogue_from_snapshot


def test_recent_dialogue_uses_active_snapshot_and_chronological_order(tmp_path):
    r = DurableRuntime(tmp_path, ReferenceTextProvider(), recent_dialogue_limit=4)
    try:
        one = r.respond("The nebula-code phrase is cobalt goose.")
        second = r.respond("Can you still see the earlier message?")
        assert "RECENT OWNER CONVERSATION" in second["model"]["prompt"]
        block = second["model"]["prompt"].split("RECENT OWNER CONVERSATION", 1)[1]
        assert "USER: The nebula-code phrase is cobalt goose." in block
        assert block.index("USER: The nebula-code phrase") < block.index("ASSISTANT: ")
        assert r.inspect()["sequence"] >= 2
        first_id = r.memory.db.execute(
            "SELECT id FROM memories WHERE kind='user_turn' ORDER BY id LIMIT 1"
        ).fetchone()[0]
        r.archive_memory(int(first_id), reviewer="owner", reason="Test no archived recall")
        # Remove other retained dialogue, so no historical assistant quote can
        # inadvertently reproduce the archived phrase.
        other = r.memory.db.execute(
            "SELECT id FROM memories WHERE kind='assistant_turn' ORDER BY id LIMIT 1"
        ).fetchone()[0]
        r.archive_memory(int(other), reviewer="owner", reason="Test no archived recall")
        snapshot = __import__("beastbox.retrieval_snapshot", fromlist=["capture_snapshot"]).capture_snapshot(r.memory)
        recent, ids = recent_dialogue_from_snapshot(snapshot, limit=4)
        assert int(first_id) not in ids
        assert int(other) not in ids
        assert "USER: The nebula-code phrase" not in recent
    finally:
        r.close()


def test_owner_chat_replays_after_restart_and_swaps_without_retraining(tmp_path):
    r = DurableRuntime(tmp_path, ReferenceTextProvider(prefix="A"), recent_dialogue_limit=4)
    first = r.respond("Remember my invented word: violet-orbit-427.")
    checkpoint = r.inspect()["checkpoint_sha256"]
    system_id = r.system_id
    r.close()
    restarted = DurableRuntime(tmp_path, ReferenceTextProvider(prefix="B"), recent_dialogue_limit=4)
    try:
        assert restarted.inspect()["checkpoint_sha256"] == checkpoint
        assert restarted.system_id == system_id
        second = restarted.respond("Hello again, what were we talking about?")
        assert "USER: Remember my invented word: violet-orbit-427." in second["model"]["prompt"]
        assert second["routing"]["recent_dialogue_ids"]
        assert "recent_dialogue_sha256" in second["routing"]
    finally:
        restarted.close()


def test_unselected_context_is_not_retained_as_assistant_memory(tmp_path):
    r = DurableRuntime(tmp_path, ReferenceTextProvider(), recent_dialogue_limit=4)
    try:
        turn = r.respond("Please analyze my attached notes.", transient_context="VERY_PRIVATE_ATTACHMENT_CANARY")
        assert "VERY_PRIVATE_ATTACHMENT_CANARY" in turn["model"]["prompt"]
        assert r.memory.db.execute(
            "SELECT COUNT(*) FROM memories WHERE kind='assistant_turn'"
        ).fetchone()[0] == 0
        followup = r.respond("Let's continue.")
        assert "VERY_PRIVATE_ATTACHMENT_CANARY" not in followup["model"]["prompt"]
        assert "USER: Please analyze my attached notes." in followup["model"]["prompt"]
    finally:
        r.close()


@pytest.mark.parametrize("limit", [-1, 7, True, 1.5])
def test_recent_dialogue_rejects_invalid_limit(tmp_path, limit):
    with pytest.raises(ValueError, match="recent dialogue limit"):
        DurableRuntime(tmp_path, ReferenceTextProvider(), recent_dialogue_limit=limit)


def test_default_historical_prompt_unchanged(tmp_path):
    r = DurableRuntime(tmp_path, ReferenceTextProvider())
    try:
        r.respond("older user turn")
        second = r.respond("another turn")
        assert "RECENT OWNER CONVERSATION" not in second["model"]["prompt"]
        assert "recent_dialogue_ids" not in second["routing"]
    finally:
        r.close()
