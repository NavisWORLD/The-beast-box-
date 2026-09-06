# Swap the brain. Keep the story.

**Consumer:** Your AI provider should not have to own your AI history.

**Engineer:** Beast Box keeps persistent memory, state, routing and provenance
outside replaceable inference models.

**Product:** Keep the continuity. Let models compete for the job.

[Download](https://github.com/NavisWORLD/The-beast-box-/releases) ·
[Quickstart](QUICKSTART.md) · [Scientific receipt](PERSISTENT_SUBSTRATE_MODEL_SWAP_002_FINAL_REPORT.md) ·
[CI receipts](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/release.yml)

## 30-second interface demo

After installing, run these three commands. Every command starts a fresh process:

```bash
beastbox runtime chat "Remember the code word is SUNFLOWER" --data-dir ./story
beastbox runtime chat "Recall the code word" --model Reference-B --data-dir ./story
beastbox runtime inspect --data-dir ./story
```

Say: “This is a deterministic interface fixture. The state belongs to the runtime.
The final command verifies its checkpoint.” Do not present the echoed context as
real-model reasoning or the frozen scientific experiment.

## Two-minute technical walkthrough

First install and load two local Ollama models; downloads are not part of the
walkthrough timing. Then run `scripts/run_story_demo.py` with `--model-a NAME`
`--model-b OTHER_NAME --output NEW_DIRECTORY` using an installed Beast environment.
It records five separate process launches, A→A→B→B→A, model manifest identities,
raw prompts/outputs, retrieved memory IDs, checkpoint hashes, backend unloads and a
portable restore before the last turn. Read `story-receipt.json`:
`memory_delivery` measures context delivery; `interpretation` separately measures
exact fact emission. Read the actual outputs before describing conversational quality.
Missing models fail; there is no fixture substitution. The CI job retains failures.

## X launch thread (draft, not posted)

1. Swap the brain. Keep the story. Beast Box is a local-first experimental runtime
   where AI history can live outside the inference model.
2. Memory, software state, routing and provenance belong to the runtime. Changing
   the model does not automatically transfer tool permissions or credentials.
3. A separate frozen real-model A→B→A experiment measured persistent substrate
   continuity with hashes and controls. Current product demos have separate receipts.
4. Downloads, installation steps and limitations are public. Desktop/mobile previews,
   physical-device gaps and optional cloud adapters are labelled honestly.
   https://github.com/NavisWORLD/The-beast-box-/releases

## Engineer launch post (draft)

Beast Box exposes a durable SQLite-backed runtime behind replaceable inference
adapters. Each completed turn records memory, routing/state, provenance and a
checkpoint. Provider failure rolls back the turn. Portable snapshots validate both
manifest and database hashes before a fresh-directory restore, without transferring
host permissions. Try the clean-install and continuity receipts; inspect the frozen
A→B→A report separately. This is release-hardened experimental software, not a
multi-tenant hosted service or universal device certification.

## Product / investor explanation

The product opportunity is continuity owned by the user: model choice can change
without requiring a fresh history store. A viable service would still need measured
user demand, migration support, encrypted storage, retention/compaction, recovery
operations, licensing clarity and unit economics. The repository demonstrates an
engineering architecture; it does not establish revenue, market exclusivity,
provider partnerships, performance superiority or a defensible monopoly.

## FAQ

| Question | Evidence-bound answer |
| --- | --- |
| Is this consciousness? | No such result is established. Persistence is a software property. |
| Is this quantum advantage? | No. Optional resource provenance and quantum advantage are different claims. |
| Is the memory infinite? | No. Storage, retention, corruption and backups impose limits. |
| Does a swap preserve personality? | Stored history/settings can remain; different models can interpret them differently. |
| Can a model inherit permissions? | Not through this runtime's context or imported state. Host authority must be granted explicitly. |
| Can I use local models? | Yes, through Ollama or a configured compatible local server; weights are not bundled. |
| Can I export my state? | Yes, through the versioned portable-state directory with a separately retained manifest hash. |
