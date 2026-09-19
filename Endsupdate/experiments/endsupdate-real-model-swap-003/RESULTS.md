# Endsupdate real model swap 003 — executed result

Experiment ID: endsupdate-real-model-swap-003
Execution commit: 747385b03d11c0ed23ec26b11edfaeb0885d277d
GitHub Actions: https://github.com/NavisWORLD/The-beast-box-/actions/runs/35430378553
Classification: COMPLETED_DESCRIPTIVE_MEASUREMENT
Scope: Real frozen-model software-substrate continuity replication; corrected CST physical-energy candidate NOT integrated into dyn12.

## Frozen source and evidence integrity

Preserved Model A archive (artifact 9670847045, run 33132618727) was re-downloaded and its contents verified against the source SHA-256s from the preregistered protocol. Pinned public Model B revision: HuggingFaceTB/SmolLM2-135M@4e53f736cbb20a9a0f56b4c4bf378d9f306ff915. Historical control result from experiment 002 was independently checked as ZIP SHA-256 1ebdf098a542e44eaf54ad9e8fefe3c74fafaeb8c280c41a1369dd58f810fd2d and result SHA-256 0bc2daf23b82d82992412b60c0b03c0cbf520a7e20f1bbb8ded5957c59d26fab. No historical result was modified.

New execution artifact ID: 10580901555, name endsupdate-real-aba-003-evidence-35430378553, ZIP SHA-256 0c41af955419bac062293f17fd3e5e7653f685a254e7ab6bd023fba794692a78.

New result.json SHA-256: f1c4837e6d63da2c19a6cd08446ef33bef27faaf968607da5265d1619efef42c.
New comparison.json SHA-256: bde8d2514e98205838a0100738f2211eb6e0d164d31e1a95fbbbb726fb6eef90.
Raw JSON and sanitized run log are preserved in the Action artifact, not copied into the Git repository or used to rewrite prior evidence.

## Execution and controls

All nine preregistered structural gates: PASS. Actual A0 → B1 → A2 model order executed with one persistent primary substrate. Both cross-swap memory access probes returned true. The canonical memory ledger advanced 352 → 353 → 354 records; state-family step 0 → 1 → 2. Model A loaded parameter SHA-256 at A0 and A2: edf6501633ff26948a73815690e2f184c3e4025414c3ac2d64fbfec203307f7a. Model B loaded parameter SHA-256: 109a74ae153ab55706aa31dcb1ae10f39fb281deea6728a3546b55d6dc0fcbb3. No parameter drift. Six of six frozen A0-to-A2 restoration errors: 0.0.

A-only three-stage, zero-record empty-memory, and deterministically shuffled-memory controls completed. Input-identity hashes matched historical experiment 002, and the original-source-versus-copied Git blob attestation passed. Four comparator negative-control tests passed before inference.

## Actual frozen paired-scoring measurements

The six-case mean preference delta is rejected minus preferred conditional NLL. Different model stages are descriptive and do not establish a CST-mechanism effect.

| Stage | Historical experiment 002 | Fresh Endsupdate 003 | Absolute difference |
|---|---:|---:|---:|
| A0 | -0.23761335668109718 | -0.23761336046551884 | 0.000000003784421665 |
| B1 | 1.121833191977607 | 1.1218328211042616 | 0.000000370873345368 |
| A2 | -0.23761335668109718 | -0.23761336046551884 | 0.000000003784421665 |

The largest absolute per-case difference against historical 002 was 0.0000010331471763 for A0/A2 and 0.00000762939453125 for B1. These small deviations are descriptive numerical/reproducibility differences, not an improvement in task accuracy or loss from corrected CST. New A0 and A2 match each other across all six cases.

## Evidence-bound decision

The new Endsupdate source successfully replicated the frozen real-model continuity experiment. This is a meaningful software-continuity result on main, but it is **not a test of whether corrected CST math improves model performance**, because the corrected physical equation has no demonstrated operational mapping to dyn12 and is not used in the model scorer. Improvement classification: NOT_EVALUABLE_UNTIL_MATCHED_CORRECTED_CST_RUNTIME_ARM_EXISTS. Preserve legacy dyn12, memory formats, model weights and host authority without change. Do not automatically promote the candidate to production.

Remaining unexecuted external gates: matched corrected-vs-legacy operational task-loss/accuracy test; production device/OS sandbox and tool authority; real Kafka/MinIO/Milvus/Neo4j/Ollama; IBM/quantum hardware; GPU/CUDA; browser/desktop/mobile/Unity/SDR. No claims of consciousness, biological identity or new physical law.
