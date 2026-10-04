# Spark Beasts

A visitor sparks a game companion from two public inputs:

1. A `cosmic-muse-traits-v1` signal (`focus` = beta, `calm` = alpha, `spark` = gamma, each 0–100). The page can simulate a headband or, after an explicit consent checkbox, read derived traits from a Muse 2, Muse S, or Muse S Athena over Web Bluetooth. Raw samples stay in the page and are discarded.
2. One recorded IBM Quantum count distribution from `data/quantum_runs.compact.json` (5,580 job×PUB distributions, 171 jobs, backends `ibm_fez`, `ibm_kingston`, `ibm_marrakesh`, `ibm_torino`).

The seed is SHA-256 of the bucketed traits, the run identity, and the full counts. Beast Box's unmodified `packets_to_dyn12`, `mirror_step`, and `StateFamily` turn that into a 12D then 54D state. Body, voice, and behavior then come from labelled SHA-256 streams. The same inputs rebuild the same beast in Python and in the browser.

The recorded counts are a fixed seed from a past hardware job. They are not a live quantum device, not entangled with the visitor, and not uniform randomness. A beast is a game companion, not a conscious system. The page is not a medical device.

## Browser

Static files live in `apps/beastbox-cloud/public/spark/` and are served by the Vercel app at `/spark/index.html` (rewritten from `/spark`). The compact runs table is copied to `public/spark/runs.json`. Nothing is uploaded.

Download writes a `.qbeast` file in the Living Universe `QBEAST1` / version 1 shape (`arcade/lost-cosmos/qbeast.mjs`). The game rebuilds its companion stats from the 64-character seed. Host progress is zero and the dyn12 projection is `unavailable`, so no signature is required. One public memory event is the spark card (`traits`, bucket, run key, stage-2 name). Open the game at https://navisworld.github.io/Cosmic-synapse-the-living-universe-sim-engine-/

## Reproduce

From the repository root, with this repo installed (`pip install -e .`):

```bash
python spark-beasts/generate.py --simulate serene --run ibm_kingston:d93jnlq47v0s73823aj0 --out /tmp/spark
python -m pytest tests/test_spark_beasts.py
node --test apps/beastbox-cloud/tests/spark-beasts.test.mjs
```

`beastgen/render.py` is the original Pillow sprite renderer. It is not imported by the tests. Install Pillow only if you want offline PNG sheets.

The browser port is `apps/beastbox-cloud/public/spark/*.mjs`. It is checked against `golden/case.json`.
