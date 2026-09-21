from __future__ import annotations

import json

from beastbox.r12_physics_probe import FROZEN_R12_VECTOR, PROTECTED_LEDGER_TIP_SHA256, PROTECTED_STATE_SHA256, TALK4_SHA256, sha256_json, verify_preregistration
from scripts.make_r12_physics_preregistration import PROTECTED_FILES, make_preregistration


def _repo(tmp_path):
    state=tmp_path/"experiments/zeref-dad-son-001/reality-memory/state/r12-state.json"
    manifest=tmp_path/"experiments/zeref-dad-son-001/reality-memory/manifest.json"
    ledger=tmp_path/"experiments/zeref-dad-son-001/reality-memory/ledger/reality-events.jsonl"
    history=tmp_path/"experiments/zeref-dad-son-001/reality-memory/state/r12-history.jsonl"
    for p in (state,manifest,ledger,history): p.parent.mkdir(parents=True,exist_ok=True)
    state.write_text(json.dumps({"sequence":4,"vector":dict(FROZEN_R12_VECTOR),"state_sha256":PROTECTED_STATE_SHA256})+"\n")
    manifest.write_text(json.dumps({"active_lineage":"ZEREF-DAD-SON-TALK-004","active_checkpoint_sha256":TALK4_SHA256,"durable_memory_record_count":352,"reality_ledger_tip_sha256":PROTECTED_LEDGER_TIP_SHA256,"r12_state_sha256":PROTECTED_STATE_SHA256})+"\n")
    ledger.write_text("sealed-ledger\n"); history.write_text("sealed-history\n")
    return tmp_path


def test_prereg_builder_seals_all_protected_files(tmp_path):
    repo=_repo(tmp_path); out=tmp_path/"out"
    result=make_preregistration(repo_root=repo,source_commit="a"*40,out_root=out)
    packet=json.loads((out/"preregistration.json").read_text())
    digest=(out/"PREREGISTRATION_SHA256").read_text().strip()
    assert digest==sha256_json(packet)==result["preregistration_sha256"]
    verify_preregistration(packet,digest)
    receipt=json.loads((out/"protected-inputs.json").read_text())
    assert set(receipt["files"])==set(PROTECTED_FILES)
    assert packet["workload"]["planned_hardware_shots"]==1179648
