"""Owner feed ingestion: bounded ticks, measured features, verifiable append-only chain, candidates only."""
from pathlib import Path

import pytest

from beastbox.owner_feed_ingest import CHAIN_SCHEMA, MAX_CHUNK_BYTES, chunk_text, ingest, normalize, sense, verify_chain

ROOT = Path(__file__).resolve().parents[1]
STORY = ("In the land of Eridoria the sun dipped low. Arin worked the forge! Did the traveler speak true? "
         "“A hero will rise,” he said.\n\n\n  \nThe journey took him far. " * 60)


def run(text, chain=(), path="zeref/feed/owner/story.txt", author="NavisWORLD"):
    return ingest(text, path=path, commit_sha="abc", author_login=author, chain=list(chain), ingested_at="2026-11-12T19:00:00Z")


def test_chunks_are_bounded_and_lose_no_words():
    chunks = chunk_text(STORY)
    assert len(chunks) > 3
    assert all(0 < len(c.encode("utf-8")) <= MAX_CHUNK_BYTES for c in chunks)
    assert " ".join(chunks).split() == normalize(STORY).split()


def test_over_cap_sentence_and_word_still_fit():
    giant = ("word " * 600) + "x" * 3000
    chunks = chunk_text(giant)
    assert all(len(c.encode("utf-8")) <= MAX_CHUNK_BYTES for c in chunks)
    assert "".join(chunks).replace(" ", "") == giant.replace(" ", "")


def test_features_are_measured_and_deterministic():
    a, b = sense("Hello there! Is it you?"), sense("Hello there! Is it you?")
    assert a == b and len(a) == 12 and all(0.0 <= v <= 1.0 for v in a.values())
    assert a["question_ratio"] > 0 and a["exclaim_ratio"] > 0
    assert sense("plain words only")["question_ratio"] == 0.0


def test_chain_is_append_only_verifiable_and_continues_state():
    r1 = run(STORY)
    assert r1["manifest"]["status"] == "ingested" and r1["manifest"]["snapshots"] == len(r1["snapshots"])
    chain = r1["chain_entries"]
    assert verify_chain(chain)["ok"] and all(e["schema"] == CHAIN_SCHEMA for e in chain)
    assert all(len(e["state_after"]) == 12 for e in chain)
    r2 = run("A second file. It folds into the same state.", chain=chain, path="zeref/feed/owner/two.md")
    assert r2["chain_entries"][0]["prev_hash"] == chain[-1]["hash"]
    assert r2["manifest"]["state_before"] == chain[-1]["state_after"]
    assert verify_chain(chain + r2["chain_entries"])["ok"]
    tampered = [dict(e) for e in chain]; tampered[1]["chunk_sha256"] = "0" * 64
    assert not verify_chain(tampered)["ok"]
    # same bytes again: no duplicate ingestion
    assert run(STORY, chain=chain)["manifest"]["status"] == "already_ingested"
    # deterministic: the same file from genesis gives the same head
    assert run(STORY)["manifest"]["chain_head"] == r1["manifest"]["chain_head"]


def test_candidates_only_and_owner_only():
    r = run(STORY)
    assert r["manifest"]["training_eligible"] is False and r["manifest"]["fair_gate"] == "pending"
    assert all(s["training_eligible"] is False for s in r["snapshots"])
    labels = r["manifest"]["labels"]
    assert labels["heartbeat"] == "SIMULATED" and labels["ibm"] == "RECORDED seed" and labels["rigetti"] == "SIMULATED"
    assert "not literal infinite context" in labels["stream"]
    with pytest.raises(PermissionError):
        run(STORY, author="someone-else")
    with pytest.raises(ValueError):
        run(STORY, path="zeref/feed/inbox/story.txt")
    with pytest.raises(ValueError):
        run(STORY, path="zeref/feed/owner/story.exe")


def test_module_never_touches_training_paths():
    src = (ROOT / "beastbox" / "owner_feed_ingest.py").read_text(encoding="utf-8")
    for bad in ("import random", "random.", "train_mix", "storeLesson", "open(", "requests", "urllib", "qiskit"):
        assert bad not in src


def test_workflow_is_owner_only_and_writes_a_data_branch():
    wf = (ROOT / ".github" / "workflows" / "zeref-owner-feed-ingest.yml").read_text(encoding="utf-8")
    assert "zeref/feed/owner/**" in wf and "github.actor == 'NavisWORLD'" in wf
    assert "zeref-owner-feed" in wf and "push origin HEAD:main" not in wf
    assert "secrets." not in wf.replace("secrets.GITHUB_TOKEN", "")
