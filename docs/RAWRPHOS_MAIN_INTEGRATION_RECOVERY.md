# RAWRPHØS + latest-main integration — source recovery (NOT A DEPLOYMENT)
Source baseline: `42dd57d67a533bd6264497c54ab5f60535cb4598`
Previously deployed production source: `d1ed41a7dcb7782aa4a9fb8277e4562d7c2189c3`
Branch: `feature/cosmos-rawrphos-unified-runtime-001`

## Stage 1: reversible source recovery, without touching frozen experimental originals
- Preserve latest main's tested `beastbox/durable.py`, semantic retrieval,
  snapshot boundaries, custody limits and release hold. We do not bring
  earlier versions of those modules across from the divergent production tree.
- Recover the deployed RAWRPHØS source, pinned checkpoint installation
  scripts, loopback inference server, rawrphos Dockerfile and startup scripts
  exactly as committed in the previously deployed production source.
- Recover the earlier owner-bridge/model catalog/consent extensions together
  with their necessary module dependencies. Their behavior must be reconciled
  against latest main security tests. This is an unverified candidate until CI
  and actual cloud end-to-end tests pass.
- Do not assume the pinned checkpoints are actually downloadable merely
  because the source refers to hashes and installation scripts.
- No live production Railway branch, public Vercel, old production volume,
  persistent owner data or secrets are altered by this branch.
- Work screenshot indicated local patches, public SciFact HTTP 502 and
  auto-review blocked by usage; no unverified local-only changes are claimed
  to be incorporated. Preserve the dataset download failure as a failure.

## Required next measurements before deployment
1. Run existing Product CI and feature-specific old bridge checks on the
   exact new source; fix all regressions (do not relax security guards).
2. Wire host-only opt-in learned embeddings through `CosmicApp._runtime`
   without changing default lexical/R12 behavior or rewriting memory state.
3. Verify actual 14k/18k model source/weights rights, pinned hashes and
   real inference on isolated resources; measure memory and CPU.
4. Confirm archive exclusion, revoked cloud authority, sensor consent,
   model switch and exact persistence across simulated and real restarts.
5. Test matching owner-authenticated Vercel preview + isolated Railway backend
   against disposable credentials, then separately authorize any cutover.

Owner's existing live 500 MB volume remains outside this experiment;
there is no independent trust root or 50k representative evaluation yet.

## Verified source-recovery checkpoints and separated claims
The public pinned 14K release tag
`rawrphos-native-conversation-step-00014000-run-35951509482`
has an uploaded 43,434,030-byte archive and a source-pinned SHA-256 in
`models/rawrphos/scripts/install_pinned_14k.py`. Release availability
does NOT prove a new download or live 14K generation for this branch.

The public 18K research release tag
`rawrphos-native-experimental-inference-step-00018000-run-36008364848`
has a separate uploaded 43,400,107-byte archive. Its original release
explicitly states the owner-repetition quality gate FAILED (10/11
mechanical checks; unreliable multi-turn results). Do not promote the
18K research candidate to production or confuse artifact integrity with
conversational quality.

The integration's dedicated real CPU workflow may train its own tiny
synthetic model and verify the inference API, but those tests are not
a real pinned 14K/18K production-model benchmark.

## Transient SciFact HTTP 502 recovery
The same baseline source uses at most three transient-download attempts,
or the host can supply `BEASTBOX_SCIFACT_VERIFIED_CACHE` (a local ZIP
path). **Both** the published archive MD5 and SHA-256 previously observed
in `docs/SEMANTIC_REAL_EVAL_001_MACHINE_RECEIPT.json` must match.
Otherwise stop. No synthetic dataset, changed positive query selection,
fabricated repeat result or altered benchmark threshold may replace the
missing public archive. This is transport hardening, NOT a new completed
large-scale model result.
