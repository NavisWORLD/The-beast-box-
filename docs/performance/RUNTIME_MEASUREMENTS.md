# Runtime performance and correctness measurements

The durable runtime exposes `result["metrics"]` after a committed turn and
`runtime.last_metrics` after an attempted event. These measurements are ephemeral:
they are not added to the checkpoint, retained memory, model receipt, or evidence
ledger. `runtime.startup_ms` measures its constructor, including validation.

```python
from beastbox.durable import DurableRuntime

runtime = DurableRuntime("./my-beast")
try:
    result = runtime.respond("Recall the sunflower project")
    print(result["metrics"])
finally:
    runtime.close()
```

`total_ms` uses the monotonic clock and includes the transaction commit.
`provider_ms` surrounds the actual blocking provider call. `provider_calls`,
`input_characters`, `input_bytes`, and `output_characters` describe that call.
The current `TextProvider.generate` contract supplies neither token usage nor a
token stream. Consequently `provider_input_tokens`, `provider_output_tokens`,
and `time_to_first_token_ms` are `null`, not estimates or invented measurements.
A provider failure reports its duration and call count, with no output count.
The metrics contain no prompt, response, exception text, or credentials.

`stages_ms` contains elapsed intervals **ending at** each named boundary. These
are sequential intervals, not independent measurements of every named function.
In particular, `policy` marks entry to output validation; `bounded_output`
includes policy evaluation and the bounded simulated tool action. The `model`
interval also includes provider receipt construction; use `provider_ms` for the
call itself. Checkpoint validation, restoration, context construction, writes,
provenance, checkpoint creation, and commit have separate boundaries. Failure
intervals include the rollback and restoration work reached by that failure.

## Request-scoped retrieval reuse

The durable adapter feeds the existing `RefractiveMemoryRouter` a memory view
that reuses association results for the same `(concept, limit)` during one
ranking call. All candidate rows, scores, state-dependent geometry, recency,
ranking order, source IDs, and context construction still use the sealed router.
The view is discarded immediately after ranking. It does not cache answers,
retrieved records, or scores across requests, writes, failures, or model swaps.
The runtime transaction holds the SQLite write lock throughout the ranking call.

The sealed experimental router and its default weights remain unchanged.
Tests compare the optimized adapter's ranking and context hash against that
router at fixed time, including unsaturated association updates. Existing live
corruption and stale-instance checks still run before provider invocation.
The host must explicitly grant authority again after `swap_provider`: a new
provider retains software continuity, but does not inherit the previous grant.

## Reproduce a comparison

Use the **same benchmark driver file** and Python environment for both source
checkouts. The baseline must be an unchanged checkout of the commit being
compared. Run each command after the previous one finishes, without competing
test or browser workloads.

```bash
python scripts/benchmark_runtime.py --source-root /absolute/baseline-checkout \
  --output build/astra-pass/before.json
python scripts/benchmark_runtime.py --source-root /absolute/changed-checkout \
  --output build/astra-pass/after.json
python scripts/benchmark_runtime.py \
  --compare build/astra-pass/before.json build/astra-pass/after.json \
  --output build/astra-pass/comparison.json
```

Each default run uses five fresh worker processes and three public synthetic
workloads: a three-turn conversation, a retrieval turn with 500 retained memory
records, and a 30-turn conversation. Seeding uses real memory writes followed by
a real checkpoint. Seed time is recorded separately. Latencies are measured
without SQLite tracing; an independent replay counts queries and must match the
timed run's behavioral digest. Original prompts, fixture contents, per-repetition
timings, source hashes, source stability, module origins, CPU time, memory use,
database growth, and environment details are recorded.

Workers exclude ambient runtime secret variables, including the optional sealing
passphrase. These runs measure unsealed SQLite storage. The temporary directory
and filesystem device are recorded, along with the Python, SQLite, CPU, and
clock environment. Cold startup means a new store after module import; warm
startup means reopening a store in the same process. Operating-system caches
are not cleared. Peak RSS is a process high-water measurement, not per-turn
allocation. Source hashing binds a run to its actual files even when the source
tree contains uncommitted changes.

The comparison refuses to calculate deltas when fixtures, environment,
measurement configuration, behavioral digests, or correctness checks disagree.
Timing thresholds are not CI pass/fail criteria. Report raw samples and regressions
as well as median improvements. The reference provider is a deterministic text
fixture: identical output hashes establish regression equivalence for these
workloads, not language-model intelligence. Fixture recall, irrelevant context,
and contradictory context are reported separately from semantic answer quality.

## Scope and remaining measurements

The pass measures the supported software substrate. The provider interface still
accepts explicitly configured models independently of memory and authority; no
Astra endpoint, model identifier, credentials, or learned inference result is
invented. Real-provider latency, token accounting, streamed output, reasoning
escalation, and semantic quality require a provisioned provider and an evaluation
suited to its actual capabilities. No new automatic model selection is inferred
from reference-provider measurements.

Full checkpoint verification and retention remain intact. Large histories still
incur scans, checkpoint serialization, and evidence-ledger growth. The benchmark
does not justify a general history-size or throughput guarantee. Exact ranking
preservation also means existing irrelevant or conflicting retrieval behavior
is preserved and visible in the quality fields. These limits must accompany
performance claims rather than be concealed by a reduced workload.

The repository's full tests, architecture acceptance, sealed-evidence guard,
security audit, installed-package demo, and real browser smoke remain separate
gates. Process-interruption and concurrent-writer regressions specifically check
that performance changes do not lose committed history or independent turns.
