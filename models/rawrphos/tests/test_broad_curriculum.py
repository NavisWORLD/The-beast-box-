"""Offline checks for the optional 30-domain synthetic supplemental curriculum."""
from collections import Counter
import json

import pytest

from rawrphos.scripts.prepare_broad_curriculum import CATEGORIES, export, generate


def test_reproducible_complete_disjoint_categories():
    train, val = generate()
    assert len(CATEGORIES) == 30
    assert train == generate()[0] and val == generate()[1]
    tc = Counter(r["category"] for r in train)
    vc = Counter(r["category"] for r in val)
    assert set(tc) == set(vc) == set(CATEGORIES)
    assert min(tc.values()) >= 3 and min(vc.values()) >= 1
    assert len(train) > 700 and len(val) > 50
    assert all(r["origin"].startswith("task-authored synthetic") for r in train + val)
    prompts = lambda rows: {json.dumps(r["messages"], sort_keys=True) for r in rows}
    assert prompts(train).isdisjoint(prompts(val))


def test_math_answers_are_exact():
    train, val = generate()
    for r in train + val:
        prompt = r["messages"][-1]["content"]
        if r["category"] == "arithmetic":
            if " + " in prompt:
                nums = prompt.removeprefix("What is ").removesuffix("?").split(" + ")
                expected = int(nums[0]) + int(nums[1])
            else:
                nums = prompt.removeprefix("Compute ").removesuffix(".").split(" times ")
                expected = int(nums[0]) * int(nums[1])
            assert r["reply"] == str(expected)


def test_export_immutable_hashes_and_no_overwrite(tmp_path):
    folder = tmp_path / "new-curriculum"
    a = export(folder)
    assert a["schema"] == "rawrphos-broad-curriculum-v1"
    assert a["train_examples"] > 700
    assert a["validation_examples"] > 50
    assert len(a["dataset_sha256"]) == 64
    with pytest.raises(FileExistsError):
        export(folder)
