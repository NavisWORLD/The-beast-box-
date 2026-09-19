# Beast Box runtime and web performance pass

The 500-memory reference workload fell from **919.35 ms to 55.19 ms** per turn
(94.00% lower median latency). The 30-turn workload fell from **3.223 s to
0.986 s** (69.39% lower). Both versions pass the same 269 correctness checks
and produce matching behavioral digests. These are software-substrate results
using the deterministic reference provider, not learned-model intelligence or
inference-speed results.

## Source and method

| Item | Evidence |
| --- | --- |
| Live main / baseline | `86312ae960746e92f3ff0c19a3727c59ad0534d2` |
| Recorded local runtime and web implementation | `34596b7b0c2f2b6d34ef103ee1cee40c485b2e71` |
| Recorded local measured revision, including benchmark isolation | `44c84d5a752186450ea0efc77b480785bd359bb0` |
| Baseline tests before behavior changes | 973 Python tests; 14 Node tests passed |
| Comparison | Five fresh worker processes per revision; same driver and fixtures |
| Machine | Linux x86_64, AMD EPYC 9V74, nine CPUs in the recorded affinity |
| Runtime | Python 3.12.14; SQLite 3.53.1; unsealed temporary SQLite stores |

Main was rechecked against GitHub and remained at the baseline revision. Its
four latest applicable workflows passed; see [main CI](astra-pass-2026-09-12/main-ci.json).
Open research drafts and dependency updates were inspected. No newer validated
product implementation was recovered from them; none was merged into this pass.

The runtime checkouts were clean and stable during the final measurements.
Publication used the authenticated GitHub connection because command-line git
had no credentials. GitHub supplies different commit metadata: the measured
source is published as [50d2b9b](https://github.com/NavisWORLD/The-beast-box-/commit/50d2b9b15f75c6cadddb59a279317251eef1e13a).
Its complete tree hash matches the recorded local measured revision. The
[publication mapping](astra-pass-2026-09-12/publication.json) preserves both
commit identities and verified tree hashes; the original benchmark receipts
are unmodified. The final evidence commit changes documentation only.

Each receipt includes source hashes, module origins, environment, public fixture
contents, raw samples, CPU time, startup/restart timing, retrieval timing,
context sizes, provider calls, database growth, and process peak RSS. SQL counts
come from a separate replay that must match the timed run's behavioral digest.
No SQL tracing or sampling profiler runs during the latency samples.

An exploratory run exposed unequal compiled-module caches between the two
checkouts. The final driver redirects Python bytecode reads to an empty cache
and disables writes. A regression deliberately installs stale unchecked
bytecode and proves that the driver uses the selected source. Only the final
normalized comparison is archived here. OS filesystem caches are not purged;
these results do not measure a machine boot or a loaded neural model.

Reproduction commands and metric semantics are in
[RUNTIME_MEASUREMENTS.md](RUNTIME_MEASUREMENTS.md). The
[before](astra-pass-2026-09-12/runtime-before.json),
[after](astra-pass-2026-09-12/runtime-after.json), and
[comparison](astra-pass-2026-09-12/runtime-comparison.json) receipts are the
numerical source of truth. The comparison refuses mismatched fixtures,
environments, measurement settings, failed checks, or changed behavior.

## Measured bottleneck and change

The historical router requested the same concept associations separately for
each memory candidate. In the 500-record fixture, eight query concepts caused
4,000 association SELECTs. R12 retrieval alone consumed 892.07 ms of the
919.35 ms turn.

The durable adapter now reuses each `(concept, limit)` association result during
one ranking call, under the existing SQLite transaction. The cache is discarded
after that call. It never retains answers, scores, or memories between turns.
All candidates, scoring, recency, state-dependent routing, provenance, validation,
and persistence remain in the path. The sealed router itself is unchanged.

| Workload | Before median | After median | Latency reduction | Association SELECTs |
| --- | ---: | ---: | ---: | ---: |
| Three-turn conversation | 19.325 ms | 17.598 ms | 8.94% | 44 → 14 |
| One turn with 500 retained records | 919.354 ms | 55.188 ms | 94.00% | 4,000 → 8 |
| Thirty-turn conversation | 3,222.870 ms | 986.458 ms | 69.39% | 11,968 → 344 |

R12 retrieval in the 500-record fixture fell from 892.07 ms to 27.69 ms.
Total CPU time fell by 94.00% in that fixture and 69.39% in the 30-turn fixture.
These measurements cover these public synthetic workloads; they are not a
general history-size, throughput, or cloud-inference guarantee.

## Correctness and context quality

| Workload | Provider calls, before = after | Prompt characters, before = after | Relevant fraction on final query, before = after |
| --- | ---: | ---: | ---: |
| Three turns | 3 | 2,758 | 3/4 |
| 500 retained records | 1 | 673 | 1/5 |
| Thirty turns | 30 | 34,936 | 1/5 |

The requested original user memory is retrieved in all three workloads, before
and after. Output digests, selected context, and retained database growth match.
Exact ranking and context hashes also match the sealed router in regression
tests at fixed time, including a later write with unsaturated association weights.

**No semantic intelligence improvement was measured.** The retained-history
fixtures still retrieve four irrelevant rows alongside the relevant row. The
outdated conflicting note in the 500-record fixture remains stored but is absent
from the final top five in both versions. This does not establish general
conflict-resolution ability. Ranking quality was preserved, not inflated by
dropping difficult cases or changing the fixture.

## Runtime observations and authority

Successful turns expose ephemeral monotonic boundary timings in `result.metrics`;
failed attempts expose them through `runtime.last_metrics`. Constructor time,
actual provider-call duration, call count, and input/output character counts are
available. Metrics contain no prompt, response, exception text, or credentials,
and are excluded from retained state and evidence receipts.

The provider contract is blocking text generation. TTFT and provider token
counts are explicitly unknown. No simulated stream or character-to-token
conversion is reported. Boundary intervals and their limitations are documented.

Direct `DurableRuntime.swap_provider` now revokes prior simulated-tool grants,
matching the model/authority separation already enforced by the product layer.
Identity, memory, state, checkpoints, artifacts, and provenance survive the swap.
Tests exercise denied and explicitly allowed tools, failed-provider rollback,
malformed input, independent writer processes, and a process killed during a
real memory write. Committed state survives recovery; interrupted state does not.

CST/dyn12, plasticity, R12, Synapse, and continuity mechanisms remain in place.
The sealed-evidence guard passes. Their experimental classifications are
unchanged; faster software routing does not establish new scientific claims.

## Web transport and interaction

The actual `/html/` server on the baseline disconnected because its `headers`
method collided with `BaseHTTPRequestHandler.headers`. The transport now serves
the client, redirects entry URLs correctly, confines static paths, and renews
its HttpOnly session cookie when the live shell is reopened.

The client loads inactive memory, trace, and storage panels on demand. After a
chat it consumes the committed POST result, then refreshes authoritative
conversation history and any active detail panel. It rejects invalid JSON and
ignores late reads from older mutations or runtime selections. Pending turns
are separate from retained history and are removed on a refused write.

| Web measurement | Before | After |
| --- | ---: | ---: |
| Initial runtime GETs | 7 | 4 |
| Initial GET response-body bytes | 46,592 | 17,082 |
| GETs after ordinary chat | 7 | 1 |
| Median GET response-body bytes after chat | 58,419 | 16,667 |
| Median automated chat-to-render time | 467.464 ms | 221.604 ms |

Because the original transport was broken, this client comparison runs old and
new assets against the **same repaired transport and backend**, with 12 seeded
chats and five measured chats. Backend, driver, browser, and environment hashes
match. Service workers are blocked for this comparison; their behavior is
tested separately. Bytes exclude headers and POST responses. Wall time includes
browser automation and is secondary evidence, not TTFT. Raw
[web before](astra-pass-2026-09-12/web-before.json) and
[web after](astra-pass-2026-09-12/web-after.json) receipts preserve every sample.

The service worker now caches only the static shell allowlist. Runtime APIs and
health responses never enter that cache. The shell uses the network when
available so a server restart can renew its session; offline status remains
explicit. The stylesheet now targets the actual app element, making the desktop
composer reachable and the 390px layout fit the viewport.

Real HTTP regressions cover invalid Host headers, traversal, malformed cookies,
session renewal, cross-origin writes, and browser form submissions. Authorized
writes require JSON and reject a supplied foreign Origin, including another
loopback port. Cloud authority remains denied without an owner grant.

## Verification and observed tradeoffs

| Local gate | Result |
| --- | --- |
| Python unit, integration, acceptance, and regression tests | 1,026 passed; 68% coverage |
| Web Node tests / syntax / static build | 14 passed / passed / passed |
| Architecture acceptance | 24 checks passed |
| Golden reference demo | 13 checks passed |
| Canonical COSMIC browser smoke | 12 flows passed, including workspace and export/import |
| `/html/` browser smoke | 12 flows passed, including delayed reads, restart, denied writes, offline, mobile width |
| Packaging | Wheel and sdist built, installed, and exercised outside the source checkout |
| Static checks | Ruff passed; mypy passed on 21 configured source files |
| Security / sealed evidence | 0 errors, 0 warnings / passed |

The [evidence manifest](astra-pass-2026-09-12/manifest.json) identifies local
receipts. GitHub Actions results must be checked on the final PR head separately;
local receipts do not stand in for CI. Web CI now runs the real HTTP regressions
and Chromium smoke in addition to static checks.

No functional regression was observed in these gates. Measured costs are also
retained: fresh-store startup increased by 0.022–0.104 ms across workloads;
warm startup increased by 0.017–0.299 ms. Peak process RSS at the 500-record
workload increased from 27,242,496 to 28,155,904 bytes, about 0.87 MiB (3.35%).
The small-workload peak increased by about 0.56 MiB; the 30-turn peak decreased
by about 0.27 MiB. These are process high-water observations, not isolated cache
allocation measurements. Thirty-turn inspection was 0.754 ms slower. No broad
startup or memory-footprint improvement is claimed. Raw samples and every
signed delta remain in the comparison receipt.

## Limits and remaining external measurements

Full history scans, checkpoint verification/serialization, and ledger growth
remain. This pass does not demonstrate arbitrarily large conversations or
unbounded parallel inference. Sealed storage correctness remains covered by the
suite, but encrypted-storage performance is not measured here. Linux package
and emulated viewport checks do not validate native release binaries or physical
devices.

Astra remains a replaceable model capability through the existing provider
boundary. No concrete Astra endpoint, model identifier, credentials, or
provisioned inference hardware was supplied for this pass. Live Astra swaps,
model latency, token usage, streamed output, and semantic answer quality remain
unverified. Reference A/B controls do not substitute for those measurements.
Automatic model selection or reasoning escalation was not added without
capability, quality, and cost evidence. Persistent substrate and host authority
remain independent of the selected provider.
