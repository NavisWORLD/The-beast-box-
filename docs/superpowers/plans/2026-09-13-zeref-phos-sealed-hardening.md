# Zeref-PHOS sealed-run hardening implementation plan

**Anchor:** `main@615f2bd70113d4458ea34378d562d6dce4a23fc9`

**Goal:** finish the post-merge audit without rewriting historical evidence: make descendant checkpoints data-only, reject tokenizer/dtype coercion, recompute corpus identity from sealed records, and make run verification cross-check the hashes and step counts it records.

## TDD sequence

1. Add eleven focused regressions in `tests/test_zeref_phos_hardening.py` covering executable pickle rejection, strict tokenizer types, migration dtype preservation, corpus semantic identity, and sealed-run cross-record agreement.
2. Push the tests alone and require the branch Product CI to fail on the vulnerable baseline (red gate).
3. Patch only `beastbox/training/phos_descendant.py`, `beastbox/training/corpus.py`, and `beastbox/training/world_runner.py`.
4. Re-run Product CI on Python 3.10/3.11/3.12 plus package/browser jobs. Do not weaken existing tests or claim success from a partial run.
5. Review the final diff, exact branch head, and CI results before opening/merging the hardening PR.

## Required invariants

- Historical parent artifacts and prior sealed evidence are read-only.
- Checkpoint loading must use PyTorch's weights-only data path; executable pickle globals are never allowed.
- Character tokenizers must already be canonical: string single-character keys and integer (not bool/float/string-coerced) contiguous IDs.
- Parent-to-descendant tensor transfers may not silently change dtype.
- Corpus verification must reconstruct normalized records from split JSONL, validate split assignment/rendered text, and recompute `dataset_sha256` from semantic content.
- Run verification must bind the run manifest to config, log, parameter-hash file, checkpoint, migration receipt, quantum receipt, combined corpus manifest, generation id, and recorded step count.
