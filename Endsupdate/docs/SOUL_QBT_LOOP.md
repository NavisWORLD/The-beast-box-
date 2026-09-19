# QBT x SOUL x Beast Closed Loop

## Status

This document describes the additive SOUL/SDT compatibility layer introduced after the sealed final-organism scientific anchor.

Scientific anchor: `c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f`

Preserved classification:

`ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`

The integration does not rewrite that result.

## What was joined

Three existing lineages now have one explicit software seam:

1. **QBT** supplies normalized provider/simulator/archive state plus provenance and result digests.
2. **Historical SOUL/SDT lineage** supplies the event/genealogy concept, including the historical `SDT_INSTANTIATE` terminology.
3. **Beast Box** supplies the current BridgePacket, Synaptic Field, CNS, dyn12, Quantum Heart, memory, model orchestration, heartbeat and hash-chained evidence ledger.

```text
QBT live/simulator/archive/external state
                    |
                    v
            SoulToken.from_qbt
                    |
             SDT_INSTANTIATE
                    |
             SoulTokenBus
          explicit consumers only
                    |
                    v
            bridge_from_soul
                    |
                    v
      existing Beast BridgePacket
                    |
        +-----------+-----------+
        |                       |
        v                       v
 existing SynapticField      existing CNS
                                |
                                v
                              dyn12
        |                       |
        +-----------+-----------+
                    v
          existing CosmosRuntime
      memory / model / heartbeat
                    |
                    v
         existing EvidenceLedger
                    |
                    v
          soul_token_consumed
```

## Terminology boundary

`SoulToken` is historical project terminology for a versioned software state/event object. It does not establish or claim a literal soul, consciousness, sentience, biological continuity, resurrection, or quantum advantage.

A QBT state may have hardware provenance. Replaying that state later is classical replay. Provenance is preserved but is not equivalent to fresh quantum computation and is not itself evidence that the source caused a model-level effect.

## Authority boundary

Every SOUL token fails closed with these authority fields set to false:

```text
host
network
credentials
tools
model
memory_write
persistence
```

The token layer refuses a token that tries to set any of those fields true. Authority remains with existing host/operator policy.

This preserves the Beast rule:

> STATE MAY TRAVEL. INFORMATION MAY TRAVEL. AUTHORITY DOES NOT TRAVEL AUTOMATICALLY.

## QBT input contract

The Beast integration consumes an already-normalized QBT state dictionary. The expected QBT v1 shape includes fields such as:

```text
qbt_version
provider
backend
execution_mode
timestamp
job_id
shots
entropy
normalized_vector
result_digest
provenance
quality
```

`normalized_vector` values must be finite and within `[0, 1]`.

Beast does not store or request provider credentials in a SOUL token. Suspicious credential-like keys are redacted before content hashing or downstream transport.

## Deterministic token identity

Token identity is computed from canonical content:

```text
schema_version
+ event_type
+ source_type
+ sanitized QBT state
+ parent token
+ generation
+ intended consumers
+ fail-closed authority map
        |
        v
     SHA-256
        |
        v
sdt-<digest prefix>
```

No new wall-clock timestamp is injected by Beast into the hashed payload. If an upstream QBT timestamp is part of the source state, it is preserved as upstream data. Therefore the same archived state and lineage produce the same token ID on replay.

## QBT -> Beast numerical adapter

QBT normalized values are in `[0, 1]`. Existing Beast Spark input is bounded in `[-1, 1]`.

The adapter performs the explicit linear transform:

```text
spark = 2 * qbt_value - 1
```

and cycles the normalized vector to 12 values for the existing dyn12-compatible bridge width. It does not change `beastbox.cns`, `beastbox.dyn12`, the Synaptic Field, or the runtime's existing bridge path.

## Python: one SOUL turn

```python
from beastbox.runtime import CosmosRuntime
from beastbox.soul import SoulLoop, SoulToken

qbt_state = {
    "qbt_version": "1.0",
    "provider": "archive",
    "backend": "example",
    "execution_mode": "archive",
    "timestamp": "2026-08-01T00:00:00+00:00",
    "job_id": "example-job",
    "shots": 1024,
    "entropy": 0.75,
    "normalized_vector": [0.75, 1.0, 0.625, 0.9],
    "result_digest": "<upstream QBT digest>",
    "provenance": {"provider": "archive", "backend": "example"},
    "quality": {"quality_class": "example", "confidence": 0.9},
}

token = SoulToken.from_qbt(
    qbt_state,
    source_type="HARVESTED_IBM_REPLAY",
)

runtime = CosmosRuntime()
try:
    result = SoulLoop(runtime).respond("hello beast", token)
    print(result["soul"])
finally:
    runtime.close()
```

## Deterministic archive replay

```python
from beastbox.soul import ReplaySoulSource

source = ReplaySoulSource(
    archived_qbt_states,
    source_type="HARVESTED_IBM_REPLAY",
)

while not source.exhausted:
    token = source.next()
    result = loop.respond("same preregistered input", token)
```

Replay creates deterministic parent/child genealogy using `parent_token_id` and `generation`.

## QBT loopback source

When the existing QBT sidecar is running on loopback, Beast can consume its normalized state directly without duplicating provider code or credentials:

```python
from beastbox.soul import QBTLoopbackSoulSource, SoulLoop

source = QBTLoopbackSoulSource("http://127.0.0.1:8766")

# Safe default: simulator/control source.
token = source.sample(provider="simulator", shots=2048, seed=9)
result = SoulLoop(runtime).respond("same preregistered input", token)
```

The Beast adapter rejects non-loopback QBT URLs.

Live IBM/Azure requires two independent opt-ins:

1. QBT itself must have been started with live providers enabled by the operator.
2. The Beast call must pass `allow_live=True`.

```python
# QBT/operator configuration remains responsible for provider credentials.
token = source.sample(provider="ibm", shots=1024, allow_live=True)
result = SoulLoop(runtime).respond("same preregistered input", token)
```

No provider credential is passed through `SoulToken`.

## Controls

The same token/adapter/runtime path should be used for source-blind experiments such as:

- harvested IBM replay;
- shuffled harvested replay;
- matched classical state;
- deterministic PRNG-derived control state;
- fixed/zero source;
- simulator state;
- authorized live QBT state.

The source type should change; the downstream consumer machinery should not.

## Live provider boundary

Live IBM/Azure provider execution remains QBT/operator responsibility. This Beast layer deliberately does not duplicate IBM IAM, Sampler submission, Azure jobs, polling, credentials, or provider SDK behavior.

`QBTLoopbackSoulSource` talks only to a loopback QBT sidecar and converts the returned normalized state into the same SOUL token used by replay/control paths. Historical QBT results can be replayed through the same downstream code path offline.

## Historical lineage anchors

The integration design references the earlier SOUL/SDT implementation lineage in `NavisWORLD/infinite-adaptive-audio-12d-universe-engine`, including commits documenting `SDT_INSTANTIATE`, Soul Dust lifecycle/genealogy and 12D state, while importing no unrelated visual renderer or exposed historical credentials.

The QBT contract remains sourced from `NavisWORLD/Quantum-azure-ibm-bridge-attachment-` rather than being reimplemented inside Beast.

## Scientific interpretation

This layer establishes an engineering consumer edge only if tests show a QBT-shaped state can become a SOUL token, enter the existing Beast bridge, reach existing state machinery and be recorded in the evidence ledger.

That engineering edge is not, by itself, evidence that quantum provenance improves model behavior or caused a downstream behavioral effect. Those questions require blinded source controls, preregistered metrics and replication.