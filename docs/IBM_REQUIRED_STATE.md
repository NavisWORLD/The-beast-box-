# IBM-dependent required-state transport

This optional experiment reproduces the strongest form of the continuity question without pretending the QPU is an autonomous COSMOS host.

## Architecture

```text
state S0
  ↓ split
S0_PUBLIC + REQUIRED_SHARD
  ↓
random 128-bit K
  ↓
seal REQUIRED_SHARD with reversible SHA-256 keystream XOR
  ↓
K commitment persisted, K itself omitted from receipt
  ↓
K encoded as sixteen 8-bit H-Z-H PUBs
  ↓
real IBM QPU job
  ↓
originating process may terminate
  ↓
fresh process retrieves same IBM-native job ID
  ↓
per-PUB majority decode
  ↓
K_hat
  ↓ commitment check
  ↓
unseal shard + full-state hash check
  ↓
reconstructed S0
```

The sealer is an **experimental transport codec**, not production authenticated encryption.

## Submit

Create `state.json`, for example:

```json
{
  "objective": "finish the mission",
  "hypothesis": "valid state survives",
  "evidence": ["receipt-a", "receipt-b"],
  "public_note": "safe to persist"
}
```

Then:

```bash
pip install -e '.[quantum]'
# set IBM_QUANTUM_TOKEN locally
beastbox ibm-shard-submit state.json \
  --required hypothesis,evidence \
  --shots 1024 \
  --yes-real-hardware \
  --receipt ibm_shard_receipt.json
```

The persisted receipt contains the sealed shard, commitment, IBM-native job ID, backend, circuit-manifest hash, shot count and PUB count. It does **not** contain the plaintext key.

## Recover from a fresh process

After the job completes:

```bash
beastbox ibm-shard-recover ibm_shard_receipt.json --out recovered_state.json
```

## Required controls

Run the same state with a classical transport channel. Try a wrong/random key and confirm commitment rejection. Score reconstruction with the shard withheld. Do not call IBM uniquely necessary if a matched classical channel succeeds equally well.

## Exact claim boundary

If successful, the experiment can establish that **information returned from a real IBM hardware job was necessary to reconstruct the deliberately designed test condition**. It does not establish quantum advantage, consciousness, IBM persistence of an agent, or real-world escape.
