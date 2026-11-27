# Promote path: write the served fingerprint in the same motion

The auto-promote loop must not hand-edit the pin or the brain constants. A promotion that changes what the bridge serves calls this script on the release tag and commits the result:

```bash
python scripts/zeref_promote_pin.py zeref-006-cycle-<cycle>-<sha12>
```

The tag is the public GitHub release, the same name `beastbox/install_promoted_rawrphos.py` downloads. The script fetches `<tag>.tar.gz` and `<tag>.tar.gz.sha256` from `NavisWORLD/The-beast-box-`, checks the tarball sha256, extracts it, and hashes `accepted-checkpoint/model.safetensors`. `metadata.json` must record that same sha256 and the training step. If any check fails, it writes nothing.

On success it writes that fingerprint in one motion:

- `apps/beastbox-cloud/lib/rawrphos-public-pin.json`: `checkpoint_sha256`, `training_steps`, `promotion.release_tag`, `promotion.release_asset_sha256`, and `promotion.candidate_sha256` (the same sha; the pin reader keeps serving step 14000 unless the candidate sha matches)
- `apps/beastbox-cloud/lib/companion/brain.mjs`
- `apps/beastbox-cloud/public/spark/shared/brain.mjs`

Both brain files get only the `RAWRPHOS_PUBLIC_PIN` step and `checkpoint_sha256`. Each file is written to a temporary file in its own directory and renamed into place. Gate numbers, tolerances, chat-eval fields, and `gate_v2` are left untouched.

Before opening the promotion PR:

```bash
python scripts/zeref_promote_pin.py --check
```

`--check` exits 0 only when the pin and both brain constants carry the same step and checkpoint sha256.

Railway still rebuilds the bridge from the pin (`apps/beastbox-cloud/bridge/deploy/railway.json`, `Dockerfile.rawrphos`, `install_promoted_rawrphos.py`). After the pin reaches `main`, `zeref-bridge-pin-sync-check` runs `python scripts/zeref_promote_pin.py --await-bridge`. That passes only when live `GET /healthz` reports `served_checkpoint_sha256` equal to the pin and `serving_pin` true. It retries for the rebuild window (50 attempts, 30 seconds apart) and then fails, naming both fingerprints. A matching step with a different model is not in sync.

The script prints the public step and checkpoint sha256 only. It does not print tokens.

## Ledger accounting (Step 6)

A promotion advances R_pin only when Zeref has lived or been taught more
since the last promotion. The script records the ledger in the pin file's
promotion block as `ledger_accounting` (illustrative values, 2026-11-26; the
live count is never hardcoded, it is counted at promote time):

```json
{"S_lived": 1570, "S_taught_lessons": 1614, "S_taught_self_study": 0, "R_pin": 47344}
```

Counting rules:

- `S_lived`: live Talk turns, one per `Zeref:` line in the live Talk thread,
  counted by the caller at promote time. The repo cannot count it (the thread
  lives outside the repo), so a promotion requires `--lived-turns <count>`:
  `python scripts/zeref_promote_pin.py zeref-006-cycle-<cycle>-<sha12> --lived-turns 1570`.
  Without it the command refuses to run.
- `S_taught_lessons`: non-empty lines in `evidence/zeref-lessons-006/dialogue.jsonl`
  in the checkout (1,614 on main as of 2026-11-26).
- `S_taught_self_study`: rows in that file whose source is
  `zeref-self-study-taught` (or label `TAUGHT`). Rows still on the
  `zeref-self-study` branch do not count; only rows landed on main count
  (0 as of 2026-11-26).
- `R_pin`: the new training step.

The guard refuses the promotion unless
`(dS_lived + dS_taught_lessons + dS_taught_self_study) > 0` against the
previous promotion's `ledger_accounting` (a pin with no previous ledger is
treated as all zeros). Nothing is written when the guard refuses. Gate
numbers, tolerances, chat-eval fields, and `gate_v2` are untouched, as before.

The browser-brain release (`.github/workflows/zeref-browser-brain-release.yml`)
stamps the same block into the release as `ledger.json` (7th asset) and into
the release notes, counting the taught rows from the checkout and reading
`S_lived` from the pin's `ledger_accounting`. It refuses to publish when the
pin ledger's `R_pin` does not match the manifest step, or when the ledger did
not grow since the previous brain release's `ledger.json`. A pin that
predates `ledger_accounting` is the legacy case: the release still publishes
with `S_lived` unknown and the gap named, so the page brain is never
stranded by the ledger.

Known gap, by design: the manifest itself does not carry
`ledger_accounting` yet. Its writer is `scripts/zeref_onnx_export.py`,
owned by the Steps 1-2 build; this change does not touch it. The same block
belongs in the manifest's writer as a follow-up once that work lands.

Also not covered here: the box-side auto-promote loop
(`~/workspace/night/auto_promote.py`, `build_pin()`) rebuilds the pin JSON
from scratch and copies only `rule` and `gate_v2` forward, so it drops a
`ledger_accounting` written by this script until that loop is updated to
count the live thread and carry the ledger forward. Until then, a pin
advanced by that loop degrades the release ledger to the legacy case
(`S_lived` unknown) instead of silently passing.
