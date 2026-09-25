"""A new dataset phase must preserve original validation and suppress split leakage."""
import hashlib
import json

import pytest

from rawrphos.data.conversation import load_dataset, write_dataset
from rawrphos.data.corpus import canonical
from rawrphos.scripts import prepare_broad_blend as blend
from rawrphos.scripts.prepare_broad_curriculum import export


def old_row(prompt, reply, *, split):
    return {
        "messages": [{"role": "user", "content": prompt}],
        "reply": reply, "category": "dialogue",
        "source": f"fixture/original/{split}",
        "license": "Apache-2.0",
    }


@pytest.fixture
def local_sources(tmp_path, monkeypatch):
    original=tmp_path/"original"
    supplement=tmp_path/"broad"
    train=[old_row("Hi there!", "Hi!", split="train"),
           old_row("How do telescopes work?", "They collect light.", split="train")]
    validation=[old_row("What is 1 + 1?", "Two.", split="validation"),
                old_row("Why does an eclipse happen?", "Alignment.", split="validation")]
    om=write_dataset(original,train,validation,{"license":"Apache-2.0","fixture":True})
    bm=export(supplement)
    monkeypatch.setattr(blend,"ORIGINAL_SHA",om["dataset_sha256"])
    monkeypatch.setattr(blend,"SUPPLEMENT_SHA",bm["dataset_sha256"])
    return original,supplement,train,validation


def test_blend_is_immutable_retains_old_validation_and_has_distinct_synthetic_categories(local_sources,tmp_path):
    original,supplement,old_train,old_val=local_sources
    out=tmp_path/"blended"
    manifest=blend.build(original,supplement,out)
    saved=load_dataset(out)
    prov=manifest["provenance"]
    assert prov["counts"]["base_train"]==len(old_train)
    assert prov["counts"]["base_validation"]==len(old_val)
    assert prov["counts"]["supplement_train"]>=600
    assert prov["counts"]["supplement_validation"]>=50
    assert len(prov["supplement_train_categories"])>=27
    assert saved["validation"][:len(old_val)]==old_val
    assert saved["train"][:len(old_train)]==old_train
    original_sha=hashlib.sha256(b"".join(canonical(row)+b"\n" for row in old_val)).hexdigest()
    assert json.loads((out/"blend-receipt.json").read_text())["original_validation_sha256"]==original_sha
    assert not {blend.question(r) for r in saved["train"]} & {blend.question(r) for r in saved["validation"]}
    assert not prov["personal_user_history_used"]
    with pytest.raises(FileExistsError):
        blend.build(original,supplement,out)


def test_blend_rejects_corrupted_audited_source(local_sources,tmp_path):
    original,supplement,*_=local_sources
    with (supplement/"train.jsonl").open("a") as f:
        f.write('{"injected":"bad"}\n')
    with pytest.raises(ValueError,match="digest"):
        blend.build(original,supplement,tmp_path/"invalid")


def test_blend_blocks_train_rows_that_match_old_validation(local_sources,tmp_path):
    original,supplement,*_=local_sources
    manifest=blend.build(original,supplement,tmp_path/"blended")
    assert manifest["provenance"]["cross_split_rejections"]["supplemental_train_reserved_or_original_validation"]>=1
    dataset=load_dataset(tmp_path/"blended")
    assert "What is 1 + 1?" not in [
        r["messages"][-1]["content"] for r in dataset["train"]]
