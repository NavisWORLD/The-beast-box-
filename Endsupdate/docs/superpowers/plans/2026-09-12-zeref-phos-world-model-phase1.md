# Zeref-PHOS World Model Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reproducible Phase 1 foundation for a new Zeref-PHOS descendant: immutable parent-lineage manifests plus deterministic, license-aware lexical/world corpus builders, without altering historical Zeref experiments or training model weights.

**Architecture:** Add a small `beastbox.training` package with two focused modules. `lineage.py` owns file hashing, canonical parent manifests, verification, and fail-closed lineage validation; `corpus.py` owns source-manifest validation, deterministic record normalization/deduplication, lemma/key-hash splitting, artifact emission, and content hashes. Thin scripts expose those modules without adding training or quantum injection yet.

**Tech Stack:** Python 3.10+, standard library only, existing `beastbox.hashutil` canonical JSON/SHA helpers, pytest.

**Spec:** `docs/superpowers/specs/2026-09-12-zeref-phos-world-model-design.md`

## Global Constraints

- Historical Zeref files, checkpoints, transcripts, and evidence are immutable and must not be modified.
- The new lineage is a descendant model lineage; it does not overwrite `zeref-pinned-active-checkpoint`.
- `MODEL ≠ MEMORY ≠ STATE ≠ PROVENANCE ≠ AUTHORITY` remains invariant.
- Phase 1 performs no model training and no quantum injection.
- Personal Beast Box memories are not included in training corpora by default.
- Corpus sources require explicit source IDs, source URIs, and non-empty license identifiers.
- Outputs are deterministic for identical input bytes and builder configuration.
- No live cloud credentials, provider tokens, or authority grants may appear in manifests.
- Python compatibility remains 3.10/3.11/3.12 and no new runtime dependency is introduced.

---

## File Structure

- Create `beastbox/training/__init__.py`: public Phase 1 exports only.
- Create `beastbox/training/lineage.py`: canonical file hashing, parent manifest creation, parent verification, and manifest persistence.
- Create `beastbox/training/corpus.py`: lexical/world source manifest validation, deterministic normalization, deduplication, splitting, rendering, and artifact hashes.
- Create `scripts/freeze_zeref_genesis.py`: CLI for building/verifying `ZEREF_GENESIS_BASELINE` from explicit local artifacts and expected hashes.
- Create `scripts/build_lexical_corpus.py`: CLI converting approved lexical JSONL records into deterministic train/validation/test artifacts and manifest.
- Create `scripts/build_world_corpus.py`: CLI converting approved world JSONL records into deterministic train/validation/test artifacts and manifest.
- Create `tests/test_training_lineage.py`: parent-lineage immutability, hashing, secret rejection, mismatch failures.
- Create `tests/test_training_corpus.py`: normalization, deduplication, deterministic split/output/hash, license/source validation.
- Modify no historical experiment files and no model implementation in Phase 1.

---

### Task 1: Parent lineage manifest foundation

**Files:**
- Create: `beastbox/training/__init__.py`
- Create: `beastbox/training/lineage.py`
- Test: `tests/test_training_lineage.py`

**Interfaces:**
- Produces: `sha256_file(path: str | Path) -> str`
- Produces: `build_parent_manifest(*, model_id: str, checkpoint_path: str | Path, architecture_path: str | Path, tokenizer_path: str | Path | None, memory_ledger_path: str | Path | None, expected_checkpoint_sha256: str | None = None, expected_architecture_sha256: str | None = None) -> dict[str, Any]`
- Produces: `verify_parent_manifest(manifest: Mapping[str, Any], *, root: str | Path = ".") -> dict[str, Any]`
- Produces: `write_canonical_json(path: str | Path, value: Mapping[str, Any]) -> str` returning the file SHA-256.

- [ ] **Step 1: Write failing lineage tests**

```python
from pathlib import Path

import pytest

from beastbox.training.lineage import build_parent_manifest, verify_parent_manifest


def test_parent_manifest_hashes_exact_files_and_verifies(tmp_path: Path):
    checkpoint = tmp_path / "zeref.pt"
    architecture = tmp_path / "arch.py"
    tokenizer = tmp_path / "tokenizer.json"
    ledger = tmp_path / "ledger.jsonl"
    checkpoint.write_bytes(b"checkpoint-v1")
    architecture.write_text("ARCH = 1\n", encoding="utf-8")
    tokenizer.write_text('{"a":0}\n', encoding="utf-8")
    ledger.write_text('{"memory_id":1}\n', encoding="utf-8")

    manifest = build_parent_manifest(
        model_id="zeref-genesis-baseline",
        checkpoint_path=checkpoint,
        architecture_path=architecture,
        tokenizer_path=tokenizer,
        memory_ledger_path=ledger,
    )

    assert manifest["schema"] == "zeref-phos-parent-manifest-v1"
    assert manifest["model_id"] == "zeref-genesis-baseline"
    assert manifest["artifacts"]["checkpoint"]["sha256"]
    assert verify_parent_manifest(manifest, root=tmp_path)["verified"] is True


def test_parent_manifest_fails_on_expected_checkpoint_mismatch(tmp_path: Path):
    checkpoint = tmp_path / "zeref.pt"
    architecture = tmp_path / "arch.py"
    checkpoint.write_bytes(b"checkpoint-v1")
    architecture.write_text("ARCH = 1\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="checkpoint SHA-256 mismatch"):
        build_parent_manifest(
            model_id="zeref-genesis-baseline",
            checkpoint_path=checkpoint,
            architecture_path=architecture,
            tokenizer_path=None,
            memory_ledger_path=None,
            expected_checkpoint_sha256="0" * 64,
        )
```

Add tests that mutate a file after manifest creation and require verification failure, reject empty model IDs, and reject manifest text containing keys matching `token`, `password`, `secret`, `credential`, or `api_key`.

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/test_training_lineage.py -q`

Expected: collection/import failure because `beastbox.training.lineage` does not exist.

- [ ] **Step 3: Implement minimal lineage module**

Use `Path.resolve()` only for reading; store artifact paths as caller-provided relative/name strings rather than machine-specific absolute paths. Hash files in 1 MiB chunks. Manifest shape:

```python
{
    "schema": "zeref-phos-parent-manifest-v1",
    "model_id": model_id,
    "artifacts": {
        "checkpoint": {"path": str(checkpoint_path), "sha256": ...},
        "architecture": {"path": str(architecture_path), "sha256": ...},
        "tokenizer": None | {"path": ..., "sha256": ...},
        "memory_ledger": None | {"path": ..., "sha256": ...},
    },
    "claim_boundary": {
        "historical_parent_immutable": True,
        "model_is_not_memory": True,
        "model_is_not_authority": True,
    },
}
```

`verify_parent_manifest` must re-hash every non-null artifact under `root`, compare exact SHA-256 values, reject path traversal outside `root`, and return `{"verified": True, "model_id": ..., "artifact_count": N}` only after all checks pass.

- [ ] **Step 4: Run lineage tests GREEN**

Run: `pytest tests/test_training_lineage.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add beastbox/training/__init__.py beastbox/training/lineage.py tests/test_training_lineage.py
git commit -m "feat: add Zeref lineage manifest foundation"
```

---

### Task 2: Deterministic corpus builder

**Files:**
- Create: `beastbox/training/corpus.py`
- Test: `tests/test_training_corpus.py`

**Interfaces:**
- Consumes: `beastbox.hashutil.canonical_json`, `beastbox.hashutil.sha256_obj`, Task 1 `sha256_file`.
- Produces: `normalize_lexical_record(record: Mapping[str, Any]) -> dict[str, Any]`
- Produces: `normalize_world_record(record: Mapping[str, Any]) -> dict[str, Any]`
- Produces: `build_corpus(*, kind: Literal["lexical", "world"], records: Iterable[Mapping[str, Any]], sources: Sequence[Mapping[str, str]], output_dir: str | Path, split_salt: str = "zeref-phos-v1") -> dict[str, Any]`
- Produces deterministic files: `train.jsonl`, `validation.jsonl`, `test.jsonl`, `train.txt`, `validation.txt`, `test.txt`, `manifest.json`.

- [ ] **Step 1: Write failing corpus tests**

```python
from pathlib import Path

import pytest

from beastbox.training.corpus import build_corpus


LEXICAL = [
    {
        "lemma": "Orbit",
        "part_of_speech": "noun",
        "definition": "A path around another body.",
        "synonyms": ["trajectory"],
        "antonyms": [],
        "examples": ["The satellite entered orbit."],
        "source_id": "dict-a",
    },
    {
        "lemma": "orbit",
        "part_of_speech": "noun",
        "definition": "A path around another body.",
        "synonyms": ["trajectory"],
        "antonyms": [],
        "examples": ["The satellite entered orbit."],
        "source_id": "dict-a",
    },
]

SOURCES = [{"source_id": "dict-a", "uri": "https://example.invalid/dict-a", "license": "CC-BY-4.0"}]


def test_lexical_builder_is_deterministic_and_deduplicates(tmp_path: Path):
    a = build_corpus(kind="lexical", records=LEXICAL, sources=SOURCES, output_dir=tmp_path / "a")
    b = build_corpus(kind="lexical", records=reversed(LEXICAL), sources=SOURCES, output_dir=tmp_path / "b")
    assert a["dataset_sha256"] == b["dataset_sha256"]
    assert a["record_count"] == 1
    assert a["split_counts"] == b["split_counts"]


def test_source_license_is_required(tmp_path: Path):
    with pytest.raises(ValueError, match="license"):
        build_corpus(
            kind="lexical",
            records=LEXICAL[:1],
            sources=[{"source_id": "dict-a", "uri": "https://example.invalid/dict-a", "license": ""}],
            output_dir=tmp_path,
        )
```

Also test Unicode NFC normalization, stable sorting of synonym/antonym lists, unknown `source_id` rejection, world records requiring `title`, `text`, `source_id`, and deterministic train/validation/test assignment.

- [ ] **Step 2: Run tests RED**

Run: `pytest tests/test_training_corpus.py -q`

Expected: import failure because `beastbox.training.corpus` does not exist.

- [ ] **Step 3: Implement deterministic normalization and split**

Use `unicodedata.normalize("NFC", text)` plus whitespace collapse for scalar text. Reject bool/non-string required fields. For lexical records lowercase/casefold the split key but preserve normalized display lemma. Sort and deduplicate synonym/antonym/example arrays.

Deduplicate records by canonical content excluding no provenance fields. Sort final records by `sha256_obj(record)` so input order cannot affect output.

Assign splits from the first 8 bytes of SHA-256 of `f"{split_salt}:{stable_key}"`:

```python
bucket = int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big") % 100
split = "train" if bucket < 90 else "validation" if bucket < 95 else "test"
```

For lexical records, `stable_key = lemma.casefold()`. For world records, `stable_key = f"{source_id}:{title.casefold()}"`.

Render lexical training text exactly as:

```text
TERM: {lemma}\nPART_OF_SPEECH: {part_of_speech}\nDEFINITION: {definition}\nSYNONYMS: {comma list or [NONE]}\nANTONYMS: {comma list or [NONE]}\nEXAMPLES: {joined with ' | ' or [NONE]}\n
```

Render world training text exactly as:

```text
TITLE: {title}\nTEXT: {text}\nSOURCE: {source_id}\n
```

Write JSONL with one canonical JSON object per line plus trailing newline. Compute each artifact SHA-256 after writing. `dataset_sha256` is `sha256_obj({"kind": kind, "records": normalized_sorted_records, "sources": normalized_sorted_sources, "split_salt": split_salt})`.

- [ ] **Step 4: Run corpus tests GREEN**

Run: `pytest tests/test_training_corpus.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add beastbox/training/corpus.py tests/test_training_corpus.py
git commit -m "feat: add deterministic Zeref corpus builder"
```

---

### Task 3: Genesis and corpus CLI entry points

**Files:**
- Create: `scripts/freeze_zeref_genesis.py`
- Create: `scripts/build_lexical_corpus.py`
- Create: `scripts/build_world_corpus.py`
- Modify tests: `tests/test_training_lineage.py`, `tests/test_training_corpus.py`

**Interfaces:**
- Consumes Task 1/2 APIs only; scripts contain no independent hashing/normalization logic.
- `freeze_zeref_genesis.py` accepts explicit artifact paths plus optional expected hashes, writes a canonical manifest, immediately re-verifies it, and prints one compact JSON summary.
- Corpus scripts accept `--records`, `--sources`, `--out`, optional `--split-salt`, parse JSONL/JSON, call `build_corpus`, and print manifest JSON.

- [ ] **Step 1: Add subprocess-level failing tests**

Use `subprocess.run([sys.executable, script, ...], cwd=repo_root, capture_output=True, text=True)` with temporary fixture artifacts. Require exit 0 for valid inputs, nonzero for SHA mismatch or missing license, and require the emitted manifest to verify through the library API.

- [ ] **Step 2: Run targeted tests RED**

Run: `pytest tests/test_training_lineage.py tests/test_training_corpus.py -q`

Expected: CLI tests fail because scripts do not exist.

- [ ] **Step 3: Implement thin CLIs**

`freeze_zeref_genesis.py` must default `--model-id` to `zeref-genesis-baseline`; it must never infer checkpoint locations from historical experiment directories. All artifact paths are explicit arguments.

The corpus scripts read a source JSON array shaped like:

```json
[
  {"source_id": "dict-a", "uri": "https://example.invalid/dict-a", "license": "CC-BY-4.0"}
]
```

and line-delimited record objects from `--records`.

- [ ] **Step 4: Run targeted tests GREEN**

Run: `pytest tests/test_training_lineage.py tests/test_training_corpus.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/freeze_zeref_genesis.py scripts/build_lexical_corpus.py scripts/build_world_corpus.py tests/test_training_lineage.py tests/test_training_corpus.py
git commit -m "feat: add Zeref genesis and corpus tooling"
```

---

### Task 4: Phase 1 verification gate

**Files:**
- Modify only if verification exposes a real defect in files from Tasks 1–3.

**Interfaces:**
- Produces no new API. This task proves Phase 1 is safe to hand to Phase 2.

- [ ] **Step 1: Run focused tests**

Run: `pytest tests/test_training_lineage.py tests/test_training_corpus.py -q`

Expected: zero failures.

- [ ] **Step 2: Run adjacent safety tests**

Run: `pytest tests/test_optional_resources.py tests/test_persistent_substrate_models.py -q`

If the exact persistent-substrate test filename differs on current branch, resolve the existing test that imports `beastbox.persistent_substrate.models` and run that file; do not invent a replacement test.

Expected: zero failures, demonstrating the Phase 1 package did not alter cloud-authority or frozen-model adapters.

- [ ] **Step 3: Run full repository suite**

Run: `python -m pytest -q`

Expected: zero failures.

- [ ] **Step 4: Run quality checks**

Run the repository's existing canonical quality command (`make quality` if present on the branch); otherwise run the exact Ruff/mypy commands used by current CI. Do not substitute a narrower check.

Expected: zero lint/type failures.

- [ ] **Step 5: Inspect diff for historical mutation**

Run:

```bash
git diff --name-only $(git merge-base HEAD origin/main)..HEAD
```

Expected: only the approved design/plan plus `beastbox/training/*`, the three new scripts, and the two new/modified tests. No `experiments/zeref/**`, historical evidence, checkpoints, existing PHOS implementation, or persistent-substrate experiment files may be changed.

- [ ] **Step 6: Commit any verification-only correction if required**

Only if a real defect was found and fixed; rerun Steps 1–4 after the correction.

---

## Phase 1 Exit Criteria

Phase 1 is complete only when:

1. A parent manifest can be built from explicit Zeref artifact paths and independently re-verified.
2. Any expected hash mismatch fails closed before a manifest is accepted.
3. Manifest content does not contain credentials/secrets.
4. Lexical/world builders reject sources without explicit licenses.
5. Identical records supplied in different input order produce the same dataset hash and split artifacts.
6. Duplicate normalized lexical records collapse deterministically.
7. Train/validation/test membership is key-hash deterministic and independent of process randomness.
8. All generated artifacts have recorded SHA-256 values.
9. No historical Zeref/model evidence is modified.
10. Full repository tests and canonical quality gates pass.

## Deferred to Phase 2

The following approved spec items are intentionally not implemented by this plan: quantum receipt schema/12D transforms; measured/pseudorandom/zero/shuffled controls; PHOS external state injection; model training; evaluation; product provider registration. Those get their own implementation plans after this foundation is green.