# Finisher V2 security overlay — frozen pristine source + verified product tree

**Approved by Cory / NavisWORLD for the isolated PR #129 only.** The experimental code files below, historical model-swap scripts and original evidence stay exactly as recorded in the historical source pins:

- `beastbox/dad_son.py`
- `beastbox/persistent_substrate/ledger.py`
- `beastbox/persistent_substrate/substrate.py`

The original `scripts/smoke/sealed-evidence-guard.sh` remains unchanged and runs on the **pristine Git checkout**. These source files must have *zero diffs in PR #129*. The overlay is exclusively a **new versioned product tree** built outside the original worktree. The original historical experiment never silently imports the new implementation, and the output is never called a historical reproduction.

## Deterministic application

`PATCH_MANIFEST.json` uses canonical JSON (sorted keys, compact separators, UTF-8, no NaN) and records each patch's raw SHA-256, target source SHA-256 before that step and patched SHA-256 after. A single target can have successive security fixes; each following stage pins the immediately previous stage's exact SHA. This is **seven changes**, one patch for each isolated change or shared prerequisite, in explicit manifest order. Every patch header repeats its target, hashes, rationale and regression test. `PATCH_MANIFEST.sha256` repeats the manifest's exact byte digest.

The script itself pins manifest SHA-256 `fb031195a7055c2a59e98b5532a5d392789fbe4ecf1b42c7aacdd8b664061ec8`. Run from the untouched branch checkout:

```bash
python scripts/apply-security-patches.py --verify-only
scripts/smoke/sealed-evidence-guard.sh
python scripts/apply-security-patches.py --destination ../beastbox-finisher-product
cd ../beastbox-finisher-product
python -m pip install -e .
python -m pytest tests/test_persistent_substrate_ledger.py tests/test_persistent_substrate_substrate.py tests/test_zeref_dad_son_memory.py
```

The builder checks patch/manifest digests, stages a *separate detached Git worktree*, checks each target's original SHA, applies the declared unified diff with `git apply --check`, checks the patched SHA and moves the **fully verified** staged worktree to the named destination. If any check fails, no product tree is promoted and the staging worktree is discarded. The pristine original tree is never edited. The destination must be outside the source and not already exist. The product worktree carries normal Git ancestry, but its active patched source is intentionally **dirty relative to the frozen commit**; this is why historical source guards are never run in the product tree.

## What these hashes guarantee — and what they do not

Hashes authenticate product content **relative to this particular pinned, reviewed manifest and the original source anchors**. A neighboring SHA-256 file alone is not an independent trust root. Bind the manifest digest to an independently retained owner-reviewed signed commit / release attestation before claiming tamper resistance against host-level rewrites. A privileged adversary able to edit the script, workflow, repository history and external attestations is outside the local hash-chain threat model.

The overlay retains the documented Phase A limitations: the new in-process append pin is **not yet an independently authenticated cross-restart tip**, the cooperating SQLite writer lock does not constrain an attacker writing the ledger outside the protocol, and the outbox crash matrix needs complete failure-injection coverage before a release. Old frozen software remains historically reproducible, but should not be selected as a new product security implementation.

## CI and receipts

1. **Pristine CI:** check the original sealed-source guard in the original checkout; run the documented historical offline fixture on original code, with independent hashes and logs uploaded as an Actions artifact. Full real-model A→B→A may require unavailable old weights or external artifacts: record such limits; never substitute offline simulation for a new real-model execution.
2. **Product CI:** invoke the builder, install **from the product worktree**, and run the full Python 3.10/3.11/3.12 matrix there. Run the original historical guard separately against the pristine checkout, never as an exception within patched source.
3. Builder writes a canonical per-stage receipt in `build/security-overlay-receipt.json` inside the patched tree. Archive it with the test reports and keep exact source/manifest/patched hashes attached to the PR.

No auto-merge, cloud deployment, release or license change is implied by creating this patch series. See [Finisher V2 status](../docs/FINISHER_V2_STATUS.md), [trust model](../docs/THREAT_MODEL.md) and [frozen-source approval history](../docs/FINISHER_V2_FROZEN_SOURCE_DECISION.md).
