# THE $0 API EXPERIMENT — real locally loaded pretrained models (002)

**Date:** 2026-09-29  
**Status:** PASSED ALL 11 STRUCTURAL CHECKS; single bounded model-directed task PASSED.  
**Measured experiment:** [GitHub Actions run 36627646099](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36627646099), PR merge-test checkout 083de94 of head 73b51c719676dbd17f951c4ff939a82cc9f8c6b2 against main e1e2fe572b8bea8e3409e0f347b9f293257607fe.  
**Raw logs and JSON:** Run artifact zero-api-real-models-receipts, artifact ID 11060649168, GitHub-reported artifact ZIP SHA-256 ca6f71b58ce3dfce0b7ead98133613da6fa057414f5cc9c6f52b2265ed9c86fb. GitHub retention: 14 days. The run includes the full exact file manifest, per-call inference events, code of the reproducible test and both successful/failed task output logs.  
**Previous 001 fixture:** [Reference-only results](BEASTBOX_ZERO_API_LOCAL_001_RESULTS.md). These two experiments measure DIFFERENT workloads; do not equate their resource numbers.

## Pre-provisioned actual model weights

Both models were downloaded as *files* before isolation and then loaded in the isolated Docker container by Transformers 4.49.0/PyTorch 2.6.0 CPU with local_files_only=True and trust_remote_code=False. No hosted model inference endpoint was used.

| Executed stage | Repo + immutable revision | Loaded parameters | Actual safetensors SHA-256 |
| --- | --- | ---: | --- |
| A0 and A2 | HuggingFaceTB/SmolLM2-135M-Instruct @ 12fd25f77366fa6b3b4b768ec3050bf629380bac | 134,515,008 | 5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c |
| B1 | Qwen/Qwen2.5-0.5B-Instruct @ 7ae557604adf67be50417f59c2c2f167def9a775 | 494,032,768 | fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe |

The raw artifact contains SHA-256+size for *every* downloaded tokenizer/config/weight file. The current script pins A and resolves then records B at provisioning. To reproduce this exact measured run rather than a potentially newer B revision, provision the exact two revisions above and verify the saved manifest before offline execution. These are two independent PUBLIC pretrained models, not the private native RAWRPHOS checkpoint.

## Actual measured execution (GitHub-hosted Linux x86-64, capped Docker CPU)

The tested container was launched with Docker --network none --cap-drop ALL --security-opt no-new-privileges --read-only --cpus 2 --memory 6g --pids-limit 128; only the checked-out code, downloaded local weights (read-only) and synthetic results directory were mounted. It used the actual existing Beast Box DurableRuntime with one continuing SQLite state substrate.

| Measurement | Actual value | Scope |
| --- | ---: | --- |
| Overall workload wall time | 15.135 s | Container workload only, AFTER downloading weights/building image |
| Measured process CPU | 26.320 s | Process accumulated CPU over multiple cores |
| Peak process RSS | 3,520,284 KiB (~3.36 GiB) | Includes model loads, memory allocator peak |
| Current process RSS at final measurement | 947,900,416 bytes | Different from historical peak |
| Final durable SQLite storage | 98,304 bytes | After close/reopen |
| Model A initial generation | 137 input + 18 output tokens in 1.029 s | One constrained generation |
| Model B with A-memory input | 145 input + 6 output tokens in 1.274 s | One constrained generation |
| Model B no-memory control | 38 input + 24 output tokens in 2.710 s | Not directly matched prompt length |
| Model B synthetic memory write | 163 input + 6 output tokens in 1.360 s | One constrained generation |
| Model B task tool-selection generation | 84 input + 16 output tokens in 2.073 s | Real Qwen output |
| Model B task report-selection generation | 89 input + 23 output tokens in 2.798 s | Real Qwen output |
| Returning A generation | 198 input + 18 output tokens in 1.129 s | One constrained generation |

These time measurements include CPU prefill/output inference and are NOT a quality-normalized throughput benchmark. Download, CI runtime allocation, Docker image build and artifact upload are outside the timed window. Memory peaks will differ on an owner's computer.

## Structural checks: 11/11 PASS

1. Real pretrained A loaded twice; separate real pretrained B loaded.
2. Actual local-model generation occurred in all A0/B1/A2 stages.
3. B's actual input contained memory written during A; returned A's actual input contained memory written during B.
4. One durable system ID and valid checkpoint chain persisted across provider swaps.
5. The exact final checkpoint SHA-256 survived runtime close/reopen.
6. The measured Docker container had only the loopback interface; external IPv4 probes to 1.1.1.1 and 8.8.8.8 both returned OS error 101 (network unreachable).
7. Independent host Docker inspection confirmed network_mode=none, exit_code=0, oom_killed=false; loopback byte counter delta was zero.
8. A task tool call without a host grant was denied.
9. A separately labeled scripted host-only baseline completed.

The number of enumerated lines does not equal the 11 individual machine Boolean fields because some lines group related checks. The raw JSON lists all eleven keys.

## Generated answer quality: IMPORTANT NULL

- Qwen B with selected memory in its actual input generated the exact target code "Quartz-Lantern".
- The same Qwen B in a direct no-memory control did *not* generate the code.
- Returning model A **received the B-stage navigation key in its input but DID NOT generate the correct B-stage key in its answer**. This is a real unfavorable result; preserved without relabeling.
- This is ONE synthetic demonstration, with unequal input lengths and no multi-seed controlled behavioral benchmark. It establishes structural memory DELIVERY across two real local models, not generally reliable semantic recall or a model-quality improvement. Older historical Zeref→SmolLM2→Zeref model-swap evidence is a DIFFERENT workload.

## Real model-originated bounded task agent: one task passed

**Initial test prompting qualification:** This particular successful task run gave Qwen the exact JSON request examples in BOTH prompts, so its behavior is strongly prompted structured tool-following, **NOT an independent action-selection or planning demonstration**. The executed Qwen model (not a deterministic stand-in) returned these two bounded tool requests:

1. A structured request for the authorized host calculator to sum the synthetic numbers 7, 11, 6.
2. After the trusted host returned 24, a structured request to write the verified total 24 to the synthetic-only results workspace.

The test host first denied a tool request without authorization. Only exact allow-listed, type-checked arguments received explicit, temporary per-step grants. The final result contained the independently checked total 24; the raw agent JSON and checksum were preserved. This is **one successful heavily prompted model-output tool workflow**. A stricter follow-up without literal target action JSON is being separately executed and must be reported, including failure if applicable. It does NOT prove general autonomous planning, reliable self-correction, unrestricted tool authority, safety across varied tasks, or ability to perform arbitrary real-world actions. The host-only scripted baseline was measured separately and not credited to the model.

## Cost / isolation scope

- **Paid hosted model inference API calls: 0. Inference API charge observed in the isolated workload: $0.**
- The two public model **file downloads and Docker preparation used ordinary internet before isolation**. Therefore this is not an air-gapped acquisition test.
- The OS-level network proof applies to the **measured Docker container**, not the runner's control plane or unrelated host processes. It does NOT establish that the entire GitHub runner or an owner's computer emitted zero network packets. The two deliberate external connect tests were blocked, not silently treated as no attempted connections.
- **Hosting/runner minutes, download bandwidth, actual power and electricity bills: NOT MEASURED**. This is not a claim of cost-free computation.
- The run was on a **GitHub-hosted computer**, NOT Cory's physical laptop/desktop. Owner-local reproduction and independent host-wide traffic measurement remain open.

## Preserved failed attempts / engineering corrections

- Initial attempt [run 36627001678](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36627001678) correctly refused to create a false receipt: the all-capabilities-dropped container process could not write into its host-owned results bind mount and exited. The initial script couldn't persist the error receipt because it had the same permission problem; its container log/host-network-proof/model manifest are retained in that failed run's artifact.
- Repository Product CI and frozen-history checks separately caught accidental new files under the protected historical experiments/ directory. Those new files were MOVED into a versioned lab/ overlay and the originals deleted without altering the sealed historical experimental sources.
- The corrected launcher keeps --cap-drop ALL while executing as the invoking host UID:GID; separate push/PR runs no longer cancel each other via a shared concurrency group.
- Only [corrected run 36627646099](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36627646099) is the 002 success report.

## Reproduce / remaining gates

See [the owner-local launcher and Dockerfile](../../lab/zero_api_real/README.md) and the measured [script](../../scripts/zero_api_real_models.py). The initial online provisioning requires enough free disk and the two exact repository revisions; subsequent measured inference is inside an OS-isolated Docker container.

**Still open:** on-owner-physical-machine execution, independent whole-host outbound packet capture with other host processes controlled, direct wall-power measurement, broad multi-task autonomous agent success rates, multi-seed equal-prompt behavioral controls and a private pinned RAWRPHOS-vs-other-local-model experiment. The current result is a scoped but real engineering demonstration, not a claim of generalized autonomous intelligence.

## Strict no-answer-template follow-up — preserved failure, new protocol

The original initial run used exact JSON answer examples, so it was NOT an independent model-planning demonstration. A separate stricter run [36628356524](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36628356524) eliminated those target JSON examples. Qwen selected the correct calculate_sum tool and values but returned an object with nested arguments. The original flat-only host parser safely rejected it, producing model_planning_succeeded=false and useful_task_completed=false. All structural A→B→A and isolated-container checks still passed. Do NOT retroactively score that run as successful agent execution. A separately defined protocol now accepts exactly either a flat or one-level nested allow-listed tool arguments object, with unchanged strict host capability and type checks. Its prospective result requires a new independent machine receipt.
