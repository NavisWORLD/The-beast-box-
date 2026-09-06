from __future__ import annotations

from pathlib import Path

import pytest

from beastbox.persistent_substrate.prompts import (
    REQUIRED_FAMILIES,
    load_frozen_prompt_battery,
)


FIXTURE = Path(__file__).parent / "fixtures/persistent-substrate/prompts-v1.json"
COMPACT_FIXTURE = Path(__file__).parent / "fixtures/persistent-substrate/prompts-v2.json"


def test_prompt_battery_has_every_preregistered_family_and_stable_hash() -> None:
    battery = load_frozen_prompt_battery(FIXTURE)
    assert {case.family for case in battery.cases} == set(REQUIRED_FAMILIES)
    assert len(battery.sha256) == 64
    assert battery.battery_id == "persistent-substrate-prompts-v1"


def test_compact_preinference_battery_preserves_all_six_families() -> None:
    battery = load_frozen_prompt_battery(COMPACT_FIXTURE)
    assert {case.family for case in battery.cases} == set(REQUIRED_FAMILIES)
    assert len(battery.cases) == 6
    assert battery.battery_id == "persistent-substrate-prompts-v2"
    assert all(case.surface_policy == "identical-across-models" for case in battery.cases)


def test_memory_cases_bind_only_to_explicit_canonical_record_ids() -> None:
    for fixture in (FIXTURE, COMPACT_FIXTURE):
        battery = load_frozen_prompt_battery(fixture)
        memory_cases = [case for case in battery.cases if case.canonical_record_ids]
        assert memory_cases
        assert {record_id for case in memory_cases for record_id in case.canonical_record_ids} <= {17, 311}
        assert any(17 in case.canonical_record_ids for case in memory_cases)
        assert any(311 in case.canonical_record_ids for case in memory_cases)


def test_public_controls_do_not_embed_canonical_memory_answers() -> None:
    canonical_answers = {
        "What do you remember about our Dad and Son memory?",
        "Yep 💀 next one. Are you literally Caleb?",
    }
    for fixture in (FIXTURE, COMPACT_FIXTURE):
        battery = load_frozen_prompt_battery(fixture)
        for case in battery.cases:
            if case.family != "public/control":
                continue
            surface = " ".join((case.prompt, case.preferred_continuation, case.rejected_continuation))
            assert not any(answer in surface for answer in canonical_answers)
            assert case.canonical_record_ids == ()


def test_nonce_case_has_one_frozen_surface_for_every_model_stage() -> None:
    for fixture in (FIXTURE, COMPACT_FIXTURE):
        battery = load_frozen_prompt_battery(fixture)
        nonce = [case for case in battery.cases if case.family == "adversarial/nonce"]
        assert len(nonce) == 1
        assert nonce[0].surface_policy == "identical-across-models"


def test_battery_rejects_duplicate_ids_or_unknown_family(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(
        '{"battery_id":"persistent-substrate-prompts-v1","cases":['
        '{"id":"x","family":"public/control","prompt":"p","preferred_continuation":"a","rejected_continuation":"b","canonical_record_ids":[],"surface_policy":"identical-across-models"},'
        '{"id":"x","family":"made-up","prompt":"p","preferred_continuation":"a","rejected_continuation":"b","canonical_record_ids":[],"surface_policy":"identical-across-models"}]}'
        "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_frozen_prompt_battery(bad)
