# i dare you 💀 — JEV × PHOS experimental recorder

Owner: Cory Davis · Beast Box. **Status: PARTIAL.** The attached local run executed an independent continuity fixture, not a completed JEV ↔ PHOS model swap. This folder does not modify historical PHOS/Zeref or CST research artifacts.

## Model and data boundaries

- **JEV:** TypeSafe's typed-decision `POST https://api.typesafe.ai/v1/systemone`. It is not a generative chat provider. An explicitly enabled call reads `TYPESAFE_API_KEY` from the environment. Private JEV outputs go in `private_jev/`; never share restricted results without appropriate permission.
- **Authentic PHOS:** published `phera-ra/QC67_cosmo` lineage, `weights/phos.pt`, served with matching architecture and tokenizer. This is different from Beast Box's independent `PHOSReferenceLM` class. An arbitrary file named `phos.pt` is not proof of authenticity.
- Never train PHOS on JEV outputs, claim a JEV API configuration is a JEV weight checkpoint, or promote external-memory retrieval into weight-level learning. `MODEL ≠ MEMORY ≠ STATE ≠ AUTHORITY`.

## Execute and inspect

From the Beast Box repository root, with Python 3.10+:

```bash
python 'i dare you/recorder.py' run --out 'i dare you/evidence/YOUR_UNIQUE_RUN'
python 'i dare you/recorder.py' verify 'i dare you/evidence/YOUR_UNIQUE_RUN'
python 'i dare you/verify_public_ledger.py' 'i dare you/evidence/YOUR_UNIQUE_RUN'
python 'i dare you/dashboard.py' 'i dare you/evidence/YOUR_UNIQUE_RUN' --port 8088
python 'i dare you/replay.py' 'i dare you/evidence/YOUR_UNIQUE_RUN'
python 'i dare you/render_ledger_replay.py' 'i dare you/evidence/YOUR_UNIQUE_RUN'
python -m pytest -q 'i dare you/tests'
```

FFmpeg, Pillow and the DejaVu font are needed for MP4 replay; the live local dashboard uses Python's standard library. The standalone replay bundles verified public events. A replay is **not** an actual screen capture.

To attempt an *authorized* live JEV call, set the key privately and pass `--enable-jev`. To attempt a locally served, authentic PHOS provider, pass `--phos-checkpoint /path/to/phos.pt --phos-url http://127.0.0.1:11500`. The supplied-file SHA-256 is recorded; independently validate checkpoint provenance. Current `--training-command` intentionally refuses to launch an unverified trainer. No authentic PHOS weight-training integration is claimed.

## Actual bundled local results

- 14 real, UTC-timestamped, sequence-numbered and SHA-256-linked ledger events.
- Independent test-fixture memory increased 2 → 3 records; checkpoint save/restore and file round-trip verified.
- Empty-memory and shuffled-memory controls executed as software-state checks.
- JEV A0/A1, PHOS B0/B1/B2, no-training PHOS and trained-PHOS controls blocked; no full provider transition established.
- Four focused local tests passed; training metrics file is **empty** because there were no verified training steps. Transcript explicitly states that no model-generated conversation occurred.
- The MP4 is an event-paced, visibly labeled **REPLAY — NOT LIVE SCREEN CAPTURE**.

The downloadable evidence package is attached to the originating ChatGPT conversation and identified by `LOCAL_EXECUTION_RECEIPT.json`. The package omits private JEV data and restricted model weights. Do not merge partial evidence into `main` as a successful model-swap demonstration.
