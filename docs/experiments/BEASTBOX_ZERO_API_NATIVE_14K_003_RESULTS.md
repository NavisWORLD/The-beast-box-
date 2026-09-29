# THE $0 API EXPERIMENT 003 — REAL ORIGINAL NATIVE RAWRPHØS 14K ↔ SMOLLM2

**Date:** 2026-09-29
**Classification:** ORIGINAL_NATIVE_REAL_CPU_OFFLINE_SUBSTRATE_AND_AUTHORITY_PASS_WITH_SEMANTIC_RECALL_NULL
**Research pull request:** https://github.com/NavisWORLD/The-beast-box-/pull/156
**Actual successful source-bound CI run:** https://github.com/NavisWORLD/The-beast-box-/actions/runs/36628260398
**Actual receipts:** Download the attached zero-api-real-original-native-14k-receipts artifact from that run. The exact checked-out experiment was commit 2f696d620f295000ddb258ec8dafcd815c8871b3.

## Fully pinned original artifacts

Native Model A is **Cory Davis / NavisWORLD RAWRPHØS**, the public original native-from-scratch 14,000-step checkpoint, not a replacement or a hypothetical reimplementation:
- Release tag: rawrphos-native-conversation-step-00014000-run-35951509482.
- Archive SHA-256: 3875bc47e8b9d2024b4dae7889bf326f269c5a73955d2d3fc27936ba6794239c.
- Immutable checkpoint weight SHA-256: 4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5.
- Verified native engine identity: 3,909,956 parameters, 14,000 training steps, maximum architectural context 2,048 tokens; **training context 384** (context extrapolation not validated).

Model B is the independent pretrained HuggingFaceTB/SmolLM2-135M-Instruct at fixed revision 12fd25f77366fa6b3b4b768ec3050bf629380bac, verified weight SHA-256 5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c.

The unmodified repository's public native-checkpoint installer independently downloads the official 14K archive, enforces its archive hash, safely extracts the release and verifies the checkpoint weights and training metadata. SmolLM2 source revision and model.safetensors hash are checked separately.

## Actual protocol

Install Python/CPU dependencies and provision the two public model weight sets *before* entering the isolated measurement environment. Run the **real Beast Box DurableRuntime**, not a simulated runtime, with original RAWRPHØS adapter A, real locally loaded pretrained SmolLM2 provider B, and return to original A **without changing its actual weight file**. Use one disposable SQLite persistent substrate and synthetically recorded keys.

Instrument actual local generation, provider swaps, checkpoint persistence after shutdown/reopen, and authority revocation when switching inference backends. Explicitly enable the runtime's last-2 persisted recent-dialogue context while leaving R12 retrieval active. Never use private owner memory. Enter an OS-level Linux network namespace before model inference; the measured process exposes only the loopback interface and has no external route.

## Recorded results: run 36628260398

| Measured property | Actual result |
|---|---:|
| Offline measured workload wall time | **7.26 seconds** |
| Process CPU time | **12.11 seconds** |
| Maximum process RSS | **1,180,266,496 bytes (~1.10 GiB)** |
| SQLite after close | **114,688 bytes** |
| Paid inference API calls | **0** |
| Linux namespace interfaces during measured inference | **lo only** |
| Public IPv4 TCP probe | **Failed as intended; ENETUNREACH (101)** |
| Electricity, equipment amortization, runner allocation cost | **NOT MEASURED** |

**All ten programmed infrastructure checks passed:** original native 14K pinned weight verified, second distinct pretrained model pinned, unchanged weight hash on return, unchanged COSMOS system identity, valid checkpoint chain, identical checkpoint after close/reopen, B-stage memory physically preserved, actual Smol B prompt received native A-stage memory, returning original RAWRPHØS prompt received B-stage memory, and simulated permission grant explicitly revoked when providers changed.

**Quality must not be conflated with persistence:** the first native forward/generation sampled **one EOS token and returned an empty visible response** (prompt 184 tokens). This is a real model invocation but **not** a successful conversational response. Real Smol B generated the first expected synthetic keyword. On returning to original native RAWRPHØS, R12 retrieved B-stage stored memory and recent context was available. Native then generated **12 tokens and 47 visible characters**, but still **did not return the expected second answer**. Its returning prompt was **395 tokens**, longer than the original **384-token training sequence** (though below its architectural cap of 2,048); quality for that extrapolation is not validated. Therefore **automatic successful semantic recall and an original-native intelligence advantage are NOT demonstrated**.

**No general autonomous planning is claimed for native RAWRPHØS.** This experiment tests native inference/swapping, continuity, and host permission boundaries, not an open-ended agent. The separate public two-pretrained-model experiment 002 found a two-step model plan could choose authorized actions but failed a strict factual output test.

## Scope and reproducibility

The experiment ran on an ordinary **GitHub-hosted Ubuntu CPU**, not on Cory's own physical desktop or laptop, and not on a fully disconnected machine from the time of installation. Model downloads and dependency setup happened online before measurement; GitHub receipt uploads happened afterward. The OS-level namespace isolated the *measured Python process and descendants*, not all runner/host traffic. Zero paid inference API calls does **not** imply free energy, hardware, internet or GitHub-runner allocation.

It used the **real publicly pinned 14K checkpoint**; no experimental 18K quality promotion, 20K milestone, unverified internal checkpoint, camera, robotics actuator, paid endpoint, production owner-memory volume or owner machine was touched.

For reproducibility, use the reviewed workflow .github/workflows/zero-api-native-rawrphos-003.yml and the script scripts/zero_api_native_14k_003.py. Run with fresh synthetic output directories and actual network-namespace privileges. Retain the immutable staging-receipt/measurement JSON artifact and any failing future runs separately.

**Publishable conclusion:** original publicly released native RAWRPHØS can be loaded as real local inference in Beast Box, swapped with a distinct local pretrained model, restored to its identical weights while a persistent independent substrate retains verifiable synthetic history, and denied automatic transfer of tool authority. This happened with **zero paid model inference API calls** and strong OS-level process egress isolation during measurement. The native semantic recall-quality target and proof on owner hardware remain open.
