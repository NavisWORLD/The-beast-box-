# ZEREF EXPERIMENT 006 — Resumable native RAWRPHØS learning heartbeat

## Exact authorization and cadence

Owner requested continuing real, interrupted/resumable RAWRPHØS training from the unexpected Experiment 005 live emulator evidence, without silently stopping. This implementation runs an initial PR-gated cycle and, **only after the PR merges onto default main**, a GitHub scheduled cycle every 6 hours at minute 17 UTC. GitHub schedule is best-effort and depends on repository Actions being enabled and runner availability. It is not an always-running background process.

**Each run is strictly bounded:** 56 new real native Lost COSMOS emulator observations, a distinct scripted-observation-conditioned training trajectory, **64 fresh CPU AdamW optimizer updates**, one heldout independent native episode, language retention checks, 65-minute job timeout, two attempts at most for a transient browser capture failure. The experiment hard caps at 64 approved cycles (4,096 additional optimizer steps) pending explicit owner renewal. This is a cloud cost and uncontrolled-overfitting safety boundary; a stopped cycle does not discard the previously approved model.

## Starting evidence

- Original model RAWRPHØS 14K checkpoint SHA:
  \`4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5\`.
- Initial approved Zeref Experiment 004 native 128-step child SHA:
  \`86d9084ee3d302fdf37980e89eef60c86be90bc4538f0bfc9e7c3b39db92fcc8\`.
- Original unmodified IBM Fez source \`db4q484vf2bc73cuuuag\`; measured Zeref identity \`bb-deada969\`; original seed \`8e2e927e2cfaf489cb7c10172836286bb08869cfff0c2508b5c6371e052e54ed\`.
- Experiment 005 established live game-controller competence: trained model 36/36 valid actions + ACKs, original model 0/36; **game reward, map completion, dialogue and earned progression still not instrumented**.
- **NO fresh IBM hardware or Azure QVM workloads** in 006; classical learning does not count as quantum model training.

## Lineage correction from the immediate 010 experiment

The first PR #286 immediate CPU cycle from GitHub Actions run `38158726567` genuinely collected 56 new native observations and performed 64 optimizer updates, but its artifact query scanned only the newest 100 unrelated repository artifacts. The original accepted 006 child fell outside that page, and the run **incorrectly bootstrapped from the older 004 candidate** `86d9084ee3d302fdf37980e89eef60c86be90bc4538f0bfc9e7c3b39db92fcc8` as a separate valid training *fork*. It created SHA `409f85256825d0009c3c122b3b411e18018c3233518ebb2c6c7873d86ad27887`. The data and checkpoint remain honest exploratory evidence but are **NOT part of the canonical 006 optimizer continuation**. No real learning or owner experiment history is discarded.

The workflow was amended to query a fixed exact canonical artifact name and fail closed on incompatible parent hashes. The rooted continuation resumes **the actual approved 006 192-step parent**, not the separate fork. This rule also applies to the six-hour recurring workflow once this fix merges.

## How continuations work

A job now resumes **only descendants of the independently approved Experiment 006 checkpoint**, SHA `37ca3f8fc9cdc0e78175508fc816ed02d5a12da1f3b106505715b7366fde5a48` (original accepted artifact, Actions run `38129248023`). Newly approved descendants publish under the EXACT GitHub artifact name `zeref-006-canonical-37ca3f8f`; the GitHub API is queried by that exact name, not an unsafe latest-100-artifacts prefix scan. The complete file manifest, model SHA, approval receipt, canonical ancestor SHA and actual saved optimizer moments must validate before optimizer work. If no descendant exists, download the original approved 006 checkpoint. **Never restart from 004, from a sibling fork, random weights or an unknown old artifact.**

The original, previous and rejected candidate checkpoints never overwrite each other. Every cycle captures **new actual framebuffer values and native controller ACKs** from the original ROM. GitHub run ID rotates the *explicit scripted teacher* fallback sequence only; this is NOT reinforcement learning, a human demonstration, or evidence of semantic vision.

Heldout episode #3 remains excluded from gradient updates. Model parent-versus-candidate heldout literal generations, legal command rate, teacher match, actual heldout negative log likelihood and basic conversational retention are rechecked. A child becomes the **next training parent only** if all predeclared gates pass. Failure or regression uploads a truthful report and preserves the last approved checkpoint for the next six-hour scheduled cycle.

**NO automatic public production model promotion, GBA cartridge replacement, new quantum measurement, user surveillance, keeper microphone capture, or covert collection.** Training is only original public native emulator display + scripted legal game actions. It does not imitate the user's personal speech without specific opt-in.

## Interruption, monitoring and boundaries

- When cloud runners are unavailable, schedule can be delayed; the next scheduled run restarts from the last accepted checkpoint.
- If a real browser capture crashes, the run retries once, with the same signed Zeref identity.
- If training fails, the latest accepted artifact remains untouched; the next cycle starts from it.
- Missing or expired checkpoint artifact is a **blocking incident**. It never regenerates fake previous weights or silently promotes a model.
- Reports and accepted checkpoints use 90-day artifact retention where allowed by the repository. If this limit is shorter or artifact expiration approaches, migrate approved checkpoints to owner-controlled durable storage under a separately authorized workflow; do not pretend artifact storage is indefinite.
- Job scheduling can consume GitHub Actions minutes and storage. The owner may pause it in GitHub Actions by disabling the "Zeref 006" workflow.
- Progress is measured honestly: legal actions and copying scripted teacher are not equivalent to independent navigation or increased intelligence. For those claims, future cartridge instrumentation must expose real objectives, coordinates and dialogue events.

## Implementation

- \`apps/beastbox-cloud/tests/rawrphos-native-observed-play.cjs\` adds per-cycle optional seed variety to the existing audited capture.
- \`scripts/zeref_continuation_006.py\` resumes saved actual model **and optimizer state** while enforcing parent integrity, new optical capture, heldout+retention acceptance and no release.
- \`.github/workflows/zeref-continuous-learning-006.yml\` gives continuous scheduled + manual + PR audit functionality.
- \`tests/zeref_continuation_006_contract.test.cjs\` protects invariants.

### Acceptance standard

Require a passing real GitHub Actions 006 run with actual 56 observation/ACK evidence, exact candidate parent SHA, 64 optimizer steps, source/candidate SHA, literal heldout replies, approval/rejection clearly labeled, and artifact uploader receipt. Do not claim the scheduled cadence operational until workflow merges into the default branch. Do not deploy the experimental model automatically.
