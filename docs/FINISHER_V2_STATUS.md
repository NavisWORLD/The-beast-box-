# Finisher V2 — evidence-led execution status

**Repository:** `NavisWORLD/The-beast-box-`
**Pinned source baseline:** `4c4e4d38e645ee521534643d42843e181be4900a` (`main`, observed 2026-09-27).
**Work branch:** `feature/beastbox-finisher-v2-001`. No production merge, release, deployment, paid action or cross-repository edit is authorized by this work.
**Source status:** Public GitHub repository, owner write permission confirmed through the connected GitHub installation. Current baseline root `LICENSE` is Apache License 2.0 and `pyproject.toml` advertises the OSI-approved Apache software license; `NOTICE` limits that grant to covered original contributions. Individually marked external models, datasets, media and research retain their own terms. Historic revisions retain their original grants.

## Baseline and limits

- Default branch `main` and its source commit are pinned above. Active concurrent work exists, including UI PR #98, Rigetti simulator PRs #123/#124 and Quantum Buddy PR #122; none is merged or modified by this branch.
- Source inspection confirms the Python stdlib-only core `pyproject.toml` has `dependencies=[]`, supports Python >=3.10, and lists optional ML/quantum/cloud/secure extras. Working baseline must also be checked on the supported 3.10–3.12 versions.
- Existing CI workflow `.github/workflows/ci.yml` runs core tests under Python 3.10 and 3.12 on pull requests; evidence workflows and optional platform tests are separate. Prior claims of 1,075 passing tests are **not** a current-run measurement.
- Local container access has Python 3.13 but cannot resolve `github.com`. It cannot clone the repository, install the exact source, or run its full test suite locally; use the repository's existing GitHub Actions on the PR and attach run URLs, test counts and failures here. **Baseline install, full tests, all optional matrices, quickstart and deployment remain NOT RUN by Finisher V2 until independently verified.**
- Protected original evidence: `docs/CLAIM_BOUNDARIES.md`, `docs/SCIENTIFIC_BOUNDARIES.md`, `docs/PERSISTENT_SUBSTRATE_MODEL_SWAP_002_FINAL_REPORT.md` and existing sealed evidence directories. Historical outcomes must not be rewritten.

## Initial code inventory (source-inspected, not full dependency audit)

| Surface | Primary path | Initial wiring / review |
| --- | --- | --- |
| Runtime / CLI | `beastbox/durable.py`, `beastbox/cli.py` | Core; test fresh start and restart |
| Personal memory | `beastbox/memory.py` | SQLite, lexical cosine, Hebbian associations; relevance floor needs measurement |
| Checkpoint integrity | `beastbox/continuity.py` | SQLite hash chain with memory digest; not signed against privileged rewrites |
| Experimental ledgers | `beastbox/persistent_substrate/ledger.py`, `beastbox/dad_son.py` | Inspect A1–A4 separately from production durable runtime |
| Experimental live invariants | `beastbox/persistent_substrate/substrate.py`, `runner.py` | Immutable input recheck exists; comparison capture needs review |
| Retrieval / knowledge | `beastbox/refractive_memory.py`, `world_knowledge.py`, `world_r12.py` | Compare ranking ablations before modifying CST state terms |
| Authority and lifecycle | `beastbox/box.py`, `beastbox/organism.py`, `beastbox/heartbeat.py` | Audit call graph before wiring agents |
| Providers / cloud / UI | `beastbox/providers.py`, `apps/beastbox-cloud/` | Preserve owner-authenticated boundaries and existing integrations |
| Research | Existing CST/dyn12/R12/CNS7, fruit-fly, quantum and RAWRPHØS paths | Preserve and build compatibility matrix, not bulk archive |

## Integrity phase A — reproducibility ledger

| ID | Evidence at pinned source | Current milestone |
| --- | --- | --- |
| A1 | `verify_memory_chain` verifies internal linkage but has no independent expected final tip or length parameter; caller context/immutable prefix gives only partial protection. | OPEN: map trust-boundary callers and define protected tip/count |
| A2 | `get_verified_memory_record` calls verifier then reopens the path. | PATCHED on branch: verifier can return rows decoded from exactly validated bytes; added path-substitution regression. CI result pending. |
| A3 | `StateEventLedger.append` verifies, appends and verifies again without cross-process lock. | OPEN: Windows-relevant serialization, fault tests and non-destructive quarantine |
| A4 | `DadSonLedger.append_experience` commits SQLite before opening JSONL, with no explicit fsync. | OPEN: transactional-outbox design and write-boundary fault injection |
| A5 | `snapshot` rechecks live hashes against construction captures, then emits those construction captures in `immutable_inputs`. | OPEN: re-observation in receipts and regression |
| A6 | `continuity.py` accurately admits privileged host rewrite limitations; top-level security docs retain old private/permission-required phrasing. | DOCUMENTATION: create `docs/THREAT_MODEL.md`, correct conflicting security docs after owner review |

A static code match is not a successful runtime regression. For each row, link a failing-before and passing-after test or document why a hypothesis was rejected.

## Retrieval and later phases

- **B:** NOT RUN — chat call graph, held-out relevance, 500 / 5k / 50k latency, embedding identity and explicit fallback.
- **C:** NOT RUN — decay, consolidation, archival, privacy deletion, 10k-turn soak.
- **D:** NOT RUN — bounded tool execution, denial logs, restart/swap revocation.
- **E:** NOT RUN — fixed/adaptive held-out comparison; no intelligence claim.
- **F:** NOT RUN — multi-provider measured routed A→B→A acceptance.
- **G:** NOT RUN — source-by-source compatibility of COSMOS, active CST, CNS7, R12, RAWRPHØS, sensor, fruit-fly and deployment integration.

## Licensing and owner gates

The older brief's 'currently proprietary' assertion is **outdated on this pinned source**. Root `LICENSE`, `NOTICE` and package classifiers currently state Apache-2.0 for covered original source. However, `LICENSE_HISTORY.md` still contains stale 'draft-only' / 'permission required' text and `SECURITY.md` still calls the repository private; reconcile this documentation under owner review. Do not relicense third-party inputs. No new owner relicensing decision was performed by Finisher V2.

**Release gate:** owner confirmation of final per-component rights/NOTICE audit; approval before any active-research move, resource spending, deployment, merge, tag or release. No permission is implied by this status document.

## Commands / results

- Static source: GitHub connector `get_repo`, `fetch`, `fetch_file` pinned to `main` head above.
- Existing `ci.yml`: `pip install -e '.[dev,ml]'` then `pytest` under Python 3.10/3.12; pull-request execution and exact results not yet observed here.
- Planned focused check: `python -m pytest -q tests/test_persistent_substrate_ledger.py`.
- Preservation checks: `git diff --exit-code c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f -- evidence/final-whole-organism-001/` on CI; monitor full branch diff and enforce no original evidence edits.

## Next authorized step

Finish Phase A's verified-bytes regression, run it on the PR, then implement and test a cross-platform state-ledger lock and crash-safe dual-write plan. Leave all deployment and release gates closed.
