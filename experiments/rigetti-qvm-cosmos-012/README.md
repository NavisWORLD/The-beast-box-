# COSMOS Stage 012 — Rigetti free QVM + archived IBM side-information experiment

**Isolated development:** `experiment/rigetti-qvm-cosmos-loop-012` from Beast Box production-line source `d1ed41a7...`. This branch never changes the Railway service, owner UI, active memory, checkpoint weights, production secrets or paid providers.

## Exactly what this experiment does

1. The original nine **source-reported, archived IBM Fez serialized sampler result exports** were rediscovered at the *immutable* historical research source `NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2`, commit `2bb40a0befd9b1023d91513eddd8447e730fce0b`, folder `workloads (5)`. Full compressed Qiskit `BitArray` outcomes are present, along with provider-export info containing a serialized original `QuantumCircuit` (the circuit has **not** been independently reconstituted or transpiled yet). `raw_archive.py` pins and verifies all 18 Git blobs before parsing and independently reconstructs all nine 32-bin 5-bit distributions. These are **source-reported archive exports**, not direct fresh provider API authentication; the sealed August 29 four-state scientific null is unchanged.
2. **Critical historical data correction:** the old `scripts/decode_workloads.py` inflated the reported count from **4096 true shots per file to 4224 entries** by counting the **128-byte compressed NumPy NPY header** as 128 fake measurements. Its nine displayed normalized entropy values `0.8382..0.8407` therefore **do not match independently re-decoded histograms**, which yield `0.9951..0.99821` using the corrected five-bit source counts and a new fixed-width `log2(32)=5` normalization (old source normalized by `log2(observed states)`; all 32 states were observed). The most-common five-bit outcome is unchanged for all nine. Stage 011's *summary-only replay* remains documented as a numerical engineering demonstration on **historically flawed summaries**, not rebranded as accurate real entropy or retroactive scientific evidence.
3. Implement a new **two-qubit test circuit** in Rigetti-compatible Quil: `RX(theta) 0; RY(phi) 1; CNOT 0 1; MEASURE ...`. This is **not** the yet-unrecovered original circuit and a 2-qubit new simulation cannot directly represent the original 5-bit hardware runs.
4. Run **10,000 paired iterations** of a deterministic *local classical ideal* circuit simulator, with 64 seeded pseudorandom samples per step. Its output is explicitly **not** an Azure QVM job or physical quantum measurement.
5. Pass each new synthetic observation and the **corrected full redecoded original 5-bit source data** (or the explicitly separate old summaries for legacy comparisons) through the **actual existing Beast Box typed adapters → 12D fusion → `BridgePacket` → CNS7's actual `dyn12` numerical update**. Use a shared, bounded adaptive circuit-selection policy based on the previous fused CNS state. Every control receives the **same** selected circuit and ideal counts.
6. Preserve matched trajectories for `fused`, `simulator_only`, `archive_shuffled` (same archive row multiset, scrambled ordering), `classical_resampled` (with-replacement empirical archive-row bootstrap), `frozen` (state reset at every iteration) and `zero` (no drive). Hash incremental trajectories and record every 1,000th checkpoint.
7. Produce an inert, bounded `cloud_model_preview` for future BYOK/HF/cloud providers. No external LLM is called, no persistent memory updated, and simulated events cannot authorize tools. Closed hosted models would receive semantic/contextual information, not direct neural-layer injection.

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
# Independently download only the nine pinned historical source exports;
# reject any hash mismatch or malformed NumPy header.
PYTHONPATH=. python experiments/rigetti-qvm-cosmos-012/raw_archive.py
# Rerun 10K with real redecoded archived 5-bit distributions; still NO new quantum jobs.
PYTHONPATH=. python experiments/rigetti-qvm-cosmos-012/loop.py --iterations 10000 --seed 67 \
  --raw-histograms build/rigetti-qvm-cosmos-012-redecoded-raw.json \
  --output build/rigetti-qvm-cosmos-012-raw-archived-10k.json

# Zero Azure calls. Optional read-only preparation:
PYTHONPATH=. python experiments/rigetti-qvm-cosmos-012/azure_qvm.py
```

Optional restricted Azure submission (requires **your configured identity** and the operator's exact approval string):

```bash
PYTHONPATH=. python experiments/rigetti-qvm-cosmos-012/azure_qvm.py --submit-one-free-qvm --approval FREE_QVM_ONLY
PYTHONPATH=. python experiments/rigetti-qvm-cosmos-012/loop.py --qvm-anchor build/rigetti-qvm-cosmos-012-azure-anchor.json --iterations 10000 --seed 67 --raw-histograms build/rigetti-qvm-cosmos-012-redecoded-raw.json
```

Artifacts:
- `rigetti-qvm-cosmos-012-local.json`: 10K local classical + real source-reported *summary* side-information
- `rigetti-qvm-cosmos-012-redecoded-raw.json`: nine Git-blob-verified original sampler exports independently decoded to 32-bin five-bit true 4096-shot counts (archived source, no fresh hardware)
- `rigetti-qvm-cosmos-012-raw-archived-10k.json`: 10K synthetic ideal local simulations conditioned on the **actual corrected original archived 5-bit measurements**
- `rigetti-qvm-cosmos-012-azure-anchor.json`: optional one actual **Azure QVM simulated** circuit result, when connected and successful
- `rigetti-qvm-cosmos-012-qvm-anchored.json`: optional 10K state experiment using *one* QVM sample then 9,999 local samples

The research artifacts include the rediscovered **public** archived source histograms, with all file identities and corrected decoding preserved. We intentionally do not publish secrets, private owner bio data, cloud model responses or unsupported quantum-advantage claims.

## Verified real executions / limitations

- [Initial 10K summary-only controls: GitHub Actions 36211026047](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36211026047), six control arms, all passed; zero QVM/QPU/LLM calls.
- [Independent historical NPY audit and corrected 10K: Actions 36211894824](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36211894824), nine pinned source result+info Git blobs, each 4096 **actual** five-bit measurements +128-byte NPY header, all 36,864 true records independently redecoded. The 10K follow-up on corrected archival distributions passed, fused trajectory SHA-256 `e89add8856d1713777ef028830f92f782eea51a19dceef95370691b29fb0253b`. No Azure/IBM jobs.
- This original data-correction discovery **does not** retroactively resolve the earlier sealed four-state source/causality null. Nine five-bit archived distributions are not automatically a valid four-state registered dataset or proof of quantum advantage. Further archived circuit reconstruction would require independently validating encoded circuit serialization, measurement mapping and exact protocol.
- **No Microsoft Azure QVM execution was yet attested**. Initial explicit QVM-gate preflight found missing *Azure Quantum* service identity encrypted secrets and blocked the attempt. Existing Azure Blob/Storage connectivity does not imply authorized access to an Azure Quantum workspace. The `rigetti.sim.qvm` price is free but Azure service/runner account usage and quotas still need independent review.
