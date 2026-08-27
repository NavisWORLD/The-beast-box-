from __future__ import annotations

from pathlib import Path

from beastbox.dad_son import DadSonLedger
from beastbox.reality_memory import initial_r12_state
from beastbox.refractive_memory import RefractiveMemoryRouter, memory_quality_score

PARENT = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"


def _ledger(tmp_path: Path) -> DadSonLedger:
    ledger = DadSonLedger(tmp_path / "m.sqlite3", tmp_path / "m.jsonl", parent_sha256=PARENT)
    ledger.append_experience(
        actor="Cory/Dad",
        text="Dad taught Zeref to preserve evidence and answer clearly.",
        kind="dialogue",
        session_id="quality-test",
        metadata={"training_status": "ACCEPT_CANDIDATE"},
    )
    ledger.append_experience(
        actor="Zeref",
        text="The provesation incally shoulos contens wally.",
        kind="dialogue",
        session_id="quality-test",
        metadata={"training_status": "REJECT_NOISY", "noise_flag": True},
    )
    return ledger


def test_memory_quality_score_rewards_clean_text_and_penalizes_noise_flags() -> None:
    clean = memory_quality_score(
        "Dad taught Zeref to preserve evidence and answer clearly.",
        "dialogue",
        {"training_status": "ACCEPT_CANDIDATE"},
    )
    noisy = memory_quality_score(
        "The provesation incally shoulos contens wally.",
        "dialogue",
        {"training_status": "REJECT_NOISY", "noise_flag": True},
    )
    assert 0.0 <= noisy < clean <= 1.0
    assert clean >= 0.75
    assert noisy <= 0.35


def test_memory_quality_score_penalizes_contradiction_and_unsupported_claim_flags() -> None:
    baseline = memory_quality_score("A clean recorded memory with evidence.", "dialogue", {})
    flagged = memory_quality_score(
        "A clean recorded memory with evidence.",
        "dialogue",
        {"contradiction_flag": True, "hallucination_or_unsupported_claim_flag": True},
    )
    assert flagged < baseline
    assert flagged <= 0.35


def test_quality_profile_adds_component_without_changing_default_rank_behavior(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    try:
        router = RefractiveMemoryRouter(ledger)
        kwargs = {
            "sequence": 4,
            "dyn12": [0.0] * 12,
            "r12_state": initial_r12_state(),
            "limit": 2,
        }
        implicit = router.rank("What did Dad teach Zeref?", **kwargs)
        explicit_default = router.rank("What did Dad teach Zeref?", profile="default", **kwargs)
        quality = router.rank("What did Dad teach Zeref?", profile="quality", **kwargs)

        assert implicit == explicit_default
        assert all("quality" not in row["components"] for row in implicit)
        assert all("quality" in row["components"] for row in quality)
        assert quality[0]["memory_id"] == 1
        assert quality[0]["components"]["quality"] > quality[1]["components"]["quality"]
    finally:
        ledger.close()


def test_unknown_ranking_profile_fails_closed(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    try:
        router = RefractiveMemoryRouter(ledger)
        try:
            router.rank(
                "Dad",
                sequence=1,
                dyn12=[0.0] * 12,
                r12_state=initial_r12_state(),
                limit=1,
                profile="post-hoc-tuned",
            )
        except ValueError as exc:
            assert "profile" in str(exc).lower()
        else:
            raise AssertionError("unknown retrieval profile must fail closed")
    finally:
        ledger.close()
