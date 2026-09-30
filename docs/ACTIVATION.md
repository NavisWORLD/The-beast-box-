# Bounded continuous activation

The supported activation path is a persistent host-owned queue in
`beastbox.activation.ActivationEngine`. It connects only mechanisms that have
executable contracts:

```text
normalized event
  → persistent queue
  → CNS7 + software state family (12D/42D/54D)
  → R12 retrieval
  → configured inference adapter
  → default-deny bounded output
  → Hebbian co-occurrence metadata + durable memory
  → hash-chained checkpoint and telemetry
```

This is continuous **operation**, not evidence of continuous consciousness or
model-weight learning. The queue is stopped by default. It accepts normalized
events and deterministic memory consolidation, not arbitrary shell commands.
Authority remains session-local and is not stored in the queue, memory, model
prompt, or portable substrate.

## Run

```bash
beastbox runtime queue-event "measured software event" \
  --features '[0.2,-0.1]' --data-dir ./my-beast
beastbox runtime queue-status --data-dir ./my-beast
beastbox runtime queue-resume --reason "owner approved bounded run" \
  --data-dir ./my-beast
beastbox runtime queue-run --max-tasks 1 --wall-seconds 30 \
  --data-dir ./my-beast
beastbox runtime queue-stop --reason "owner emergency stop" \
  --data-dir ./my-beast
```

`beastbox-cosmic` exposes the same queue in **REALITY** and displays the actual
12-value transition, association-update counts, memory IDs, routing receipt,
configured model identity, bounded action result, and measured process/provider
timings in **SYNAPSE TRACE**.

## Recovery and cancellation

Tasks use a finite lease and are recovered after an interrupted lease expires.
Execution is explicitly at-least-once. A crash after the substrate transaction
commits but before queue acknowledgement creates an ambiguous task that can be
retried; inspect the runtime checkpoint and task audit before resuming it.

Queued tasks can be cancelled. A blocking provider call cannot be safely
preempted by Python, so a running task is not reported as cancelled. Emergency
stop prevents new claims and survives process restart; it does not erase the
substrate or queued work. Provider timeouts remain the adapter's responsibility.

## Telemetry interpretation

`cosmos-runtime-telemetry-v1` is persisted in each runtime receipt:

- `state_transition`: real before/after software state, including all 12D
  values and hashes for the 42D/54D families.
- `hebbian_update`: actual SQLite association/salience update deltas. These are
  retrieval metadata updates, not neural-network weight training.
- `memory`: retrieved IDs and committed record IDs/counts.
- `outcome`: bounded authorized-action result. Prediction is marked
  `NOT_EMITTED` unless a future explicit prediction contract is implemented.
- `resources`: measured process CPU, elapsed time, provider time, and character
  counts. Character counts are not token counts.

The activation audit is hash-chained for corruption detection. Like the main
unanchored continuity chain, it is not a signature and cannot defeat a
privileged host that rewrites both records and hashes.
