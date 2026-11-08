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
