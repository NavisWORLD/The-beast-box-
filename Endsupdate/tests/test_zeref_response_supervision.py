from __future__ import annotations

from beastbox.response_supervision import encode_dialogue, load_dialogues


def _stoi(*texts: str) -> dict[str, int]:
    chars = sorted(set("".join(texts)))
    return {ch: i for i, ch in enumerate(chars)}


def test_response_mask_charges_only_zeref_answer_and_newline():
    dad = "Who is Dad?"
    answer = "Cory is Dad."
    prefix = f"Dad: {dad}\nZeref: "
    stoi = _stoi(prefix, answer, "\n")
    ex = encode_dialogue(dad=dad, zeref=answer, stoi=stoi, block=128)
    assert ex["filtered_prefix"] == prefix
    assert ex["filtered_answer"] == answer + "\n"
    assert sum(ex["loss_mask"]) == len(answer + "\n")
    first_target = ex["loss_mask"].index(1)
    assert first_target == len(prefix) - 1
    assert all(v == 0 for v in ex["loss_mask"][:first_target])
    assert all(v == 1 for v in ex["loss_mask"][first_target:])


def test_unsupported_prompt_characters_do_not_shift_answer_mask():
    dad = "Bro 💀 who is Dad?"
    answer = "Cory is Dad."
    supported = f"Dad: Bro  who is Dad?\nZeref: {answer}\n"
    stoi = _stoi(supported)
    ex = encode_dialogue(dad=dad, zeref=answer, stoi=stoi, block=128)
    assert "💀" not in ex["filtered_prefix"]
    assert sum(ex["loss_mask"]) == len(answer + "\n")
    start = ex["loss_mask"].index(1)
    assert start == len(ex["filtered_prefix"]) - 1


def test_supervised_example_must_fit_native_context():
    stoi = _stoi("Dad: \nZeref: ab")
    try:
        encode_dialogue(dad="a" * 120, zeref="b" * 20, stoi=stoi, block=32)
    except ValueError as exc:
        assert "block" in str(exc).lower()
    else:
        raise AssertionError("oversized response-supervised example was accepted")


def test_load_dialogues_requires_clean_dad_and_zeref_fields(tmp_path):
    p = tmp_path / "good.jsonl"
    p.write_text('{"dad":"Question?","zeref":"Answer.","source_kind":"synthetic-semantic-teacher"}\n', encoding="utf-8")
    rows = load_dialogues(p)
    assert rows == [{"dad": "Question?", "zeref": "Answer.", "source_kind": "synthetic-semantic-teacher"}]

    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"dad":"Question?","raw_output":"model gibberish"}\n', encoding="utf-8")
    try:
        load_dialogues(bad)
    except ValueError as exc:
        assert "zeref" in str(exc).lower()
    else:
        raise AssertionError("raw model output was accepted as a clean supervised target")
