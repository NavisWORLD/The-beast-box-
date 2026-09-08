# Beast Box Cosmic Interface Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing Tk desktop client into one coherent COSMIC.CYPHER operating surface over the authoritative `DurableRuntime`, exposing verified memory, provider, optional-input, portable-state, workspace, files, observability, privacy and lab controls without moving authority into the model or UI state.

**Architecture:** Preserve `DurableRuntime` as the sole transactional substrate and add narrow host-side product services around existing APIs. Desktop pages are clients of those services; permissions are session grants, credentials remain host-only, and unsupported hardware/providers fail closed. Historical model-swap evidence is read-only and untouched.

**Tech Stack:** Python 3.10–3.12, stdlib Tk/ttk, SQLite-backed `DurableRuntime`, existing Beast provider/sensor/portable-state APIs, optional OS/device libraries only behind import/permission gates.

**Spec:** User-supplied Beast Box Cosmic Interface Completion brief, 2026-09-07.

## Global Constraints

- `MODEL != MEMORY`, `MODEL != STATE`, `MODEL != PROVENANCE`, `MODEL != AUTHORITY`, `MODEL != WHOLE SYSTEM`.
- State/information may travel; authority never transfers automatically.
- No secret values in conversation memory, R12, evidence, prompts, exports, logs or crash text.
- No camera/microphone/cloud/quantum/repository-write activation without an explicit host grant.
- No silent model fallback. Provider identity is recorded on every turn.
- Frozen experiment evidence and historical failures/nulls are never rewritten.
- Camera/voice/physical-device/cloud capabilities are reported at their measured boundary, never inferred from documentation.
- Scientific labels remain software instrumentation; no consciousness, medicine, quantum-advantage or new-physics claims.

---

### Task 1: Product service contract and capability inventory

**Files:**
- Create: `beastbox/product_services.py`
- Create: `tests/test_product_services.py`
- Create: `docs/COSMIC_INTERFACE_CAPABILITIES.json`

**Interfaces:**
- Produces `AuthoritySession`, `ProductService`, `FileContext`, `WorkspaceGrant`, `capability_inventory()`.
- `ProductService` owns no durable state; every durable operation opens the existing `DurableRuntime` through the serialized desktop worker boundary.

- [ ] Write failing tests for default-deny authority, capability inventory vocabulary, bounded file inspection, workspace root confinement, resource status sanitization and portable export/import authority exclusion.
- [ ] Run the targeted tests and record RED because the module does not exist.
- [ ] Implement the minimal host-side service contract using current runtime APIs.
- [ ] Re-run targeted tests and existing desktop/runtime tests.
- [ ] Commit the green slice.

### Task 2: Provider bay and secret boundary

**Files:**
- Modify: `beastbox/desktop.py`
- Create: `beastbox/secret_store.py`
- Modify: `beastbox/providers.py`
- Extend: `tests/test_product_services.py`, `tests/test_desktop.py`

**Interfaces:**
- `ProviderSettings` supports reference, Ollama and compatible Chat Completions without storing secret values.
- `SecretStore` uses an OS keyring when available and otherwise reports unavailable rather than silently writing plaintext secrets.

- [ ] Write failing tests for compatible provider construction, remote HTTPS opt-in, secret-reference-only persistence and redaction.
- [ ] Verify RED.
- [ ] Implement provider construction and OS-keyring boundary; never include the credential in settings or receipts.
- [ ] Verify targeted and provider tests.
- [ ] Commit.

### Task 3: Memory Vault and Synapse Trace

**Files:**
- Modify: `beastbox/memory.py`, `beastbox/durable.py`, `beastbox/product_services.py`
- Extend: `tests/test_product_services.py`

**Interfaces:**
- `memory_records(limit, kind)`, `memory_search(query, limit)`, `trace_summary()` return bounded owner-facing data.
- Trace exposes stages, hashes, routing IDs, provider metadata, policy/tool outcome and checkpoint metadata, never private model chain-of-thought.

- [ ] Write failing tests for bounded listing/search and trace redaction.
- [ ] Verify RED.
- [ ] Implement read-only memory/trace inspection through the runtime database and safe receipts.
- [ ] Verify tests and checkpoint integrity.
- [ ] Commit.

### Task 4: Files and read-only workspace

**Files:**
- Modify: `beastbox/product_services.py`
- Extend: `tests/test_product_services.py`

**Interfaces:**
- `inspect_file(path, persistent=False)` accepts only bounded safe text/source/JSON/CSV/image/WAV metadata paths supported by current tooling; unsupported formats are explicit.
- `WorkspaceGrant` canonicalizes an allowlisted root; reads cannot escape it; repository write is denied unless a separate session authority is granted.

- [ ] Write failing traversal, symlink, oversize, executable and temporary-vs-persistent tests.
- [ ] Verify RED.
- [ ] Implement bounded file hashing/preview and workspace read-only browse/read operations.
- [ ] Verify tests.
- [ ] Commit.

### Task 5: Reality, Listen and Q-Bay adapters

**Files:**
- Modify: `beastbox/product_services.py`
- Extend: `tests/test_product_services.py`

**Interfaces:**
- Existing `wav_event`, `light_event`, `resource_status`, `quantum_event` are exposed as explicit host actions.
- Live quantum submission requires both a session authority grant and the existing `allow_live=True` gate.

- [ ] Write failing tests proving WAV/light are local bounded observations and Q-Bay is denied by default.
- [ ] Verify RED.
- [ ] Wire existing adapters; surface configuration status only, never secret values.
- [ ] Verify tests.
- [ ] Commit.

### Task 6: Camera, microphone and voice honest capability adapters

**Files:**
- Create: `beastbox/media_devices.py`
- Extend: `tests/test_product_services.py`

**Interfaces:**
- Camera/mic methods require explicit session grants before importing/opening device libraries.
- Missing libraries/devices return a typed unavailable state without opening hardware.
- Any local observation is bounded and labelled derived; raw media is not cloud-routed by default.

- [ ] Write failing tests with imports blocked to prove default-deny and fail-closed behavior.
- [ ] Verify RED.
- [ ] Implement optional-device boundaries and stop/close semantics.
- [ ] Verify tests. Physical validation remains external unless hardware is present.
- [ ] Commit.

### Task 7: COSMIC.CYPHER desktop information architecture

**Files:**
- Modify: `beastbox/desktop.py`
- Create: `beastbox/cosmic_theme.py`
- Extend: `tests/test_desktop.py`

**Interfaces:**
- Pages: ORBIT, BRAIN, BRAIN BAY, VISION, LISTEN, VOICE, REALITY, MEMORY VAULT, SYNAPSE TRACE, FILES, WORKSPACE, Q-BAY, CONNECTIONS, AUTHORITY, SETTINGS.
- Basic/Advanced/Lab modes hide complexity but never remove capability/status truth.

- [ ] Write failing headless tests for navigation metadata, status badges, model-swap banner and master privacy-stop state transition.
- [ ] Verify RED.
- [ ] Implement cosmic dark theme, navigation rail, page frames, dashboard cards and service-backed controls using Tk/ttk only.
- [ ] Verify headless service/UI metadata tests and desktop smoke.
- [ ] Commit.

### Task 8: Docs, security audit, packaging and acceptance

**Files:**
- Create/update user guides for UI/providers/camera/audio/voice/files/workspace/memory/sensors/Q-Bay/storage/authority/privacy.
- Modify CI only where needed to exercise the new desktop/service surface.

- [ ] Add a machine-readable final feature matrix with the required status vocabulary.
- [ ] Run targeted tests, full pytest/quality, security audit, architecture acceptance and package smoke.
- [ ] Run desktop smoke from installed package.
- [ ] Inspect CI on the exact branch head; fix regressions through test-first commits.
- [ ] Create PR only after fresh verification; merge only if required gates are green and GitHub permits it.
