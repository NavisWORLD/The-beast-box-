# Zeref cloud verification — 2026-10-12

Baseline: `4da4b953c4b9761cce1a7ada05d3908dce4f598e` (`main`). Checks were read-only except local HTTP stand-ins for the isolated Blob probe. No IBM, Azure Quantum or model job was submitted by this audit. No live provider configuration was changed. Credential values were neither fetched nor printed.

## Observed integration status

| Integration | Evidence | Result and limit |
| --- | --- | --- |
| Production app / Azure Blob | Live HTTPS GET `/api/cosmos/beasts` and `/api/cosmos/beasts/bb-7f9c2a03` on `https://www.beastboxcosmos.xyz`, both HTTP 200 | Both returned `configured:false`. The production app did not see a usable storage configuration at observation time. This says nothing about a SAS saved for another environment or a newer undeployed configuration. |
| Historical IBM physical QPU sources | 15 shipped `public/spark/ibm-*.json` files, 30 compact count rows, and successful source workflow run 38029814847 | Every public row passed bit-width, nonnegative integer count, shot-total and SHA-256 validation. These are retained hardware-source records, not new measurements or a fresh authenticated IBM job-status query. |
| Azure Quantum Rigetti QVM | Data-only `zeref-diary` branch, manual workflow run 38186869966 | Tick 1 contains an actual retained QVM job ID, 256 shots and a verified count digest. The target is exactly `rigetti.sim.qvm`, explicitly simulated. No current provider credential was available locally for a fresh query. |
| Per-creature folders and diary | `cosmos-store.mjs`, `zeref-diary-loop.yml`, 15 existing learner/seed/store tests | The implementation stores isolated beast profiles/state/diaries and round-robin receipts; tests verify create-only identity, chain integrity and honest failure fallback. Live storage-backed folders were not verified because the public app reports unconfigured. |
| Scheduled diary | Main declares cron `7,37 * * * *`; the observed first tick came from `workflow_dispatch` | The manual tick and hash chain are verified. Automatic repeated diary execution is not verified; the sampled scheduled-run collection did not show a diary run. |
| Scheduled RAWRPHOS training | `zeref-continuous-learning-006.yml`, schedule run 38179059173 | A scheduled run completed successfully at 2026-10-11 22:09:45 UTC. The workflow uses GitHub's automatic `github.token`; it does not reference a user provider secret. |
| Railway RAWRPHOS host | Service inventory, startup logs and live `/healthz` | Production deployment is `SUCCESS`; startup logs verify pinned native 14K and separate unpromoted 18K on private loopback. Live `/healthz` returned HTTP 200 and `ready:true`. A fresh authenticated model response was not requested by this audit. |
| Scratch-host RAWRPHOS | `beastbox.rawrphos_local.status()` | `AVAILABLE_NOT_INSTALLED`, `configured:false` in this audit's local environment. This does not describe the Railway host. |
| Exact baseline deployment | GitHub commit status and run metadata | Vercel status is `success`, Product CI and CI are completed `success` for exact baseline `4da4b953`. One production recording workflow failed; these statuses do not establish all cloud features are working. |

## IBM and QVM provenance

The Moonwraith companion's recorded origin is `ibm_marrakesh` job `db4te7slf4us73c3888g`. Its shipped two-row subset contains 8,192 shots. The source script records four PUBs and 16,384 shots for the complete job; the smaller public subset must not be reported as the full job. The public shard names source workflow [38029814847](https://github.com/NavisWORLD/The-beast-box-/actions/runs/38029814847), completed successfully on 2026-10-10. The source code requires `simulator=False` and a completed IBM Sampler result, and pins full receipt digests.

Other separately retained sources include `ibm_kingston` job `db4tc8kvf2bc73cv3np0` (Nightcat) and `ibm_fez` job `db4q484vf2bc73cuuuag` (heart-sound). This audit preserves the distinction between these sources. It does not equate a Moonwraith diary identity with the separately trained native-game lineage.

Fourteen shipped Azure count receipts passed SHA-256 and shot-total checks. The companion's new diary tick is separate from those archived receipts:

| Diary field | Verified value |
| --- | --- |
| Workflow | [38186869966](https://github.com/NavisWORLD/The-beast-box-/actions/runs/38186869966), `workflow_dispatch`, completed `success` |
| Tick time | `2026-10-12T00:08:55.270Z` |
| Target / source | `rigetti.sim.qvm` / `rigetti-qvm-simulated` |
| Job | `156654dd-c5d1-11f1-ae67-3833c5dd6293` |
| Counts | `010:8, 100:1, 101:224, 110:23` (256 shots) |
| Counts SHA-256 | `18e01e0ca2e1583da61ee19709712a0663bd172973aa58ed339ed1be881a97ec` |
| Diary head | `a6727f4166052acec9a3a5c70d61123fd318ba8a7406a8eb0032a57576af7533` |
| Thought source | `deterministic-template`; `model-not-configured` |

The fetched `state.json`, `latest.json` and `diary.jsonl` agree. `verifyChain` validates the one-entry chain and its head. The identity matches the recorded genesis exactly. The QVM count hash and shot total were recomputed; diary text was not attributed to RAWRPHOS inference.

## Credential existence and scope

Only names and booleans are reported. Main's diary workflow references `AZURE_QUANTUM_CONNECTION_STRING`, `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_CONTAINER_SAS_URL`, and optional `HFTOKEN`. The successful QVM tick is operational evidence that the Quantum connection worked for that run. It is not evidence of Blob access: the existing Blob mirror script exits successfully when storage is unconfigured, and Azure Quantum's connection string is not automatically a Blob credential.

The GitHub connector does not expose secrets APIs. Local provider environment names were absent; `gh`, `vercel`, `railway`, and `az` were unavailable in PATH, and their checked credential files were absent. Current GitHub secret inventory is therefore not independently readable from this session. The separate training workflow uses an automatically issued GitHub token, and its successful scheduled run demonstrates the artifact/checkout path worked for that run. No provider credential values were requested.

The root agent's Vercel project read failed with HTTP 403, not authorized for team scope `team_j1cniaZln5NJAnnw4wyO4hQD`. This audit did not repeat the unchanged request. The observed production GET `configured:false` is a concrete application finding. Whether a recently saved SAS has the correct name, deployment environment and redeploy cannot be resolved with the current Vercel scope.

Railway's names-only service description contains `RAWRPHOS_LOCAL_ENABLED`, `RAWRPHOS_API_KEY`, and `BEASTBOX_CLOUD_BRIDGE_TOKEN`. Their existence alone does not prove inference; deployment startup logs supply the separate model-load evidence.

## Railway availability

Project `0f127a08-6074-4612-87bb-da8837f28fa1` (Beast Box COSMOS Engine), production environment `44d28bc1-5b3d-4a3a-8bf7-2c2851b3a867`, service `6fcc8ca2-a0c5-49ff-826e-45d6f996fc75` (`cosmos-owner-bridge`) has no staged changes. Deployment `ab9ac5bd-d1a1-46b9-bbce-018b001dfa46` is `SUCCESS`, created 2026-10-10 03:26:37 UTC. Its persistent volume is 500 MB mounted at `/srv/beastbox/data`; the configured build is `Dockerfile.rawrphos`.

Filtered startup logs at 2026-10-10 03:28:58 UTC contain `Verified RAWRPHOS native 14K on private loopback` and `Verified separate unpromoted RAWRPHOS 18K on private loopback`. Current source verifies checkpoint digests `4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5` (14K) and `20932937afb3e0e1b62a4e5f38f92170046ae2928b437dc31b8a37d6538e701e` (18K). The host's public [health endpoint](https://cosmos-owner-bridge-production.up.railway.app/healthz) returned `{"ready":true,"service":"beastbox-owner-bridge"}`. Startup verification and current host health do not attest a fresh model request or model-training improvement.

## Isolated Blob test prepared for authorized execution

`scripts/zeref_cloud_blob_probe.mjs` uses the existing server-only Blob REST client. It accepts only the two existing storage credential names and a valid Azure HTTPS container configuration. SAS mode requires container scope, read plus create/write plus delete permissions, a nonexpired validity interval, and no snapshot/list request parameters. It never creates a container.

The test object name is fixed to `verification/zeref-cloud/<numeric-run-id>-<attempt>/<random-UUID>.json`. Its bytes are synthetic, without creature or owner data. The probe checks absence, uses create-only `If-None-Match:*`, reads and compares exact bytes and SHA-256, then deletes only an exact matching object with `If-Match:<etag>` and reads again to verify absence. An uncertain write acknowledgement is reconciled for cleanup but remains a failed test. A create conflict or foreign replacement is never deleted. Redirects are rejected. Receipts contain credential booleans, test-object path, hashes and sanitized Azure status/code; they exclude credentials and URLs.

`.github/workflows/zeref-cloud-verification.yml` supports manual dispatch and pushes restricted to exactly `feature/zeref-cloud-verification-20261012`, with file-path restrictions. There is no main/PR/schedule trigger, no provider job and no model call. It uploads the sanitized receipt even when blocked or failed. Missing credentials produce `BLOCKED` and a nonzero exit. `CLEANUP_FAILED` requires resolution before claiming a completed cloud test.

The local CLI execution at 2026-10-12 03:55:14 UTC returned `BLOCKED/STORAGE_CREDENTIAL_MISSING`, both credential booleans `false`, and `write.attempted:false`. This is not a live Blob integration pass. Remote execution on the isolated branch had not occurred at the time this report was prepared.

## Validation

- The nine new lifecycle tests were observed failing before implementation, then all passed. They cover credential absence, approval/run-ID gates, unsafe/expired/inadequate SAS, successful cleanup, uncertain acknowledgement, create conflict, foreign replacement, delete rejection, and SharedKey credentials.
- The complete app test command passed: 378 tests, 372 passed, six skipped, zero failed. The first baseline attempt had four missing-dependency failures (`companion-roaming`, `creature-profile`, `meta-muse-e2e`, `meta-muse`); linking the already installed root dependencies resolved those setup failures before the complete passing run.
- The workflow YAML was parsed and checked for its exact branch/manual triggers, read-only repository permissions, protected cleanup concurrency, and two existing storage secret references. Push-trigger inspection found no IBM/QVM/model workflow matching this branch and its changed paths; unrelated package/device build workflows may also run.
- `node --check scripts/zeref_cloud_blob_probe.mjs` and `git diff --check` passed.
- Repository security audit passed with zero errors and zero warnings.

Next verification is the isolated branch run and its sanitized receipt. A passing GitHub Blob probe would establish runner storage access; the production Vercel endpoint must separately return configured storage and successfully read a genuine beast folder before the public integration is called working.
