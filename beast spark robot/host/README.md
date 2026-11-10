# spark_brain — host brain for the Zeref Spark

> **CONCEPT DESIGN / NOT BUILT HARDWARE.** It's tested on synthetic and recorded frames only.
> The pulse is an **ESTIMATE, non-medical**. Simulated frames are labelled **SIMULATION** and can't drive the real
> state.

It uses Cory's Beast Box code as-is. `spark_brain/beastbox_vendor/` holds byte-identical copies from
`NavisWORLD/The-beast-box-` @ `4783146`, with SHA256SUMS checked by a test.
- Architecture: `../docs/BRAIN_ARCHITECTURE.md`.
- Spec and citations: `../docs/SPEC_FROM_BEASTBOX.md`.
- Decisions: `../docs/DESIGN_DECISIONS.md`.

```bash
cd host
python -m spark_brain demo [--psi] [--speak --say "hello"]    # simulated frames through the whole brain
python -m spark_brain replay frames.jsonl                    # recorded Spark output
python -m spark_brain serial /dev/ttyACM0 --beastbox-features ~/.beastbox/features [--speak --say "hi"]  # real device (pyserial; untested)
python -m pytest tests -q                                    # 58 tests (C++ parity tests need a host C++ compiler)
```

New in this pass:
- **Overlay bands** (`routing_spark_overlay.json`, `overlay.py`): band 7 crystal and band 8 body. Same receipt rules as
  Cory's router, with their own state, so his 54-slot state is unchanged (D2).
- **ψ readout** (`psi.py`): off by default, DERIVED, drives nothing (D4).
- **Speech** (`speech.py`): local piper TTS in `~/.zeref-spark/ttsv` with the voice `~/.zeref-spark/voices/en_US-lessac-low.onnx`,
  or a labelled stub. It produces 16 kHz PCM lines with credit-based pacing. Speech is off unless you turn it on (D6).
  Override the paths with `ZEREF_PIPER_PYTHON` and `ZEREF_PIPER_MODEL`.

To feed the real Beast Box, point `--beastbox-features` at its `BEASTBOX_FEATURE_DIR` and run the Beast Box with
`BEASTBOX_LIVE_ROUTING=on`. Overlay sources never go there.

Test result: `TEST_RESULT.txt`.
