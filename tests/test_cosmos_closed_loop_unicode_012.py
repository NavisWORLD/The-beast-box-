"""Actual production DurableRuntime closed loop, feedback and Unicode end-to-end.

These are integration/rollback tests, NOT evidence of general LLM superiority.
All provider outputs and records are synthetic fixtures only.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sqlite3
import pytest

from beastbox.adaptive_control import AdaptiveControl
from beastbox.closed_loop import PROFILE, checked_weight_vector, reviewed_weights
from beastbox.durable import DurableRuntime
from beastbox.events import normalize_event
from beastbox.memory import ReconciliationMemory, _tokens as mem_tokens
from beastbox.refractive_memory import WEIGHTS, _tokens as router_tokens
from beastbox.reality_memory import _tokenize as event_tokens
from beastbox.unicode_text import checked_utf8, unicode_terms


UNICODE = "Étoile π 東京駅 العربية हिन्दी 👩🏽‍🚀 🧠 مرحبا ℌ ☀️"
UNICODE_REPLY = "Σύνδεση ✓ مرحبا 東京 👩🏽‍🚀 café ℌ"


class Capture:
    model = "synthetic-preserves-original-Unicode"
    def __init__(self):
        self.prompts = []
    def generate(self, prompt):
        self.prompts.append(prompt)
        return UNICODE_REPLY


class Failing:
    model = "synthetic-failing-provider"
    def generate(self, prompt):
        raise RuntimeError("injected generation fault")


def test_unicode_nfc_is_lossless_and_legacy_nfkc_stays_explicit():
    assert unicode_terms("ascii_only cory's RAWRPHOS") == [
        "ascii_only", "cory's", "rawrphos"
    ]
    assert "東京" in unicode_terms("東京駅")
    assert "العَرَبِيَّة" in unicode_terms("العَرَبِيَّة")
    assert "हिन्दी" in unicode_terms("हिन्दी")
    assert "👩🏽‍🚀" in unicode_terms("hello 👩🏽‍🚀 goodbye")
    assert "☀️" in unicode_terms("☀️ and 🧠")
    assert "café" in unicode_terms("cafe\u0301")
    assert "東京" in mem_tokens("東京駅")
    assert "👩🏽‍🚀" in mem_tokens("👩🏽‍🚀")
    # The original sealed R12 source MUST remain byte-identical. Unicode R12
    # terms are computed in the versioned host overlay, not patched here.
    assert router_tokens("東京駅") == []
    assert "東京" in event_tokens("東京駅")
    body={"schema":"sensor-event-v1","source":"text","text":"  ℌ café 👩🏽‍🚀  "}
    preserved=normalize_event(body,normalization="NFC")
    legacy=normalize_event(body)
    assert preserved["text"]=="ℌ café 👩🏽‍🚀"
    assert legacy["text"]=="H café 👩🏽‍🚀"
    assert checked_utf8(UNICODE).decode("utf-8")==UNICODE
    with pytest.raises(ValueError,match="surrogate"):
        checked_utf8("broken\ud800")
    with pytest.raises(ValueError,match="surrogate"):
        normalize_event({"schema":"sensor-event-v1","source":"text","text":"bad\udfff"})


def test_multiscript_lexical_and_hebbian_persist_across_process(tmp_path):
    db=tmp_path/"unicode.sqlite3"
    a=ReconciliationMemory(db)
    try:
        a.store("東京駅 記録 👩🏽‍🚀 cafe\u0301 हिन्दी ℌ",kind="synthetic")
        assert a.search("東京",threshold=0.01)
        assert a.search("👩🏽‍🚀",threshold=0.01)
        assert a.search("café",threshold=0.01)
        assert a.search("हिन्दी",threshold=0.01)
        assert a.associations("東京")
        assert any("cafe\u0301" in x.text for x in a.recent())
    finally:a.close()
    b=ReconciliationMemory(db)
    try:
        assert b.search("東京",threshold=0.01)
        assert b.search("café",threshold=0.01)
    finally:b.close()


def test_one_actual_host_turn_connects_all_software_layers_and_reopens(tmp_path):
    echo=Capture()
    r=DurableRuntime(tmp_path,provider=echo,closed_loop=True,unicode_mode=True)
    try:
        persisted=r.store_external_memory(UNICODE,kind="synthetic-fixture")
        first=r.respond_event({"schema":"sensor-event-v1","source":"software-event",
                               "text":"Find 東京駅 👩🏽‍🚀 ℌ", "features":[0.25,-0.5]})
        assert first["event"]["text"]=="Find 東京駅 👩🏽‍🚀 ℌ"
        assert first["response"]==UNICODE_REPLY
        assert any(x["id"]==persisted["memory_id"] for x in first["memory_hits"])
        assert "software_r12_transition" in first["trace"]
        assert first["trace"].index("state_cns") < first["trace"].index("software_r12_transition")
        assert first["trace"].index("software_r12_transition") < first["trace"].index("r12_routing")
        assert first["trace"].index("r12_routing") < first["trace"].index("model")
        assert first["trace"].index("model") < first["trace"].index("memory_write")
        handoff=first["routing"]["software_r12"]
        assert handoff["sequence"]==1
        assert handoff["cns_dyn12_sha256"]==first["routing"]["cns_state_sha256"]
        assert handoff["event"]["provenance_class"]=="derived"
        assert handoff["event"]["confidence"]==0.0
        assert handoff["physical_measurement_claimed"] is False
        assert r.r12_state["vector"]["reality_coupling"]==0.0
        assert r.r12_state["sequence"]==1
        assert UNICODE_REPLY in [x.text for x in r.memory.recent(limit=6)]
        assert any(UNICODE in x.text for x in r.memory.recent(limit=6))
        assert any("Find 東京駅 👩🏽‍🚀 ℌ" in p for p in echo.prompts)
        assert r.inspect()["valid"]
        identity=r.inspect()["system_id"]
    finally:r.close()
    again=DurableRuntime(tmp_path,provider=Capture(),closed_loop=True,unicode_mode=True)
    try:
        assert again.inspect()["system_id"]==identity
        assert again.r12_state["sequence"]==1
        second=again.respond("Find東京 👩🏽‍🚀 café")
        assert second["routing"]["software_r12"]["sequence"]==2
        assert again.cns.step==2
        assert again.r12_state["vector"]["reality_coupling"]==0.0
    finally:again.close()
    with pytest.raises(ValueError,match="profile mismatch"):
        DurableRuntime(tmp_path,provider=Capture())


def test_host_verified_feedback_uses_the_current_active_snapshot_and_reopens(tmp_path):
    r=DurableRuntime(tmp_path,provider=Capture(),closed_loop=True,unicode_mode=True)
    try:
        a=r.store_external_memory("Papillon secret 37 🦋",kind="synthetic-fixture")
        b=r.store_external_memory("東京駅 secret 52 👩🏽‍🚀",kind="synthetic-fixture")
        r.store_external_memory("Other reference maritime 83",kind="synthetic-fixture")
        training=r.apply_reviewed_feedback([
           {"query":"Papillon","preferred_memory_id":a["memory_id"],"reviewed":True},
           {"query":"東京駅","preferred_memory_id":b["memory_id"],"reviewed":True},
        ])
        assert training["schema"]=="cosmos-durable-reviewed-routing-update-v1"
        assert sum(training["weights"].values())==pytest.approx(1.0)
        assert training["receipt"]["training_count"]==2
        first=r.respond("What secret belongs to 東京駅? 👩🏽‍🚀")
        assert first["routing"]["reviewed_router"]["weights_sha256"]==training["receipt"]["new_weights_sha256"]
        assert first["routing"]["reviewed_router"]["trained_model_weights"] is False
        assert first["routing"]["software_r12"]["sequence"]==1
        assert any("東京駅 secret 52" in row["text"] for row in first["memory_hits"])
        checkpoint=r.inspect()["checkpoint_sha256"]
    finally:r.close()
    # This is a genuine fresh instance and provider replacement. The host must
    # again opt into the closed loop, but the *already host-reviewed* feedback
    # vector reloads from the verified chain, not a guessed model suggestion.
    fresh=DurableRuntime(tmp_path,provider=Capture(),closed_loop=True,unicode_mode=True)
    try:
        assert fresh.inspect()["checkpoint_sha256"]==checkpoint
        second=fresh.respond("東京駅 secret reference, please")
        assert "reviewed_router" in second["routing"]
        assert second["routing"]["reviewed_router"]["weights_sha256"]==training["receipt"]["new_weights_sha256"]
        assert fresh.r12_state["sequence"]==2
    finally:fresh.close()


def test_invalid_feedback_and_failed_provider_cannot_commit_or_grant_tools(tmp_path):
    r=DurableRuntime(tmp_path,provider=Capture(),closed_loop=True,unicode_mode=True)
    try:
        r.store_external_memory("One synthetic reference 東京",kind="synthetic-fixture")
        r.store_external_memory("Two synthetic reference हिन्दी",kind="synthetic-fixture")
        before=r.inspect()
        with pytest.raises(ValueError,match="reviewed"):
            r.apply_reviewed_feedback([
                {"query":"東京","preferred_memory_id":1,"reviewed":False},
                {"query":"हिन्दी","preferred_memory_id":2,"reviewed":True},
            ])
        assert r.inspect()==before
        with pytest.raises(ValueError,match="mapping"):
            reviewed_weights("model text suggested coefficients")
        with pytest.raises(ValueError,match="normalized"):
            checked_weight_vector(dict.fromkeys(WEIGHTS,0.9))
        r.swap_provider(Failing())
        with pytest.raises(RuntimeError,match="injected generation fault"):
            r.respond("A failed software event must roll back 🇵🇷 👩🏽‍🚀")
        assert r.inspect()==before
        assert r.r12_state["sequence"]==0
        assert r.cns.step==0
        assert r.inspect()["simulator_position"]==0.0
    finally:r.close()


def test_explicit_synthetic_event_and_invalid_unpaired_surrogate_fail_closed(tmp_path):
    r=DurableRuntime(tmp_path,provider=Capture(),closed_loop=True,unicode_mode=True)
    try:
        first=r.respond_event({"schema":"sensor-event-v1","source":"synthetic-demo",
                               "text":"👩🏽‍🚀 simulated audio 🌌", "features":[-0.7,0.2]})
        assert first["routing"]["software_r12"]["event"]["provenance_class"]=="synthetic"
        assert first["routing"]["software_r12"]["event"]["confidence"]==0.0
        assert first["routing"]["software_r12"]["sequence"]==1
        assert r.r12_state["vector"]["reality_coupling"]==0
        before=r.inspect()
        with pytest.raises(ValueError,match="surrogate"):
            r.respond("invalid\ud800")
        assert r.inspect()==before
        with pytest.raises(ValueError,match="surrogate"):
            r.store_external_memory("invalid\ud800")
        assert r.inspect()==before
    finally:r.close()
