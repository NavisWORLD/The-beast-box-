# COSMOS Stage 012 — Rigetti free-QVM integration gate and 10K 12D feedback

**Isolated branch:** experiment/rigetti-qvm-12d-feedback-012  
**Parent:** production backend recovery branch at merge d1ed41a7dcb7782aa4a9fb8277e4562d7c2189c3  
**Cost and authority:** zero new Azure provider jobs until independently authorized and authenticated. Zero QPU jobs in all modes. No change to Railway, Vercel, model weights or durable owner memory.

## What has actually executed

A complete zero-provider-network experiment ran on GitHub Actions:
https://github.com/NavisWORLD/The-beast-box-/actions/runs/36211559893

The new runner uses the *existing implementation* of COSMOS source_from_soul_token,
versioned signal_fusion, matched_classical_control, BridgePacket,
CNS7.tick, update_dyn12, and MissionState. It is not a rewritten fake 12D engine.

The **10,000** iterations each independently sample **64** ideal shots from a
two-qubit circuit: RX(theta) on q0; CNOT q0->q1; measure both. This is an ideal
*local classical Monte Carlo* emulator for that circuit. Angles follow a fixed,
predeclared exogenous sweep. The same pre-sampled tape feeds all arms to avoid
misreporting random draws as a behavioral improvement.

There is no physical calibration. The nine source-reported historical IBM Fez
**published summaries** are separately referenced through the current
archive_summary adapter as explicit provenance-bearing contextual state.
They are NOT complete QPU histogram archives, NOT actual Rigetti hardware
measurements, and do not define the ideal-Bell simulation's noise model.
All Monte Carlo shots are novel *synthetic* random draws, not recovered
physical source measurements.

The primary conditioned arm mixes a local ideal-circuit SIMULATION source with
the separately labeled archived IBM-summary source under generic model-control
coordinates C1..C12. The other four arms are zero, first-vector frozen,
a seed-fixed independently time-shuffled tape and a strength-matched classical
signed permutation of the SAME primary vector. Each arm maintains its own
CNS7 and evolving dyn12 state for 10,000 iterations.

## Numerical results — run 36211559893

- 10,000 software simulation iterations, 640,000 synthetic shots total.
- 40 hash-linked snapshots, at increments of 250 iterations.
- All five arms completed. Both the native source-fusion implementation and
  CNS7/dyn12 ticked in the actual repository code. The entire result is
  deterministic for seed 67 and its declared algorithm.
- Final hash chain:
  650fc31ad707fc178551c2432310bde9a0884612f7d77599bdb337a0c31069af
- RMS difference of conditioned 12D software state from each control,
  *not* a model output, accuracy score or experimental advantage:

| Control | 10K state-trajectory RMS separation |
|---|---:|
| All-zero | 0.379091071 |
| Frozen initial control | 0.613306378 |
| Independently time-shuffled data | 0.314564840 |
| Exact-L2-strength-matched signed classical permutation | 0.536818347 |

The nonzero separations mean changing a software control input changes the
software trajectory. None of these measurements proves that the QVM or archive
produces intelligence, quantum advantage, true quantum-derived randomness or
a better language-model answer. No model was called in this phase.

The artifact "cosmos-stage012-local-10k-no-azure-jobs" provides the complete
numerical receipt and a separate dry-run manifest. A subsequent version of the
same workflow additionally prepares an owner-gated *offline only* five-arm
blinded prompt bundle for future cloud-model testing.

## Azure Quantum Rigetti simulator is a separate, gated provider

Microsoft's Azure Quantum documentation identifies the Quil target
\`rigetti.sim.qvm\` as **free**, with actual Rigetti QPUs billed separately.
Only the simulator target is supported by this adapter:
https://learn.microsoft.com/en-us/azure/quantum/backend-simulators
https://learn.microsoft.com/en-us/azure/quantum/azure-quantum-credits

The isolated \`beastbox/rigetti_qvm_adapter.py\` produces a real Quil circuit
and enforces the single exact target \`rigetti.sim.qvm\`. It refuses a QPU
target. Dry-run mode requires NO Azure account and dispatches zero jobs.

The real Azure transport is intentionally fail-closed. An actual QVM job
requires **both**:
1. Authorized Azure Quantum workspace access (not merely Azure Blob Storage);
   four nonsecret workspace location identifiers in the execution environment:
   \`AZURE_QUANTUM_SUBSCRIPTION_ID\`, \`AZURE_QUANTUM_RESOURCE_GROUP\`,
   \`AZURE_QUANTUM_WORKSPACE_NAME\`, \`AZURE_QUANTUM_LOCATION\`, plus valid Azure
   identity in the runner; and
2. A separate explicit \`AZURE_QUANTUM_QVM_OPT_IN=yes\` flag and the explicit
   \`--submit-free-qvm\` CLI switch.

The production connector tools made available to this experiment expose
GitHub and Railway, not an authorized Azure Quantum workspace/session.
No Azure Quantum credential or workspace identity was retrieved from Railway
service variable names. Therefore this experiment **does not assert that
actual Azure-hosted QVM jobs have run**. No provider job, paid QPU job,
new live sensor read or cloud LLM inference was started.

An authenticated smoke will use a *single* bounded job, default **32 shots**
and RX(pi/3)+CNOT. It must verify the exact target, output format, count total
and returned Azure job identifier. It must fail closed (no retries, no
auto-target selection or fallback). There is no 10K Azure job dispatcher yet.
An unbounded "infinite" provider loop is prohibited; provider quotas,
Azure account costs, storage costs and cloud-model bills remain separate.

## Model comparison is prepared but NOT run

\`beastbox/qvm_cloud_context.py\` generates offline, bounded, deterministic
blinded contexts from the experiment receipt ONLY after explicit
\`--owner-approves-offline-preparation\`. It produces five equal-question
prompts: no context, common archive-labeled observations, full 12D state,
time-shuffled-state context, and norm-matched classical state.
The blinding key is stored under a clearly marked owner-private receipt field
and must **never** be sent to the evaluated model.

Prompts are data only. They grant no provider access, model authority,
memory writes or sensor permissions. All arms must use the SAME selected
cloud-model version and generation settings. Independent evaluations must
measure whether relevant, correctly sourced answers improve, not simply
whether logits or software states differ. The no-context and context arms
differ in information availability; only the state-conditioned versus
state-control comparisons help isolate the extra 12D control contribution.
An owner-approved remote-model test will require separate provider
credentials, a bounded token budget, explicit cost consent and independent
result receipts.

## Acceptance and promotion checklist

- [x] New isolated branch; no production mutation.
- [x] Source lineage from existing nine IBM Fez published summaries.
- [x] True existing COSMOS source fusion and CNS7 over 10K local ideal-circuit iterations.
- [x] Fixed-seed exogenous observation tape and zero/frozen/shuffled/classical controls.
- [x] Hash-chained execution receipt with checkpoint state and provenance.
- [x] Strict target-allowlisted Azure Rigetti QVM adapter and dry run.
- [ ] Actual Azure Quantum workspace connection validated.
- [ ] Single genuine **Azure QVM** smoke (simulated cloud execution only), returned job receipt.
- [ ] Honest replay of multiple QVM executions with bounded quotas if useful.
- [ ] Owner-approved cloud-model comparison with blinded, fixed-budget tasks.
- [ ] Evidence of model/task benefit relative to matched controls, if any.

**Immutable historical boundary:** August 29 original preregistered scientific
closure remains unchanged. This is a NEW software integration and simulation
experiment using a new contract; these results cannot be backfilled as
previously preregistered real hardware evidence.


## Stage 012B: Real free QVM GitHub owner handoff (prepared, not yet submitted)

The real authenticated free simulator runner has been implemented on this
isolated branch, separate from the 10K local classical experiment.

**Secrets URL:**
https://github.com/NavisWORLD/The-beast-box-/settings/secrets/actions

1. Open the owner's **Azure Quantum workspace**, **Operations > Access Keys**.
   Prefer a secondary workspace key, not the account's general-purpose primary
   secret. Copy the **entire Azure Quantum workspace connection string**.
   A raw key alone, Azure Blob storage string, IBM token, or generic Azure
   subscription token is not equivalent.
2. In GitHub, **Settings > Secrets and variables > Actions > New repository
   secret**, create EXACTLY: \`AZURE_QUANTUM_CONNECTION_STRING\`. Paste the full
   Azure Quantum string there. Never put it in a repository file, PR comment,
   GitHub issue, model prompt, chat message or CI artifact.
3. Tell the engineer that GitHub secret setup is complete **without revealing
   the secret value**. Repository Actions secrets cannot be read back from
   GitHub after saving; workflow results safely report whether login worked.
4. The engineer changes only
   \`experiments/stage012/azure-qvm-run-request.txt\`, which triggers
   [azure-rigetti-qvm-free-012.yml](../.github/workflows/azure-rigetti-qvm-free-012.yml)
   once on this isolated branch. No normal code push, secret update or local
   simulation automatically starts an authenticated provider job.
5. The authorized workflow keeps the secret in the submission step only,
   validates the current official \`qdk[azure]\` imports, and issues a maximum
   of **three sequential simulator jobs** with **32 shots each** at exactly
   \`rigetti.sim.qvm\`, using independently specified circuit angles.
   Each successful job receives a distinct cloud job ID, counts and public
   Quil program hash in its sanitizer-only JSON artifact. It performs no
   cloud-language-model inference and does not touch Production.
6. There is no automatic retry, target fallback or paid-QPU selection.
   If the workspace does not have Rigetti enabled or the simulator is
   unavailable, the workflow aborts and reports the authentication or provider
   failure without a fabricated receipt. Successful partial receipts are
   preserved if a later job fails.

**Cost boundary:** Microsoft labels the Rigetti QVM simulator *free at the
provider target*, not unlimited free GitHub compute, Azure account/storage or
other Azure resources. The first approved request is bounded to three jobs,
96 simulated shots combined. No open-ended polling/iteration is enabled.

**CI preflight** is a separate zero-Azure-credentials job:
[official SDK and no-credential tests](../.github/workflows/azure-rigetti-sdk-preflight-012.yml).
It verifies SDK imports, the strict backend allowlist and fail-closed tests.
Neither preflight nor the 10K local experiment is evidence that an actual
Azure-hosted QVM job has been submitted; only the new authenticated workflow
can generate such receipts.

For lower-risk long-term CI access, a narrowly scoped Azure service principal
with the \`Quantum Workspace Data Contributor\` role and GitHub OIDC
federation should replace direct workspace access keys if available. Keep
the connection string private and rotate/revoke it after use if no longer
needed.
