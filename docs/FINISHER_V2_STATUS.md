# Finisher V2 — evidence-led implementation and release hold

**Repository / merged V2 foundation:** [NavisWORLD/The-beast-box- #129](https://github.com/NavisWORLD/The-beast-box-/pull/129), merged as `2c75784ff72161fb592ffe81e2e68dc5cbe38077` on 2026-09-27. **Continuing full program:** [A–G gate issue #132](https://github.com/NavisWORLD/The-beast-box-/issues/132) and [opt-in authenticated HTTPS authority PR #133](https://github.com/NavisWORLD/The-beast-box-/pull/133).
**Initial main baseline:** `4c4e4d38e645ee521534643d42843e181be4900a`.
**Prior corrected-code checkpoint:** `2df88c4c6c6fbee8e2e59433efa3148c48fe662b`.
**Recovered concurrent branch checkpoint:** `2b0576475779cfb4c53c241f808486b6042be670`.
**Branch:** `feature/beastbox-finisher-v2-001`.
**Verified implementation checkpoint (all three workflow families):** `f3549d78bc96db70edd5ac714cb7db9c37fb37f1` (Linux full Product CI 1,166 on each 3.10/3.11/3.12, V1 fixture replay, actual Windows V2). **Later edits to documents/CI metadata:** validate the actual new branch HEAD before any merge-readiness assertion; changing documentation does not alter this earlier run's identity.
**Owner decision:** [final Option 1: separate V1/V2 source](FINISHER_V2_FROZEN_SOURCE_DECISION.md). Interim patch-overlay commits are retained in branch history, **not** an active build architecture. **New owner authorization:** merge the tested Finisher V2 foundation once checks and no-production-deployment guard pass; this authorization does not make incomplete A–G phases or an unprovisioned external trust authority "done." Public release, production deployment, paid cloud work and licensing changes remain outside this merge.

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

## Expanded execution evidence — exact code checkpoint 2026-09-27

**Commit:** `a27d12206e49cc4816aa18083c8e1e2cf49e80fb`. On this exact source:
[combined Product CI](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36332862492)
**success** on Python 3.10, 3.11 and 3.12: **1,191 passing tests on each**,
68% whole-repository measured coverage in the full quality run, architecture
acceptance `passed: true`, security audit 0 errors / 0 warnings, unchanged
historical sealed guard, clean package smoke and browser integration.
[Repository CI](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36332862444)
**success** (full 3.10/3.12 matrix), and
[historical/V2/Windows suite](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36332862474)
**success** across all five jobs, including actual Windows 3.12, historical V1
offline replay, Linux V2 and optional product-anchor regression tests.

**New active product safeguards:** `beastbox/trusted_anchor.py` defines an
optional monotonic, external-checkpoint-authority protocol and a SQLite
reference backend. `DurableRuntime(anchor_authority=...)` refuses unanchored
existing-store enrollment, compares exact system identity/tip/sequence/memory
digest across restart and on each operation, and stops after an external
publication failure until independent operator reconciliation. Regression
tests exercise coherent local database rollback, process restart, stale CAS,
outage, and path separation. **This does not deploy an authenticated outside
authority:** the SQLite reference, when hosted by the same writable principal,
does not protect against an attacker who rewrites both databases. Default
installs remain explicitly `unanchored`. See [trusted anchor contract](TRUSTED_ANCHOR.md).

**New Phase B scope:** active product pre-CNS lexical retrieval and unchanged
historical R12 scoring now share a *single materialized SQLite record read*
through a read-only SQL adapter. Controlled tests compare lexical and R12
scores with unoptimized original semantics; the runtime benchmark was updated
to measure the actual optimized lexical hook. This is **not** learned
embeddings, held-out semantic quality validation or proof of lower end-to-end
latency at 5k/50k retained records.

**New Phase C scope:** explicit host-reviewed, reversible archive/restore
updates original memory metadata without deleting source text; archive is
excluded from active lexical and R12 product retrieval. Reviewed contradiction
links retain both originals and checkpoint the provenance. Full lifecycle
policies, evidence adjudication and a 10k-turn long-running soak remain open.

**New Phase D scope:** `ScopedMaintenance` supports only inspect, archive,
restore and explicitly reviewed contradiction actions. It defaults to denial;
a host-supplied *independent* approval callback can mint exact-plan,
single-use, short-lived, revocable grants. Grants are invalidated after provider
swaps and are not serialized across restart. This is a bounded host API
prototype, **not** a background autonomous agent or a substitute for actual
owner authentication, persistent denial logs, preemption, sandboxed tools or
cross-process authorization auditing.

## Latest complete Finisher A–G engineering test checkpoint (2026-09-27)

**Exact tested code commit:** `cd9b05a3fb6a91b52a599644b82f79ad2fa47465`.
[Combined Product CI](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36333761776)
**SUCCESS:** **1,212 tests passed on each of Python 3.10, 3.11 and 3.12**,
68% measured repository-wide test coverage, original historical guard pass,
architecture acceptance pass, security audit 0 errors/0 warnings, package
smoke and actual browser checks passed.
[Repository CI](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36333761769)
**SUCCESS:** 3.10/3.12 full-suite and quality/package-smoke jobs.
[Dedicated historical/V2/Windows and scale workflow](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36333761933)
**SUCCESS:** original untouched historical source guard and verified offline
fixture replay, focused V2 Python 3.10/3.11/3.12 and actual Windows 3.12
tests, and newly added isolated 10,000-record retention-scale job.

The 10k scale artifact classifies its inputs as **derived-synthetic**:
it created 10,000 retained memory rows, checkpointed 500-row SQLite batches,
executed one real product turn, archived/restored one original and reopened
the product under a different reference provider while verifying exact
checkpoint and memory digest. It **did not** perform a 10k-turn interactive
endurance soak. On the recorded Actions environment, seeding measured
approximately 5.55 seconds, reversible lifecycle 0.95 seconds, and the
single 10k-corpus turn 1.53 seconds. These are one observed environment,
not platform-independent latency limits, a benchmark comparison to V1, or
evidence of real-model performance.

**Phase E controlled software feedback:** the
[isolated reviewed-feedback adaptive controller](../beastbox/adaptive_control.py)
can reweight existing frozen R12 score components using training-only
reviewed examples; [negative-control tests](../tests/test_finisher_adaptive_control.py)
reject train/evaluation query leakage and compare frozen/adaptive MRR on
separate synthetic held-out inputs. Neither model weights nor original
historical R12 source change. These tiny fixtures do not establish any
real-world performance improvement or complete Phase E evaluation. See the
[protocol](ADAPTIVE_ROUTING_PROTOCOL.md).

**Phase F configured routing:** the [host-authorized model router](../beastbox/model_router.py)
explicitly selects labeled provider/capability pairs, keeps the same product
memory/state/authority outside replaceable inference, revokes grants on every
swap and refuses failed-provider and missing-capability fallback.
[Regression evidence](../tests/test_finisher_model_router.py) includes
one **reference-provider software A→B→A control**, swapped-host approval
revocation and deceptive model-output denial. No provider weight identity
was attested and this was **not** a new multi-real-neural-model comparison.
See [configured routing scope](MODEL_ROUTING_SCOPE.md).

**Phase G narrow offline compatibility:** the
[adapter smoke tests](../tests/test_finisher_ecosystem_smoke.py) exercise
owner-supplied software light-feature summary → validated
`sensor-event-v1` → actual durable CNS/state/continuity turn → approved
reference-provider route swap, verify rejection of out-of-range inputs
and safe missing-cloud credentials. This is **not** validation of live
phone bio/camera/mic, paid hardware, current RAWRPHØS weights, Synapse OS
boot or live fruit-fly data.

**Progress compared to frozen-source milestone:** the originally sealed V1
research files are still byte-identical to their historical anchor and the
unaltered guard passes. All A–G **have some implementation or evidence**, but
none meets the original unconstrained Finisher final acceptance: independent
authenticated anchor custody, large-corpus held-out semantic/adaptive tests,
full conversation soak, production owner-authenticated autonomous execution,
measured real two-model capability routing and live external ecosystem
integrations remain open. Do not automatically merge or release.

## Finisher phases (only evidence-backed state)

| Phase | Status | Evidence / still required |
| --- | --- | --- |
| A — Security and recovery | **in progress** | [Original sealed/V2/Windows/10k run](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36333761933), [full Product CI](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36333761776). Separately versioned V2 corrections, strict optional [product CAS authority](TRUSTED_ANCHOR.md), rollback/outage/restart tests passed. Independently administered authenticated off-writer authority and extended fault matrix not deployed/proven. |
| B — Semantic retrieval | **in progress** | [Shared immutable per-turn product snapshot](../beastbox/retrieval_snapshot.py) and frozen R12 parity tested, corrected [measurement harness](../scripts/benchmark_runtime.py), observed single turn with 10k synthetic rows. No learned embedding adapter, held-out real relevance evidence, replicated 5k/50k latency evaluation. |
| C — Memory lifecycle | **in progress** | Reversible reviewed archive/restore and human-reviewed contradiction link checkpoints [tested](../tests/test_finisher_memory_lifecycle.py); 10,000 synthetic rows + real single turn + reopen + archived scale receipt [passed](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36333761933). NOT a 10k-turn soak; no owner-approved forgetting/retention or full source archival policy. |
| D — Agency | **in progress** | Default-deny [finite scoped maintenance host API](../beastbox/scoped_maintenance.py), bounded one-use expiring grants, revoke/swap/restart denial [regressions](../tests/test_finisher_scoped_maintenance.py) pass. No deployed independent owner-authentication service, long-running agent, full real tool-authority review or durable grant audit. |
| E — Adaptation | **in progress** | New opt-in [reviewed pairwise feature-weight control](../beastbox/adaptive_control.py) + [disjoint synthetic held-out comparator](../tests/test_finisher_adaptive_control.py) pass. Baseline/feedback/shuffled/zero-state on representative real corpora and externally preregistered measured advantage remain unproven; no neural training. |
| F — Multi-model routing | **in progress** | [Host-selected capability router](../beastbox/model_router.py) and [reference-provider A→B→A/no-fallback tests](../tests/test_finisher_model_router.py) pass while preserving one persistent runtime and revoking tools. Does not attest real checkpoints or measure real two-model capability routing. |
| G — Ecosystem reconciliation | **in progress** | [Matrix](FINISHER_V2_ECOSYSTEM_MATRIX.md) + [offline sensor→CNS→durable→provider compatibility smoke](../tests/test_finisher_ecosystem_smoke.py) pass. Real device, current RAWRPHØS weight integration, fruit-fly dataset, live quantum and Synapse OS compatibility still externally untested. |

## Milestone 1 — frozen-source architectural blocker

- [x] Final owner selection documented: versioned V1 / separate secure V2.
- [x] Three changed historical paths restored verbatim to historical Git blobs; existing guard script untouched.
- [x] Prior V2 A1–A4 corrections relocated to separate modules with explicit V2 dependencies.
- [x] Versioning docs, canonical manifest and tamper-verifier committed, with negative tests.
- [x] Unchanged historical guard passed at code-verified commit `f3549d78bc96db70edd5ac714cb7db9c37fb37f1`: [dedicated historical workflow](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36330659101), [Product CI](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36330659080). Any later documentation-only commit needs a fresh final-head rerun before merge consideration.
- [x] Original V1 deterministic offline reproduction independently passed at tested commit `f3549d78` and its witness hashes, version-verification receipt and offline evidence were archived by the [dedicated workflow](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36330659101). **Scope:** frozen deterministic offline fixture, not re-execution of historically measured externally dependent real models/hardware.
- [x] Focused V2 source integrity, bad-manifest rejection, no-V1-security-fallback, cross-process writers, crash/recovery outbox, independent *caller-supplied* receipt rejection after subprocess restart, and immutable-input regressions passed on Linux 3.10/3.11/3.12 and actual Windows 3.12 at `f3549d78` ([dedicated workflow](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36330659101)). **Not covered:** an installed independently authenticated persistent receipt service or a comprehensive cross-host/filesystem/hardware-fault matrix; these remain Phase A release blockers.
- [x] Fresh **combined** [Product CI](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36330659080) green at tested code commit `f3549d78`: **1,166 passed each** on Python 3.10, 3.11 and 3.12, architecture acceptance `passed: true`, security audit 0 errors/0 warnings, original frozen guard pass, package and real browser jobs pass. [Repository CI](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36330659180) green at the same commit. Final doc-only HEAD still requires a fresh full run.

**Updated tested implementation checkpoint:** [a27d1220 combined Product CI](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36332862492), [repository CI](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36332862444), [historical/V2/Windows](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36332862474) all green at the same exact code SHA, with **1,191 passing tests each supported Python** in Product CI. This documents the architectural frozen-source conflict resolution; it does not close the remaining independent authority or full Finisher gates. Subsequent documentation/test-matrix commits require their own exact-HEAD verification.

**Latest exact tested code milestone:** [Product CI 36333761776](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36333761776), [CI 36333761769](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36333761769), and [historical/V2/Windows/10k 36333761933](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36333761933) all completed **successfully** on `cd9b05a3fb6a91b52a599644b82f79ad2fa47465`. The original frozen-source architectural conflict and reproducible offline model-swap fixture are verified. Documentation and expanded contract-test workflow changes committed *after* this code SHA require their own final-head checks, and do not imply all Phase A–G functionality is ready.

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
Three completed workflow runs at exact code checkpoint `f3549d78bc96db70edd5ac714cb7db9c37fb37f1`: [historical/V2/Windows](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36330659101) **success**, [Product CI](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36330659080) **success** (1,166 passing tests per supported Python), and [repository CI](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36330659180) **success**. These are post-versioning test measurements. Subsequent documentary commits require their own exact-head run to call the **new** overall branch tip verified.

The root license was already Apache-2.0 at the inspected main
baseline. [License history](../LICENSE_HISTORY.md) was corrected to describe that existing adoption accurately, not to alter rights. No root license edit is part of this PR. Individually marked
third-party resources retain separate rights. Scientific framing remains
bounded by [claim boundaries](CLAIM_BOUNDARIES.md) and
[scientific boundaries](SCIENTIFIC_BOUNDARIES.md).

## Merge boundary and production safety

See [MERGE_SCOPE.md](MERGE_SCOPE.md). Vercel Git auto-deployment for `main` is deliberately set to `false` in `apps/beastbox-cloud/vercel.json` before any merge into the default branch; the Railway production service was inspected on 2026-09-27 and tracks `feature/cosmos-world-interface-recovery-001`, not `main`. This configuration blocks the known automatic Vercel main-branch path; external integrations or independently configured deploy hooks must be checked separately. Re-enabling production deployment requires separate explicit owner permission.

## Post-merge Phase A HTTPS protocol (draft follow-on)

[PR #133](https://github.com/NavisWORLD/The-beast-box-/pull/133) implements the optional CA-verified remote monotonic witness client and a distinct TLS server process with bounded request/response parsing and separate local witness storage. [REMOTE_ANCHOR.md](REMOTE_ANCHOR.md) specifies separate OS principal/host/private keys and safe enrollment. CI fixtures run the server in an **ephemeral subprocess under the same CI principal**, so even fully green Linux/Windows results are protocol correctness, **not production independently administered authority**, off-host backup verification or completion of Phase A. Live operator provisioning requires separate owner authorization and real evidence. The V1 historical sealed guard and original measurements remain unchanged.
