# OMEGA — Activation Report (Directives 002–010)

Reproducible entrypoint: `python scripts/omega_activation.py --output ./omega-receipt.json`
(needs `PYTHONPATH=.`; stdlib only, no paid services, no network, no GPU).

## What was built on the existing system

- `beastbox/omega/loop.py` — the organism pipeline with per-stage provenance:
  SENSORS (`normalize_event`) → CNS7 (`CNS.tick`) → 12D (`update_dyn12`) →
  HEBBIAN + MEMORY (`ReconciliationMemory`) → R12 (`RefractiveMemoryRouter`) →
  SYNAPSE (`SynapticField`) → MODEL (replaceable `TextProvider`) →
  AUTHORIZED ACTION (`bounded_output` + `AuthorityPolicy`) → FEEDBACK → MEMORY.
  Every numeric value is computed by the production module it names.
- `beastbox/omega/operator.py` — continuous event-driven operation with
  persistent tasks (consolidation/health), budgets (`max_steps`/`max_ms`/
  `max_tool_calls`), cancellation, host authorization, graceful stop and
  emergency stop. A stopped model never destroys the substrate
  (verified: `substrate_survives_estop`).
- `beastbox/omega/sandbox.py` — disposable autonomy world: filesystem confined
  to one root, network denied by construction, execution confined to an
  allowlist, proposals require host approval, policy immutable after
  construction (the sandbox cannot grant itself authority).
- `beastbox/omega/experiments.py` — preregistered H1/H2/H3 with controls and
  preserved nulls (see below).
- `beastbox/omega/self_improve.py` — bounded self-improvement rig: immutable
  baseline checkpoint, disposable candidate copy, forbidden targets/tokens
  (authority, monitoring, promotion paths), trusted host evaluator on held-out
  workloads, external rollback, promotion never automatic.
- `beastbox/omega/web.py` + `beastbox/cosmic_web.py` routes + `html/omega.html` —
  live control deck polling real telemetry (`/api/omega/recovery`,
  `/api/omega/step`, `/api/omega/experiments`).
- `beastbox/omega/recovery.py` + `docs/OMEGA_RECOVERY_MAP.md` — Directive 001 inventory.
- `beastbox/omega/telemetry.py` — JSONL recording of real stage telemetry.

## Latest activation receipt (stdlib reference providers)

| Check | Result |
| --- | --- |
| Substrate inventory | 6/22 CONNECTED (narrow probe; rest present/importable) |
| Teach → retrieve hit count | 4 |
| Model swap A→B→A preserved | true (memory + dyn12 bit-identical at swap instant) |
| Restart recovered (memory + dyn12 + turn) | true |
| Restart recall works | true (709 chars) |
| Sandbox approved executed | true |
| Sandbox unapproved denied | true |
| Sandbox network | denied |
| Operator steps drained | 2 |
| Operator e-stop | estop, substrate survives |
| H1 model independence | PASS (substrate stable; fact recall via substrate; memory-disabled control fails) |
| H2 adaptive advantage (toy) | PASS on tiny synthetic MSE only — **does not overturn the repo's controlled 006 FAIL** |
| H3 self-correction | PASS via independent deterministic evaluator — **not** intrinsic model self-correction |

## Honest boundaries (read before citing)

- H1 PASS shows memory/context delivery across swaps, not perfect semantic
  recall, personality preservation, or weight attestation.
- H2 toy PASS is a matched-budget check on one synthetic regression task. The
  repository's rigorous three-seed controlled study (006) **failed** its primary
  advantage test; that null stands.
- H3 PASS counts corrections through an independent evaluator channel. The
  repository's blinded native-checkpoint study (005) observed **zero**
  wrong-to-right intrinsic corrections; that null stands.
- Reference providers are deterministic fixtures, not pretrained language models.
- No consciousness, AGI, superintelligence, or novel-physics claims are made or implied.
