# Finisher V2 — frozen-source compatibility decision (owner gate)

**Do not change the sealed-evidence guard just to get a green badge.** This is an engineering/research boundary decision for Cory Davis / NavisWORLD, not an automatic code fix.

## Confirmed blocker

At pinned main commit `4c4e4d38e645ee521534643d42843e181be4900a`, `scripts/smoke/sealed-evidence-guard.sh` compares current source bytes against historical swap anchor `b43f2883425e56446d3db8c009ea301b0adc21bc`. It explicitly protects the experimental ledgers `beastbox/dad_son.py`, `beastbox/persistent_substrate/ledger.py`, `beastbox/persistent_substrate/substrate.py`, plus original CST/retrieval source, scripts and `experiments/`. An unrelated earlier guard also pins `evidence/final-whole-organism-001/` to the independent scientific anchor. These are deliberate provenance controls, **not merely stale CI configuration**.

This branch's provisional A1/A2/A3/A4 patches modify exactly three of those protected source files. On [Product CI run 36327780550](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36327780550), Python 3.12 executed **1,146 passing tests** and the architecture acceptance script reported `passed: true`; the final `sealed-evidence` target failed because protected source bytes differed from their historical anchor. The combined quality job is **FAIL**, not green. Later commits, including the A5 verification regression and non-destructive quarantine, must be retested at their exact head.

The historical experimental implementation is deliberately frozen. The normal product `DurableRuntime` keeps its own SQLite `ContinuityStore` path, distinct from the Dad/Son offline swap ledger. Do not retroactively describe sealed model-swap artifacts as measurements of the new patch.

## Owner choices and consequences

1. **Versioned secure replacement (freeze intact).** Restore protected v1 source verbatim, move the new ledger/outbox implementation into a separately named v2 runtime module with narrowly reviewed adapters and dedicated tests, leaving historical experiment scripts pinned to their original implementation. Preserve migration and format compatibility. This avoids weakening the original guard but introduces a temporary second implementation and takes additional integration work. Audit all call sites so new production paths cannot silently fall back to insecure legacy writes.
2. **Approved historical source split and guard migration.** Preserve a byte-for-byte, hash-verified frozen v1 source bundle and historical experiment entrypoints, then require the guard to check that bundle **and** original immutable evidence while allowing tested active source to evolve. Independently reproduce old sealed outputs from the archived version. This changes the repository's protected-code policy and requires explicit owner approval, migration review and compatibility testing; never replace the guard with a blanket skip.
3. **Keep research frozen; document the scope exclusion.** Revert patches to protected paths, harden the separate current product runtime where needed and document legacy offline-ledger weaknesses as experimental limitations. The product can proceed without rewriting frozen science, but Phase A experimental-ledger acceptance remains **BLOCKED** and cannot be advertised as complete without an owner-approved exception.

**No option includes altering historical receipts, silently archiving active CST research, destructive ledger repair, production deployment or release.** Choose an option before a Phase A merge, then run both the historical reproduction and new security regressions under the selected design. The current branch remains draft-only with a deliberately visible guard failure pending this decision.
