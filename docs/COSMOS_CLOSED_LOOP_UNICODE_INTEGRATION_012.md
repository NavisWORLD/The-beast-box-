# COSMOS 012 — CONNECT THE WIRES, NO MORE FALSE FULL-SYSTEM BENCHMARKS

**Owner:** Cory Davis / NavisWORLD. **Scope:** real existing public `DurableRuntime` software integration, optional reviewed-feedback route, Unicode-safe Python host transport. **Not** a native model retrain, physical instrument receipt, model-tokenizer vocabulary upgrade, live sensor hardware deployment or scientific benefit claim.

Prior research established a concrete gap: the actual durable CNS updated its dyn12 on each conversation turn but never advanced the persisted R12 software state. Experiment 009 used an isolated adapter with a fixed all-zero dyn12, initial R12 `reality_coupling=0`, unrelated feedback training, and an oracle generator that failed the original combined arithmetic task. Rather than endlessly modifying performance tests, this change **wires the production host's real connected software path and provides a finite integration finish line**. Original measured nulls remain in PR #158 and original 011 diagnostic/isolated repair remain in PR #159; neither is rewritten or cherry-picked.

## Actual end-to-end stage ordering (single trusted host / one durable checkpoint)

`sensor-event-v1 {source,text,features}` → validated UTF-8 and optional lossless **NFC** → existing bounded BridgePacket numeric features → existing SYNAPSE dyn12/dyn42/dyn54 and CNS.tick (live state) → **host-created verified hash-bound nonphysical R12 software transition** → existing R12 router using CURRENT post-CNS dyn12 and the CURRENT R12 sequence + same immutable active-memory snapshot → optionally **host-reviewed** product AdaptiveControl weights re-rank the router's original five actual score components on every active candidate → optionally existing offline embedding fusion → selected actual context → replaceable local/provider interface → existing authorization and purely simulated tools only → user/assistant durable memory + Hebbian associations + slow organism/monologue + provenance receipt → existing single-writer continuity checkpoint + anchor/rollback ↺.

The old default is unchanged: `DurableRuntime(root)` remains historical behavior. Enable the connected software path from trusted host Python only:

```python
from beastbox.durable import DurableRuntime

runtime = DurableRuntime(
    "/owner/verified-runtime-root",
    provider=existing_host_selected_provider,
    closed_loop=True,   # Explicit host opt-in to nonphysical per-turn R12 state.
    unicode_mode=True,  # Preserve Unicode NFC instead of historical NFKC folding.
)
# After storing real owner-approved memories and obtaining honestly reviewed labels:
receipt = runtime.apply_reviewed_feedback([
    {"query": "first relevant query", "preferred_memory_id": approved_id_1, "reviewed": True},
    {"query": "second relevant query", "preferred_memory_id": approved_id_2, "reviewed": True},
])
# Subsequent turns now use the reviewed weights in the SAME real route.
# A fresh process also needs closed_loop=True and unicode_mode=True; it restores
# only previously hash-verified host-reviewed weights from durable history.
```

## Actually connected owner service entrypoints

The same opt-in flags are now threaded into **all existing authenticated service readers and writers**: `OwnerBridge` trusted environment → `CosmicApp._runtime` real chat → `ProductService` orbit/memory/conversation/trace readers → owner-approved device-observation persistence → bounded `OwnerMemoryLoop` maintenance. These previously separate short-lived `DurableRuntime(root)` openers must agree on one verified persisted profile; a misconfigured restart fails closed rather than silently taking down every owner read endpoint.

The authenticated owner dashboard's `GET /api/orbit` now includes a hash-only `runtime.wiring` block for `closed_loop`, `unicode_nfc`, reviewed routing availability, persisted software R12 sequence/state hash and explicit no-physical-measurement/no-model-authority claims.

For *new or isolated copied* owner substrate instances, set the host-only configuration (never browser JSON, provider output or public visitor parameters):

```shell
BEASTBOX_CLOSED_LOOP_ENABLED=yes
BEASTBOX_UNICODE_NFC_ENABLED=yes
```

Flags are intentionally empty in `.env.example` to satisfy credential-safe CI inventory; unset/empty values are interpreted as `no` in owner runtime host configuration. On an existing real owner production database, first verify source backups and recovery on a separate copy and ensure **every** owner bridge, reader and optional background index loop uses identical flags before opt-in; after the first upgraded checkpoint, accidental flag removal intentionally fails closed. Do not flip production blindly during a normal Git deploy.

The original RAWRPHØS native tokenizer is **byte-level BPE**, with a separately tested Unicode byte transport roundtrip; this proves tokenization fidelity but not multilingual model instruction performance or unbounded context. Existing original PHOS/SAMGO character models retain whatever smaller vocabulary their checkpoint actually supports; no checkpoint or tokenizer is silently replaced.

**Review is a trusted-host assertion, not a cryptographically verified human review.** No model output automatically updates the weights. All numerical weights must come through a validated original `AdaptiveControl.fit` receipt or that actual product `apply_reviewed_feedback` API. Learned weights are host-only state persisted in the chain, not model parameters. Use different reviewed training examples from subsequent held-out research evaluation cases.

**Provenance law:** text, synthetic-demo and software-event are at most derived/synthetic *software events*. Nothing in this path automatically accepts purported physical instrument data, labels it measured, grants hardware authority or increases `reality_coupling`. Current R12 geometry uses `reality_coupling` to control actual reflection: for purely software input that coupling rightly remains zero. However its **software state, transition hashes and sequence are now live**, and its query/memory positions consume the current real CNS dyn12 and state sequence. A separate measured-sensor adapter would need strict owner-verified physical provenance before allowing nonzero hardware coupling; software success is not physics verification.

**Unicode law:** Python host, input normalization (opt-in NFC), generated text UTF-8 checks, SQLite memory content, Unicode lexical and Hebbian indexing, R12 lexical relevance, retained model context and restart checks preserve Greek, Arabic, Devanagari, Han, CJK substring keys, accents, emoji with skin tones and ZWJ, and non-BMP code points. The exact original ASCII lexical tokenizer remains fast-path equivalent for existing historical English tests. Unpaired surrogate strings fail closed; owner files are stored in their exact input text bytes without rewriting original content. Index terms are comparison keys, not modifications to source text. This is Unicode-safe *host transport and lexical search*, NOT a claim of perfect segmentation, multilingual semantic comprehension or *full native RAWRPHØS generated-model vocabulary support*. Each model's own tokenizer/output capability remains independently testable; unsupported trained vocab requires a properly trained new checkpoint, not silent character stripping.

**Rollback/continuity law:** all enabled per-turn R12 transition, reviewed routing selection, model response, memory updates and the full hash-linked receipt stay inside the existing atomic SQLite turn transaction and optional external anchor. Provider failure restores the original full checkpoint; failed or malformed reviewed updates are atomic. Changed/disabled host opt-in flags may not silently reinterpret an already upgraded checkpoint: fresh processes must explicitly re-enable the same profile, and previously host-approved weights auto-restore only from a validated continuity checkpoint. The default no-feature owner checkpoint remains compatible and untouched.

## Required acceptance evidence

The focused Python 3.10 / 3.11 / 3.12 CI job runs real original production host tests (not an isolated SimpleNamespace clone), legacy durable/refractive regressions, a fresh-process model-provider replacement, real memory retrieval/feedback against the same active snapshot, source/routing/CNS/transition hash receipts, preserved and archived original Unicode sources, malformed-surrogate rejection, zero fabricated measurement authority, and provider-error/training-error rollback. Generic Product CI, source-pristine checks and security tests must also pass before release.

**Complete-integration limits still to be verified separately:** authenticated live mic/camera transports and their permission controls, every HF/PHOS/SAMGO/Cypher/Luna native-model checkpoint/vocabulary, typed physical hardware measurement provenance, frontend controls, and full production health/load tests. This module does not pretend to connect unavailable hardware or solve failed LLM oracle arithmetic. It connects the verified existing **software** graph, while leaving each extra peripheral/model capability observable and fail-closed.

**No automatic deployment.** Ship this opt-in behavior on reviewed green PR only, then opt the existing owner service into it after a verified fresh-process recovery test on an isolated copy of the real production substrate. Do not overwrite historical frozen architecture, metadata or measured receipts.
