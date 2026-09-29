"""Real durable-dialogue assembly tests; no downloaded model or synthetic weight claim."""
from beastbox.durable import DurableRuntime
from beastbox.memory import ReconciliationMemory


class CapturingProvider:
    def __init__(self, model="test-provider"):
        self.model = model
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return "I heard you." if len(self.prompts) > 1 else "That name is remembered."


def test_recent_dialogue_survives_restart_and_model_change(tmp_path):
    first = CapturingProvider()
    original = DurableRuntime(tmp_path, provider=first)
    try:
        original.respond("My new project is called Moon Garden")
        system_id = original.inspect()["system_id"]
    finally:
        original.close()
    swapped = CapturingProvider(model="alternate-provider")
    restored = DurableRuntime(tmp_path, provider=swapped)
    try:
        answer = restored.respond("What should we work on next?")
        prompt = swapped.prompts[0]
        assert "RECENT RETAINED DIALOGUE" in prompt
        assert "User: My new project is called Moon Garden" in prompt
        assert "Assistant: That name is remembered." in prompt
        assert restored.inspect()["system_id"] == system_id
        assert answer["checkpoint"]["sha256"]
    finally:
        restored.close()


def test_private_transient_attachments_never_replayed_as_chat(tmp_path):
    provider = CapturingProvider()
    runtime = DurableRuntime(tmp_path, provider=provider)
    try:
        runtime.respond("Please inspect this attachment", transient_context="ONLY_PRIVATE_ATTACHMENT_123")
        runtime.respond("What do you remember?")
        assert "ONLY_PRIVATE_ATTACHMENT_123" not in provider.prompts[1]
        assert "User: Please inspect this attachment" in provider.prompts[1]
        assert "Assistant: That name is remembered." not in provider.prompts[1]
    finally:
        runtime.close()


def test_native_prompt_is_short_and_uses_shared_ledger(tmp_path):
    provider = CapturingProvider(model="rawrphos-native")
    runtime = DurableRuntime(tmp_path, provider=provider)
    try:
        runtime.respond("Remember Moon Garden")
        runtime.respond("hello")
        prompt = provider.prompts[1]
        assert "RAWRPHØS" in prompt
        assert "Recent dialogue (quoted)" in prompt
        assert "Remember Moon Garden" in prompt
        assert "User: hello" in prompt
        assert "QUANTUM HEART MODE" not in prompt
        assert len(prompt) < 800
    finally:
        runtime.close()


def test_many_nonchat_observations_do_not_evict_recent_dialogue(tmp_path):
    memory = ReconciliationMemory(tmp_path / "dialogue.sqlite3")
    try:
        memory.store("We are building the Moon Garden", kind="user_turn")
        memory.store("Yes, the Moon Garden", kind="assistant_turn")
        for i in range(50):
            memory.store("unverified sensor reading " + str(i), kind="device_observation")
        recent = memory.recent_dialogue(limit=8)
        assert [row.kind for row in recent] == ["assistant_turn", "user_turn"]
        assert "Moon Garden" in recent[0].text
    finally:
        memory.close()
