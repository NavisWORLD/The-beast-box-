# Finisher V2 — evidence-led implementation and release hold

**Repository / draft PR:** [NavisWORLD/The-beast-box- #129](https://github.com/NavisWORLD/The-beast-box-/pull/129).
**Initial main baseline:** `4c4e4d38e645ee521534643d42843e181be4900a`.
**Prior corrected-code checkpoint:** `2df88c4c6c6fbee8e2e59433efa3148c48fe662b`.
**Recovered concurrent branch checkpoint:** `2b0576475779cfb4c53c241f808486b6042be670`.
**Branch:** `feature/beastbox-finisher-v2-001`.
**Owner decision:** [final Option 1: separate V1/V2 source](FINISHER_V2_FROZEN_SOURCE_DECISION.md). Interim patch-overlay commits are retained in branch history, **not** an active build architecture. No merge, production deployment, release, paid cloud task or licensing change is authorized.

## Exact frozen-source integrity and derived modules

The historical guard is **unchanged**. The original source files were fetched independently from historical Git commit
`b43f2883425e56446d3db8c009ea301b0adc21bc` and their exact UTF-8
byte SHA-256 values checked against the current protected paths. The separate
scientific-evidence anchor remains
`c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f`.

| Original immutable V1 source | Verified historical SHA-256 | Reviewed, separate secure V2 |
| --- | --- | --- |
| `beastbox/dad_son.py` | `0500094e0eabadc13bc4e1b819ae42f320b4af32e16ceb405a9e2cf2e8bcc6a5` | `beastbox/dad_son_v2.py` |
| `beastbox/persistent_substrate/ledger.py` | `a32996e3e1093ee58222c50364d9c1800811419a37a55a524c945047fac899c5` | `beastbox/persistent_substrate/ledger_v2.py` |
| `beastbox/persistent_substrate/substrate.py` | `e579038e3c9cdf0e2f7a4a7a39e1b30d8b39b8ca854c7bc021a070a926a9260a` | `beastbox/persistent_substrate/substrate_v2.py` |

The manifest `docs/VERSION_MANIFEST.json` uses canonical JSON and has
reviewed digest `bd75a778a646832f91f00577fc7d9b4e008e4d9f8ee1e0313f9084e3511a6971`.
The verifier `scripts/verify_versioned_sources.py --git-anchor` checks all six
files against declared bytes, the known original pins and historical Git
objects; see [VERSIONING.md](VERSIONING.md). These same-repository hashes
are **provenance metadata**, not a substitute for independently retained
signatures or an external secure anchor.

Secure tests explicitly use V2 while historical experimental runners retain
V1 imports. The separately designed `DurableRuntime` still uses
`ContinuityStore`, not the offline Dad/Son ledger. The product does **not**
yet claim a blanket migration of all persistent consumers to V2.

## Finisher phases (only evidence-backed state)

| Phase | Status | Evidence / still required |
| --- | --- | --- |
| A — Security and recovery | **in progress** | [V2 ledger](../beastbox/persistent_substrate/ledger_v2.py), [V2 Dad/Son outbox](../beastbox/dad_son_v2.py), [V2 substrate](../beastbox/persistent_substrate/substrate_v2.py), [recovery regressions](../tests/test_finisher_v2_security_acceptance.py), and [lineage tamper tests](../tests/test_finisher_v2_versioning.py) committed. Original V1 hashes verified; fresh independent historical/product/Windows run evidence and independently authenticated cross-restart anchor still outstanding. |
| B — Semantic retrieval | **in progress** | [Lexical relevance guard and regression](../beastbox/memory.py), [test](../tests/test_full_runtime.py). One-pass product retrieval graph, optional embeddings/hybrid experiments, held-out quality and latency benchmarks incomplete. |
| C — Memory lifecycle | **in progress** | Source-attributed, stopword-aware thematic index in [memory](../beastbox/memory.py) with regression; not equivalent to validated abstractive summaries. Contradictions, archival, restoration, intentional deletion, long growth/soak unfinished. |
| D — Agency | **not started** | Existing product primitives are not an audited scoped autonomy/revocation/restart test matrix. |
| E — Adaptation | **not started** | No controlled held-out adaptive/frozen state measurements; no superiority claim. |
| F — Multi-model routing | **not started** | Original [historical A→B→A result](PERSISTENT_SUBSTRATE_MODEL_SWAP_002_FINAL_REPORT.md) retained. No fresh measured capability routing proving Finisher F. |
| G — Ecosystem reconciliation | **in progress** | [Source-inspected matrix](FINISHER_V2_ECOSYSTEM_MATRIX.md) covers COSMOS/CST/dyn12/CNS7/R12, RAWRPHØS, sensors, quantum adapters and fruit-fly sources; live integration and compatibility contracts remain to be tested. |

## Milestone 1 — frozen-source architectural blocker

- [x] Final owner selection documented: versioned V1 / separate secure V2.
- [x] Three changed historical paths restored verbatim to historical Git blobs; existing guard script untouched.
- [x] Prior V2 A1–A4 corrections relocated to separate modules with explicit V2 dependencies.
- [x] Versioning docs, canonical manifest and tamper-verifier committed, with negative tests.
- [ ] Unchanged historical guard passed at final exact commit (see [Actions](https://github.com/NavisWORLD/The-beast-box-/pull/129/checks)).
- [ ] Historical offline reproduction independently passed at final exact commit and receipt archived. Deterministic offline simulation is **not** the original externally dependent real-model experiment.
- [ ] Full relevant A1–A5 security, restart/fault and actual Windows contract tests passed at final exact commit. In-process expected count/tip does not prove independent authentication across restarts; externally retained protected receipt infrastructure remains an explicitly scoped limitation.
- [ ] Fresh **combined** Product CI green at final commit on each of Python 3.10/3.11/3.12; original pre-restructure 1,150 test counts do not satisfy this gate.

## Milestone 2 — overall Finisher acceptance

- [ ] Each Phase A–G reaches evidence-backed acceptance or the owner approves a specifically reduced release scope.
- [ ] All required performance, trust, authority, platform, packaging and ecosystem compatibility gates are evidenced.
- [ ] Independent external trust anchor for persisted memory implemented and evaluated for the defined attacker/trust model.
- [ ] All scientific claims remain limited to recorded measurements; historical source and receipts preserved.
- [ ] Release blocker list closed, reproducible artifact hashes and final commit recorded.
- [ ] Separate owner authorization for any merge, production deployment, release or cost-bearing cloud execution.

## Test history and reporting discipline

Prior source checkpoint `2df88c4c6c6fbee8e2e59433efa3148c48fe662b`
passed 1,150 Python tests on 3.10, 3.11 and 3.12 but **Product CI
failed** its frozen-source check. This is not post-versioning evidence.
The new [dedicated workflow](../.github/workflows/finisher-versioned-v2.yml)
runs a separate historical-pristine offline replay, focused V2 tests on all
three Pythons, and real `windows-latest` locking/crash tests. Existing
[CI](../.github/workflows/ci.yml) and [Product CI](../.github/workflows/product-ci.yml)
now exercise the unchanged checkout directly, without modifying or patching V1.
Fresh final-commit links and exact counts must be added **after** each runner
actually completes; don't present queued or cancelled earlier runs as green.

The root license was already changed to Apache-2.0 on the inspected main
baseline. No license edit is part of this PR. Individually marked
third-party resources retain separate rights. Scientific framing remains
bounded by [claim boundaries](CLAIM_BOUNDARIES.md) and
[scientific boundaries](SCIENTIFIC_BOUNDARIES.md).
