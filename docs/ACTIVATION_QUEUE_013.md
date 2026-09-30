# Bounded host-owned activation queue — staged recovery

This module selectively recovers the existing `ActivationEngine` work from the earlier Astra agent branch while keeping the canonical reviewed `DurableRuntime` and its closed-loop/Unicode profile (merged in PR #161) unchanged.

Implementation: `beastbox/activation_queue.py`, not `beastbox/activation.py`. The latter belongs to the independent measured Activation 007 experiment in PR #162; the two are not interchangeable.

## Contract and status

- Defaults to **stopped**. Only a trusted host call to `set_stopped(False, reason=...)` resumes task processing.
- Accepts bounded normalized software events or deterministic maintenance, not arbitrary code, tools, provider-controlled scheduling or physical sensor authority.
- Keeps its own SQLite queue/audit journal and uses the existing `DurableRuntime` for all real turns. The queue never rewrites original memory or neural weights.
- Records an explicit **at-least-once** limitation: interruption after committing a runtime turn but before queue acknowledgement may require owner reconciliation. The operator must not claim exactly-once execution.
- Host-configured `closed_loop` and `unicode_mode` flags must match the real substrate's previously checkpointed profile. Model text or browser payloads cannot change them.
- Emergency stop persists independently of provider availability and preserves existing substrate data.

## Isolated Python example

Run this only against a *new disposable* substrate, not the live Railway owner volume:

```python
from beastbox.activation_queue import ActivationEngine

engine = ActivationEngine("./fresh-disposable-beast")
try:
    task = engine.enqueue("event", {
        "schema": "sensor-event-v1",
        "source": "software-event",
        "text": "isolated bounded software observation",
        "features": [0.2, -0.1],
    })
    assert engine.status()["stopped"] is True
    engine.set_stopped(False, reason="explicit trusted host test")
    result = engine.run(max_tasks=1, wall_seconds=30)
    engine.set_stopped(True, reason="test complete")
finally:
    engine.close()
```

This staged branch deliberately introduces the library and its original regression tests first. No browser, public API or production background scheduler is enabled by this step. CLI/owner control-deck handlers will be ported only after conflicting activation module names and current SIGNALS telemetry are reconciled in review.

## Verification and release boundary

Run `python -m pytest -q tests/test_activation_queue.py tests/test_cosmos_closed_loop_unicode_012.py tests/test_substrate_activation.py` after PR #162 is merged. Also require the whole exact-head CI/security/license/source-pristine matrix, host read/write consistency, restart, malformed task rejection and interruption/stop recovery.

This queue's software continuity or passing fixture tests do **not** establish semantic intelligence, continuous self-learning, verified native checkpoint swaps or intrinsic model self-correction. Production opt-in additionally requires a verified current Railway volume backup and separate-copy recovery drill.
