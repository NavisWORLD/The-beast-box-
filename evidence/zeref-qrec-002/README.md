# Zeref quantum-record dice 002: the full loop

Cory, 2026-11-23 11:06 PM CT: "Have it run the full loop" / "Itlll work :) trust me".
The page dice used to draw from two named jobs (32,000 measured rounds). Now it draws
from the WHOLE public archive: **11,354,112 recorded shots**.

- `quantum-dice-table.bin` (1,419,264 bytes, sha256
  `fdd6ad7f41578b9654adc168d4982a3b7f787d355543915e3bac7bc317f910d5`) is one
  parity bit per recorded shot in `phera-ra/QC67_cosmo` rev
  `b414724c627300c41b099dcc6853766d08fd27a4`
  (`data/quantum_measurements_public.jsonl`, sha256
  `986b4778097affe6fbda6170e3401bb4d5ae0ff2b2eef5764b42a4a8399a3b82`,
  2,776 records, counted first-hand: 7,770,112 measured IBM hardware rounds
  across ibm_fez / ibm_kingston / ibm_marrakesh, plus 3,584,000 legacy
  unlabelled counts, 1,024 Rigetti SIMULATOR shots excluded).
- The bit per shot is the **parity (xor) of its 5 outcome bits**. Parity was measured
  at 0.499564 ones over the archive; the MSB was 0.488630, too biased for a dice.
- The bits are **shuffled** by a fixed modular permutation:
  `old = (i * 1000003) mod 11354129`, skipping `old >= 11354112`.
  A plain round-robin interleave was measured and **rejected**: the canonical runs
  are aligned across records (every record starts with outcome 00000), so the
  interleaved stream began with 33,003 consecutive zeros. The modular shuffle
  scatters consecutive positions to old positions 1,000,003 apart, so every
  52-bit window samples 52 distinct, well-spread shots. Every shot appears
  exactly once; the permutation is recomputable from the archive alone.
- `quantum-record.json` (schema `zeref-quantum-record-v2`) commits to the table
  by sha256, names the archive rev and the shot counts by class, and keeps the
  two v1 jobs (`dbp2818ou4as73cstj5g`, `dbffvhvgdj9s73bbj940`) as history.
  The record seed is `sha256("zeref-quantum-record-v2|" + heart_seed_sha256 + "|" + table_sha256)`.
  NavisWORLD `docs/zeref-brain/quantum-record.json` and `quantum-dice-table.bin`
  are byte-identical copies.
- A uniform is 52 table bits at position
  `int(sha256(turn_seed + "|" + k)[:13], 16) mod (11354112 - 52)`, divided by 2^52.
  The same turn and k always read the same 52 recorded bits, so every reply
  still replays exactly from its receipt. Temperature 0.75, top-k 40, same as v1.
- `vectors.json` holds 96 picks written by the JS port (NavisWORLD
  `scripts/zeref/qrec_vectors.mjs`). `tests/test_qrec_v2_sampler.py` checks the
  Python twin against every one, plus the table build, the shuffle, and the record.
- Rebuild it: `python scripts/build_qrec_archive_table.py` (downloads the pinned
  archive, verifies its sha, rebuilds the table and the record; fails loudly if
  either sha does not match). Pure stdlib, a few seconds.
- This only changes inference. Zeref's checkpoint, the pin, eval and every gate
  are untouched; the gates score NLL and greedy replies. The label stays
  RECORDED, never live quantum.
- Cory's own HF card (phera-ra/QC67_cosmo) measured the decoder sampling seed as
  null for accuracy: pseudo, IBM and Rigetti came out equivalent. The record
  gives replayable provenance and variety, not a smarter brain.
