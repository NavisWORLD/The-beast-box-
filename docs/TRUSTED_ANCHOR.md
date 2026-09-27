# Optional product checkpoint authority — explicit trust boundary

The default Beast Box `DurableRuntime` is deliberately **unanchored**: an
internal SQLite hash chain detects corruption relative to locally retained
data, not a fully coherent privileged rewrite or rollback of that database.
Historical V1 experimental source/evidence are controlled separately by the
unchanged sealed-source guard, not by the product authority below.

## What is implemented

`beastbox.trusted_anchor` defines `ContinuityTip` (system ID, sequence,
checkpoint digest, memory digest), `ContinuityAnchor` (read latest + strictly
monotonic compare-and-swap), and a durable `SQLiteAnchorAuthority` reference.
`DurableRuntime(anchor_authority=authority)` verifies the external receipt
at startup and before each write/inspection, publishes each newly committed
checkpoint and fails closed on disagreement, missing existing-runtime
enrollment, stale CAS or post-commit authority outage. The SQLite reference
preserves a history of receipts and supports Linux/Windows SQLite locking.
[Regression tests](../tests/test_finisher_trust_anchor.py) cover coherent
database rollback, separate-process restart, outage, mismatched enrollment,
out-of-root path separation and stale updates.

The exact protocol **does not authenticate itself**. The directory-separated
SQLite reference must **not** be advertised as independent authentication
when the runtime writer and the receipt database share the same writable OS
account. Full Phase A independent authenticity requires a separately
administered service/principal/host or equivalent owner-retained immutable
receipt custody. No such production service or credential was created here,
and no historical measurements or third-party rights were changed.

## Developer / ledger-only corruption exercise

The following is a *fresh-runtime test arrangement only*. The example's
separate directory demonstrates a ledger-only rollback check; use another
administered trust domain and a secure `ContinuityAnchor` protocol client
before calling it independently authenticated in production.

```python
from pathlib import Path
from beastbox.durable import DurableRuntime
from beastbox.trusted_anchor import SQLiteAnchorAuthority

owner_anchor_dir = Path("/example/operator-witness")  # pre-provision separately
authority = SQLiteAnchorAuthority(owner_anchor_dir / "checkpoints.sqlite3")
runtime = DurableRuntime("/example/fresh-beastbox", anchor_authority=authority)
try:
    print(runtime.inspect()["anchor_mode"])  # external_cas; NOT proof of isolation
    runtime.respond("an explicitly owned test interaction")
finally:
    runtime.close()
    authority.close()
```

Never auto-enroll an existing runtime from only its own current SQLite file:
an attacker could otherwise bless a fully rewritten ledger by supplying
fake local history. Migrating existing stores requires authenticated original
witness receipts and separately approved migration logic not shipped here.
When the authority is unavailable **after SQLite committed**, preserve both
data and independent authority state for human reconciliation; never
silently repair, rewind, reset external history or resume side effects.

## Security and release boundary

The reference implementation protects against a narrower **ledger-only**
adversary that cannot modify the separately retained authority, subject to
proper administration and supported local SQLite filesystem semantics.
It is **not** a guarantee against compromised root/admin, full host rollback,
stolen trust credentials, compromised clients or external hardware failures.
Strongly authenticated production authority and comprehensive operational
failure injection remain open gates. The [threat model](THREAT_MODEL.md) and
[Finisher status](FINISHER_V2_STATUS.md) name all remaining scope limitations.
