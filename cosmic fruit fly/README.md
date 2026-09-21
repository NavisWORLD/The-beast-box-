# Cosmic Fruit Fly 🪰 — isolated experimental continuation

**Status: engineering harness executed on a synthetic graph; a genuine fly-connectome result is NOT established.** This continues the existing README-only folder without modifying the Beast Box runtime or historical experiments.

## Recovered state and boundaries

The repository's `main` at `21ecef58011409a257394e5f7e2fb1bdf8a681a6` contained this folder's original README only. The seven historical local feature commits were not present on the verified remote; no lost source code is claimed as recovered. The checked-in public `beastbox/dyn12.py` was inspected and its `update_dyn12` is loaded from the parent project by `harness.py`. That module itself warns it is a public reference, not private COSMOS equivalence. The isolated harness uses its own **non-durable dict** for a bounded cue-action lookup and its own computational plasticity; it does **not** claim operational integration of `beastbox.memory.ReconciliationMemory`, R12, SYNAPSE, HEARTLIGHT, a deployed model provider, or physical sensors/actuators. Those remain external integration gates.

## Actual execution

The harness operates a discrete-time closed loop: scripted sensor cue and context → sparse recurrent activity → canonical dyn12 → four-key bounded lookup → software binary action → environment reward → bounded reward-modulated weight update. Recurrent dynamics, learning-rate, stimulus encoding, and controller are engineered assumptions, **not measured fly physiology**. The nine arms compare no connections, intact connections, topology rewiring, lesioning, plasticity-disabled, and memory-disabled in a crossed subset. The synthetic engineering fixture is deliberately **not** Drosophila connectivity.

Each of eight seeds receives the same seeded 80-train/40-test schedule across arms. Training delays are four time steps; test delays seven time steps. The task reuses four cue-context combinations in the test phase: this is a delay robustness smoke test, **not out-of-distribution generalization**. The memorization path dominates, obscuring graph effects. Per-trial actions, reward, state norms and run metrics are in the JSONL file.

## Reproduce (from repository root)

```bash
python -m unittest discover -s 'cosmic fruit fly/tests' -v
python 'cosmic fruit fly/harness.py' --fixture --output 'cosmic fruit fly/evidence/reproduction'
```

To try a separately acquired FlyWire-compatible CSV and accompanying honest provenance declaration:

```bash
python 'cosmic fruit fly/harness.py' --csv /path/to/connections.csv --metadata /path/to/connections.metadata.json --output /path/to/fly_run
```

Metadata must contain nonempty `dataset`, `version`, `source_url`, `license`, `sha256`, and `origin_class` (`source_declared_biological` or `synthetic`). Connectivity must have `pre_root_id,post_root_id,syn_count` and optionally `nt_type`; a source-provided SHA is checked against exact bytes. The loader selects the **first file-order rows** (up to 1024 edges / 64 neurons by default), which is NOT a representative connectome sample. A source assertion is not independent verification of biological provenance. No automatic download, fabricated-data fallback, license override or externally authorized action occurs.

Original FlyWire v783 annotations: https://github.com/flyconnectome/flywire_annotations ; connectivity: https://zenodo.org/records/10676866 . **Review source/data licensing before redistribution or commercial deployment.** The provided synthetic fixture is not derived from FlyWire. A full, verified dataset, source-identity checks and external integration are pending.

Evidence and limitations: [`FINAL_REPORT.md`](FINAL_REPORT.md), [`evidence/synthetic_2026-09-19/summary.json`](evidence/synthetic_2026-09-19/summary.json). Do not treat synthetic scores as biological evidence.

## New hard-mode continuation — 2026-09-20
See `HARD_MODE_REPORT.md` and run `python hard_mode.py --seeds 4` or `python render_hard_mode.py --output hard_mode.mp4`. The discrete three-token communication uses an experimenter-fixed grammar and in-memory resource gate. Source-derived 42-neuron neural activity and historical IBM summary replay are separate measured modeled inputs, not a demonstrated mechanism for language. The video is a rendered virtual experiment replay.


## Full reproducible source snapshot (separate release package)

The latest verified local snapshot adds `neural_dependency.py`, its complete dependency chain, 42-node relay tests and `native/` numeric parity interfaces. Python remains the complete simulator. Install `requirements-research.txt` from the repo root; `ffmpeg` is needed for MP4 output. Windows launchers are in `windows/`, with limitations in `NATIVE_COMPATIBILITY.md`.

**Source-delivery gate:** the GitHub feature branch may include only part of this snapshot until the entire source archive has been uploaded and CI has run on its final commit. This README does not claim a completed push. See `NEURAL_DEPENDENCY_REPORT.md`, `data/DATA_LICENSE.md` and the offline package manifest.
