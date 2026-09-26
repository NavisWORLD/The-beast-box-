# COSMOS Stage 012 — Rigetti free QVM + archived IBM side-information experiment

**Isolated development:** `experiment/rigetti-qvm-cosmos-loop-012` from Beast Box production-line source `d1ed41a7...`. This branch never changes the Railway service, owner UI, active memory, checkpoint weights, production secrets or paid providers.

## Exactly what this experiment does

1. Reuse the nine **source-reported, published IBM Fez summary rows** already versioned at `beastbox/soul/archive_summary.py`. Each row has a historical job identifier, date, entropy, five-bit most-frequent state and claimed 4,224 shots. The full raw histogram, originating circuits and raw decoder responses are **absent**. We neither recreate them nor call these nine records independent proof of quantum-specific effects. The sealed August 29 four-state historical scientific null remains unchanged.
2. Implement a new **two-qubit test circuit** in Rigetti-compatible Quil: `RX(theta) 0; RY(phi) 1; CNOT 0 1; MEASURE ...`. It is not the missing original IBM circuit.
3. Run **10,000 paired iterations** of a deterministic *local classical ideal* circuit simulator, with 64 seeded pseudorandom samples per step. Its output is explicitly **not** an Azure QVM job or physical quantum measurement.
4. Pass each new synthetic observation and the historical summary side information through the **actual existing Beast Box typed adapters → 12D fusion → `BridgePacket` → CNS7's actual `dyn12` numerical update**. Use a shared, bounded adaptive circuit-selection policy based on the previous fused CNS state. Every control receives the **same** selected circuit and ideal counts.
5. Preserve matched trajectories for `fused`, `simulator_only`, `archive_shuffled` (same archive row multiset, scrambled ordering), `classical_resampled` (with-replacement empirical archive-row bootstrap), `frozen` (state reset at every iteration) and `zero` (no drive). Hash incremental trajectories and record every 1,000th checkpoint.
6. Produce an inert, bounded `cloud_model_preview` for future BYOK/HF/cloud providers. No external LLM is called, no persistent memory updated, and simulated events cannot authorize tools. Closed hosted models would receive semantic/contextual information, not direct neural-layer injection.

**Hypothesis only:** recursive 12D state might help a cloud model select or reason about follow-up experiments. Differences among simulated CNS states do not demonstrate model intelligence improvement, quantum-specific advantage, real physics, biological life, or statistical significance. None of the controls independently trains a model. A future randomized, equal-context-token, independent-holdout cloud-model experiment is required.

## One real Azure QVM simulator anchor, ONLY if the Quantum workspace is connected

Current Microsoft documentation identifies `rigetti.sim.qvm` as a **free ($0) simulator**, distinct from separately billed Rigetti QPUs:
https://learn.microsoft.com/en-us/azure/quantum/provider-rigetti

The optional `azure_qvm.py` can submit **exactly one 64-shot** job to that literal target, after inspecting the actual accessible workspace for the exact target name. The target cannot be supplied by the caller or swapped to a QPU. A strict, authenticated Azure result can optionally replace the *first* local two-qubit observation, and its one-job provenance appears separately in the follow-up 10K receipt. The other 9,999 iterations still remain **local classical ideal simulation**; a single QVM sample does not calibrate physical noise or prove a match to IBM's original 5-qubit experiment. A QVM is still a simulator, **not** fresh quantum hardware.

Your previously configured **Azure Storage SAS/Blob connection is not an Azure Quantum service identity**. GitHub Actions needs a working Azure Quantum workspace **resource ID** and service-principal credentials supplied privately via GitHub Actions encrypted secrets, never written in repository source, commit messages, chat, logs or evidence artifacts.

Required Actions secret names (set on the GitHub repository, not supplied in this chat):
- `AZURE_QUANTUM_RESOURCE_ID`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`

On the explicit `[FREE_QVM_ONCE]` push, the workflow checks whether those encrypted secrets exist. If absent, it records `BLOCKED_MISSING_AZURE_QUANTUM_SERVICE_IDENTITY`, submits **zero** Azure jobs and still completes the local 10,000-iteration stage. With credentials present, it attempts exactly one allowlisted free QVM submission; missing target, failed identity or provider error fails closed (no retry or fallback fabricated result). You can also run the workflow manually, when an authorized Actions trigger is available.

Do **not** run 10,000 cloud job submissions: free target pricing is not unlimited service quota, and Azure/GitHub account constraints may apply. The initial design uses **one QVM anchor maximum**, then 10K reproducible local iterations; expand only after checking actual workspace allowances.

## Reproduce

```bash
python -m pip install -e '.[dev]'
python -m pytest -q tests/test_rigetti_qvm_cosmos_loop_012.py
PYTHONPATH=. python experiments/rigetti-qvm-cosmos-012/loop.py --iterations 10000 --seed 67
# Zero Azure calls. Optional read-only preparation:
PYTHONPATH=. python experiments/rigetti-qvm-cosmos-012/azure_qvm.py
```

Optional restricted Azure submission (requires **your configured identity** and the operator's exact approval string):

```bash
PYTHONPATH=. python experiments/rigetti-qvm-cosmos-012/azure_qvm.py --submit-one-free-qvm --approval FREE_QVM_ONLY
PYTHONPATH=. python experiments/rigetti-qvm-cosmos-012/loop.py --qvm-anchor build/rigetti-qvm-cosmos-012-azure-anchor.json --iterations 10000 --seed 67
```

Artifacts:
- `rigetti-qvm-cosmos-012-local.json`: 10K local classical + real source-reported *summary* side-information
- `rigetti-qvm-cosmos-012-azure-anchor.json`: optional one actual **Azure QVM simulated** circuit result, when connected and successful
- `rigetti-qvm-cosmos-012-qvm-anchored.json`: optional 10K state experiment using *one* QVM sample then 9,999 local samples

We intentionally do not publish secrets, private owner bio data, cloud model responses, simulated "quantum advantage" claims or source histograms that we do not possess.
