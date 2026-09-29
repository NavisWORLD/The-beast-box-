# THE $0 API EXPERIMENT — BEAST BOX LOCAL REFERENCE FIXTURE (001)

**Date:** 2026-09-29  
**Status:** PASS (bounded reference-fixture proof; NOT a real two-checkpoint model experiment)  
**Executed source:** PR [#153](https://github.com/NavisWORLD/The-beast-box-/pull/153), branch `experiment/zero-api-local-cosmos-001`, verified head `d8f5f3476400dc7deb203588382444bd4bce1e3e`  
**Verified CPU run:** [GitHub Actions 36625466316](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36625466316) (PR merge checkout of stated branch and main)  
**Raw receipt:** `zero-api-local-fixture-receipts` artifact attached to run above.  
**Reproduction:** `python -m pip install -e . && python scripts/zero_api_experiment.py --output build/zero-api-experiment.json`

## Protocol

Run the **actual** checked-out `beastbox.durable.DurableRuntime` on an Ubuntu 24.04 GitHub-hosted runner with Python 3.12.14 and no model credentials. Create a fresh synthetic-only SQLite substrate. Record a synthetic phrase through the project's deterministic `ReferenceTextProvider` A, replace the provider with separately labeled reference adapter B, confirm B actually received A-stage memory in its input, record new B-stage synthetic memory, switch back to A, and check that A received the new memory. Verify identical system ID and valid memory/checkpoint chain after an explicit close and restart.

Separately submit a deterministic, strictly simulated tool request with **no host permission**, assert denial, give an explicit host-side grant, and assert a bounded 0.25 simulated-position change. Execute the existing bounded host maintenance method, record whether it did work. Sample actual process wall time, process CPU time, peak resident-set size and actual database + WAL bytes. The measured Python process forbids Python socket creation/network activity and subprocess execution, with all attempts counted. Initial source installation and GitHub's result upload are **outside** the measured window.

## Measured result

| Actual measurement | Result | Interpretation |
| --- | ---: | --- |
| Experiment runtime wall time | **85.053 ms** | Bounded reference fixture on this GitHub-hosted CPU, excludes setup/upload |
| Process CPU time | **79.092 ms** | Same measured workload; not model inference FLOPs |
| Peak process RSS | **28,572 KiB (~27.9 MiB)** | Peak for Python process and loaded Beast Box runtime |
| SQLite + WAL bytes before close | **691,976** | Pre-close live files; NOT final on-disk main database size |
| SQLite files after restart | **282,624 bytes** | Checkpointed database/storage after close/reopen |
| Python socket/subprocess attempts | **0** | During the guarded Python workload; not a whole-machine egress audit |
| Paid model API calls | **0** | Only bundled deterministic reference adapters, no paid providers |
| Runtime turns | **6** | Four synthetic continuity turns + two simulated tool turns |
| Final memory records | **13** | Synthetic test records, no private owner data |
| Maintenance change | **false** | Maintenance was invoked and found no work; cannot claim continuous self-improvement |

**All assertions passed:** same system ID across A→B→A, routed memory delivery in both directions, valid checkpoints, changed memory digest with recorded turns, denied tool without permission, authorized tool only after explicit host grant, exact verified checkpoint after restart, zero attempted Python network/subprocess use, and fixture-only labeling.

## Interpretation and exclusions

This is a narrow proof that the existing local-first **software substrate**, routing interface, checkpoint recovery and host authority gate operated together without paid inference APIs for this synthetic workload. It **does not demonstrate two pretrained language models**: both A and B wrap the same deterministic `ReferenceTextProvider` code under separate labels. Routing memory into a fixture prompt does not establish semantic recall, reasoning improvement, learning or a new intelligence property.

The authorized action is a **simulated numeric move**, not real-world actuation. The host explicitly invoked maintenance, which performed **no new consolidation** on this tiny dataset. It is **not autonomous open-ended task planning or execution**.

This proof was executed on a **GitHub-hosted local CPU process**, not the owner's laptop or a disconnected physical machine. Dependencies were installed online before measurement; GitHub uploaded artifacts afterward. Python-level socket/subprocess guards and zero counted attempts are **not an OS-level packet capture** and do not measure external co-tenant traffic. Unmeasured costs include runner allocation, electricity, hardware amortization and any local model-download bandwidth; **“$0” here means $0 paid inference API calls, NOT free computation**.

No RAWRPHØS 14K/18K weights, third-party pretrained model, remote provider, GPU, camera, real sensor, paid endpoint, owner memory or production deployment was used or tested. Do not generalize this fixture's 85 ms wall time or 27.9 MiB RSS to those workloads.

## Preserved initial failure

An earlier workflow attempt [36625208158](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36625208158) was **incorrectly green** because its shell piped an exception through `tee` without `pipefail`; its actual Python test failed when `platform.platform()` attempted a subprocess after the lock was activated. The subsequent patch removed that forbidden subprocess, wrote structured crash receipts and added `set -o pipefail` plus a nonempty-receipt assertion. **Only corrected run 36625466316 is the successful measurement.** Preserve both logs for reproducibility.

## Remaining gates before claiming the full $0 local experiment

1. Repeat offline, on actual owner-local hardware, using pinned and hashed **real** RAWRPHØS and a second installed local pretrained model checkpoint (no HF/Ollama Cloud runtime calls). Prove actual inference A→B→A and measure tokens/second, latency, CPU/RAM/disk/electricity where available.
2. Implement and evaluate a separately authorized, bounded agent task loop with independently verifiable useful task success, failures, rollback, authority checks and no uncontrolled physical or shell access.
3. For a strict *network isolation* claim, run a dedicated OS-level network namespace/firewall with packet/egress counters, including any helper processes, after offline weight provisioning; inspect results before publishing.
4. Compare against reference-only and memory-disabled controls; do not treat this small fixture as evidence of pretrained-model reasoning quality or autonomous cognition.

**Public claim:** In a measured Python process running Beast Box's actual durable runtime and deterministic offline reference adapters, A→B→A routed-memory continuity, restart recovery and explicitly governed simulated tool execution passed, with zero attempted Python network connections and zero paid inference API calls. Actual two-model inference, useful autonomous task success, disconnected-machine operation and total system cost remain unverified.
