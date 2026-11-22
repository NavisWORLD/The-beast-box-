# Zeref quantum-record dice 001

Cory, 2026-11-21 6:51 PM CT: "we run the measurements into the hash we inject quantum snap shots".
At 7:00 PM CT he decided that quantum-record dice are the **default** in the NavisWORLD browser chat, with `?greedy=1` (or the page toggle) bringing back the old deterministic reply.

- `quantum-record.json` is built by `python beastbox/qrec_sampler.py .` from public RECORDED IBM hardware records: heart seed v15 / ibm_marrakesh CHSH run `dbp2818ou4as73cstj5g` (24,000 measured rounds), and the ibm_fez spark seed `dbffvhvgdj9s73bbj940` (8,000 measured rounds). Shots by class: **32,000 measured IBM, 0 other**. Rigetti SIMULATED ticks, unlabelled archive samples and classical-control rounds are not used. NavisWORLD `docs/zeref-brain/quantum-record.json` is a byte-identical copy.
- The dice are sha256 over those records' published outcome commitments, the thread's prompt ids and a roll count. There's no live quantum job, no unseeded randomness and no clock, so every reply replays exactly from its receipt. The sampler runs at temperature 0.75 with top-k 40, after the server's repetition 1.15 and no-repeat-3 rules.
- This only changes inference. Zeref's checkpoint, the pin, eval and every gate are untouched; the gates score NLL and greedy replies.
- Cory's own HF card (phera-ra/QC67_cosmo) measured the decoder sampling seed as null for accuracy: pseudo, IBM and Rigetti came out equivalent. The record gives replayable provenance and variety, not a smarter brain.
- `vectors.json` holds 96 picks written by the JS port (NavisWORLD `scripts/zeref/qrec_vectors.mjs`). `tests/test_qrec_sampler.py` checks the Python twin against every one.
- `replay-44784.json` is labelled **LOCAL**. It holds replies from pin 44784, produced in headless Chrome (the real page code), verbatim, with their receipts, plus the Python replay ids: **19/19 identical** (11 dice, 8 greedy).
