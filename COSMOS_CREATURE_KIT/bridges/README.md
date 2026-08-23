# IBM, Azure, and classical bridges

All providers must cross the same `cosmos.bridge-receipt.v1` boundary before their state can reach a creature.

## IBM loop

`IBM credential -> isolated broker -> authenticated hardware/job result -> sanitized resident receipt -> BridgeReceipt -> 12D -> 42D -> balanced 54D`

The existing Full Zeref broker is the reference IBM credential boundary. Convert only its sanitized output with `ibm_receipt_from_resident`.

## Azure loop

`Azure credential -> owner-controlled Azure function/service -> numeric 12D payload + provenance hash -> sanitize -> BridgeReceipt -> shared state loop`

The core SDK never stores Azure credentials. The Azure-facing service is responsible for authentication and must return only numeric/provenance data safe for model consumption.

## Classical loop

A deterministic seeded PRNG receipt is provided as a baseline/control. This is important for matched provider experiments.
