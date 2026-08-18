from beastbox.descendant.corpus import fingerprint_record, normalize_text


def test_normalization_is_deterministic() -> None:
    assert normalize_text("  The\nLEGEND   of Zelda! ") == "the legend of zelda"


def test_explicit_zelda_franchise_text_is_quarantined_with_reason_codes() -> None:
    rec = fingerprint_record(
        source_ref="corpus/dialogue-1.txt",
        data=b"We reached Clock Town in The Legend of Zelda: Majora's Mask.",
        license_id="historical-unknown",
    )
    assert rec.disposition == "QUARANTINE"
    assert "ZELDA_FRANCHISE_EXPLICIT" in rec.contamination_labels
    assert rec.byte_sha256
    assert rec.normalized_text_sha256


def test_ambiguous_game_language_is_review_not_clean() -> None:
    rec = fingerprint_record(
        source_ref="corpus/ambiguous.txt",
        data=b"Link the game state to the controller and inspect the mask.",
    )
    assert rec.disposition == "REVIEW"
    assert "AMBIGUOUS_GAME_TERMS" in rec.contamination_labels


def test_clean_technical_cst_text_remains_clean() -> None:
    rec = fingerprint_record(
        source_ref="corpus/cst.txt",
        data=b"dyn12 updates twelve scalar states and mixes state affinity with causal attention.",
        license_id="project-origin",
    )
    assert rec.disposition == "CLEAN"
    assert rec.contamination_labels == ()


def test_same_normalized_text_gets_same_normalized_hash() -> None:
    a = fingerprint_record(source_ref="a.txt", data=b"CST   state\nupdate")
    b = fingerprint_record(source_ref="b.txt", data=b"cst state update!!")
    assert a.normalized_text_sha256 == b.normalized_text_sha256
    assert a.byte_sha256 != b.byte_sha256


def test_high_marker_overlap_is_quarantined() -> None:
    rec = fingerprint_record(
        source_ref="corpus/game.txt",
        data=b"Hyrule Triforce Ganondorf Master Sword Termina",
    )
    assert rec.disposition == "QUARANTINE"
    assert rec.contamination_score >= 0.5
