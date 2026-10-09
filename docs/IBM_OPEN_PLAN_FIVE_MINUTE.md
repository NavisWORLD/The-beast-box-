# IBM Open Plan: five-minute Beast Box preflight

This is an **opt-in, read-only** first step for the existing IBM Quantum
host-side implementation. It does not submit a circuit, reserve time,
regenerate a Beast, or change QBEAST identity.

## Run

1. Confirm `IBM_QUANTUM_TOKEN` is present under **Repository settings →
   Secrets and variables → Actions → Repository secrets**. Never use a
   workflow-dispatch input or public Spark form for the token.
2. Merge the manual preflight workflow into the default branch after CI review.
3. Open GitHub Actions → **IBM Open Plan — Five Minute Preflight** →
   **Run workflow**. The workflow reads only the current IBM allowance.
4. Download the seven-day `ibm-open-plan-readiness-*` artifact. It contains
   usage seconds and a hash of the instance reference, not credentials.
5. Only if it reports at least 300 QPU seconds available, develop and
   review a separately authorized **single-job** submission with
   `SamplerV2.options.max_execution_time <= 300`. No new job is authorized
   or submitted by this preflight.

## Limits and safeguards

- IBM Open Plan allowance is **600 QPU seconds in a rolling 28-day window**.
  The 300-second proposal is the *entire experiment* budget, not a per-user,
  per-creature or per-page allowance.
- This preflight accepts only IBM usage with an explicit 600-second limit
  and consistent consumed/remaining values. Unknown quota, a paid plan, a
  missing secret, or a mismatched instance means **STOP**.
- QPU seconds differ from wall-clock runtime; a queue can wait longer
  without consuming an equivalent amount of QPU usage.
- All jobs must use the Open Plan instance with a deliberate IBM-native
  job ID, count receipt, source classification, and checked usage.
- Public users providing their own IBM keys require a distinct, authenticated
  and encrypted server-side BYOK flow; never share the owner's Actions Secret
  or place a user's key in `localStorage`, HTML, or browser bundles.
- Existing Rigetti/QVM simulator records remain **SIMULATOR** and must not
  be relabeled as physical IBM QPU output.
- Azure Cosmos DB can store versioned lineage/measurement references with
  partition key `owner_or_tenant_id + QBEAST_ID` and idempotent event IDs;
  verify an actual connected Cosmos service and its ETag/partition scheme
  before writing anything. This workflow performs **no Azure writes**.
- Never silently run jobs from CI, public routes, scheduled tasks or
  browser events; direct hardware use must always be explicitly authorized.
