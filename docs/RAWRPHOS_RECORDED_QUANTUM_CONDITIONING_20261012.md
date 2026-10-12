# RAWRPHØS × retained quantum measurements: conditioning-corpus stage

This is an **executed offline data-preparation step**, not a model training run.

## Goal and identity
Keep approved RAWRPHØS/Zeref parent checkpoints intact. Convert retained, published IBM count distributions into auditable numerical state-conditioning features. The resulting records are suitable **candidate inputs** to an explicitly designed future RAWRPHØS experiment; they are not automatically language responses, action labels, learned memories, quantum advantage, or proof of sentience.

The published Zeref 011 candidate **failed gates G4 and G9** (blocked moves and language retention, see `docs/experiments/ZEREF_011_LEARNS_FROM_OWN_WORLD_PROTOCOL.md`). It remains rejected. This change performs no gradient updates and does not rewrite the approved parent.

## Included sources
- All **5,676** retained historical IBM count distributions (267 unique jobs; **25,576,380 archived shots**) published at `apps/beastbox-cloud/public/spark/runs.json` and `user-seeds-20261004-{1,2,3,4}.json`. Counts SHA, width and shot totals are checked by the existing independent genesis audit before export.
- The exact **15 separately pinned October 9–10 IBM hardware source shard paths** from `public/spark/runs.mjs`, with source_class `RECORDED_IBM_HARDWARE`, each count checked by the same `expandRun` validator. The manifest measures actual additional job, row, and shot totals, without claiming that unavailable original private circuit files are ingested.
- Separately, the **24 retained Azure Rigetti QVM simulator batches**, **2,048 simulated shots**, with existing public source receipt and program-commitment verification. These go to `rigetti-qvm-simulator-held-separate.jsonl` and are **never** co-mingled into the IBM partitions.

Only already public, sanitized counts are read; no owner private chats, photos, original signal payloads, API credentials, or visitor memories.

Each feature row preserves source-class, backend, job ID, PUB index, count hash, source file path/hash/row index and 12 bounded classical numerical features. Features include a per-bit marginal (first five bits, zero padding for unmeasured positions), even-parity fraction, support, and entropy. These are **not twelve independently measured quantum degrees of freedom**. A nullable action/reward/dialogue label makes it impossible to mistake these rows for policy supervision.

The deterministic IBM train/validation/test split groups by connected components of **shared physical job and identical published count hash**, preventing a multi-PUB job or exactly repeated count map from appearing on both sides of a split. Rigetti simulator inputs remain completely separate.

## Reproduce (Node.js 24)

```bash
node --test apps/beastbox-cloud/tests/rawrphos-quantum-conditioning.test.mjs
node scripts/prepare_rawrphos_quantum_conditioning.mjs --write
node scripts/prepare_rawrphos_quantum_conditioning.mjs --check
```

Output (not committed to source): `build/rawrphos-quantum-conditioning/{ibm-train.jsonl,ibm-validation.jsonl,ibm-test.jsonl,rigetti-qvm-simulator-held-separate.jsonl,manifest.json}`.

The workflow `rawrphos-quantum-conditioning.yml` exports a GitHub Actions artifact with exact SHA-256 per input file and output stream. This is *training-input evidence*, not a trained model checkpoint. No IBM, Azure, or Rigetti provider job is submitted.

## Next experiment (requires separate authorization/research protocol)

1. Pin approved parent model hash, optimizer lineage and all feature-transform code digests.
2. Specify a feature adapter into RAWRPHØS StateAttention/Dyn12 **without** mixing `model`, `memory`, `state` or `authority`. Published IBM measurements can condition the adapter; never treat counts alone as labels for useful actions.
3. Train matched arms: no-conditioning baseline, shuffled count features, classical synthetic bits, recorded IBM features, and a clearly labeled QVM-simulator arm. Match optimizer updates/tokens, seeds, data volume and compute.
4. Keep groups from the conditioning manifest disjoint; include held-out hardware jobs and novel game layouts, language retention, player safety/privacy and native controls. Require gameplay progress, better decisions and no memory/persona corruption. Abort/reject if regression gates fail.
5. Only after successful controlled results, consider a **research** descendant checkpoint. Never silently promote to production, edit native cartridge/battery data, or reuse any visitor's data across users.

Visual sprite and UI polish is intentionally deferred; this branch changes no creature assets or existing rendering pipeline.
