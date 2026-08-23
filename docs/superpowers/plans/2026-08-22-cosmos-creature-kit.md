# COSMOS Creature Kit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a creator-ready COSMOS Creature SDK and distribution kit with honest weight/GGUF handling, reusable CST state helpers, isolated IBM/Azure/classical bridges, doctor tooling, templates, examples, and installable CLI.

**Architecture:** Keep executable behavior in `beastbox.creature` and make `COSMOS_CREATURE_KIT/` a distribution/documentation layer that imports or invokes the package. Reuse the existing Trinity and IBM broker code rather than cloning math or credential logic. All provider outputs cross a sanitized 12D receipt contract before state composition.

**Tech Stack:** Python 3.10+, setuptools, pytest, existing Beast Box Trinity runtime, hashlib/json/pathlib, optional IBM/Azure HTTP integrations, GGUF-compatible external converters when available.

**Spec:** `docs/superpowers/specs/2026-08-22-cosmos-creature-kit-design.md`

## Global Constraints

- Never store or expose IBM, Azure, Hugging Face, or other cloud credentials in model context, receipts, manifests, evidence, examples, or logs.
- Native QC67/Spark `.pt` checkpoints are not labeled GGUF unless a real converter succeeds.
- Default state architecture is validated 12D -> 42D -> balanced 54D using the existing Trinity implementation.
- Cloud inputs are provenance/state sources only. No quantum advantage, consciousness, autonomy, or intelligence claim is implied.
- CI support remains Python 3.10 and 3.12.

---

### Task 1: Creature manifest and project creation

**Files:**
- Create: `tests/test_creature_manifest.py`
- Create: `beastbox/creature/__init__.py`
- Create: `beastbox/creature/manifest.py`
- Create: `beastbox/creature/project.py`

**Interfaces:**
- Produces `CreatureManifest.from_dict`, `CreatureManifest.load`, `CreatureManifest.save`, `create_creature_project(name, root)`.

- [ ] Write failing tests for valid/invalid manifests and project creation.
- [ ] Run `pytest -q tests/test_creature_manifest.py` and confirm RED because `beastbox.creature` is missing.
- [ ] Implement manifest validation and creator project scaffolding.
- [ ] Re-run the focused tests and confirm GREEN.

### Task 2: Weight vault and honest GGUF tooling

**Files:**
- Create: `tests/test_creature_weights.py`
- Create: `beastbox/creature/weights.py`
- Create: `beastbox/creature/gguf.py`

**Interfaces:**
- Produces `sha256_file`, `inspect_weight`, `build_weight_manifest`, `export_gguf`.
- `export_gguf` must reject fake extension-only conversion and may run an explicit external converter command.

- [ ] Write failing tests for hashing, manifest fields, format inference, and fake-conversion refusal.
- [ ] Verify RED.
- [ ] Implement minimal weight/manifest/GGUF behavior.
- [ ] Verify GREEN.

### Task 3: Bridge receipt contract and provider adapters

**Files:**
- Create: `tests/test_creature_bridges.py`
- Create: `beastbox/creature/bridges.py`

**Interfaces:**
- Produces `BridgeReceipt`, `classical_receipt`, `ibm_receipt_from_resident`, `azure_receipt_from_payload`, `validate_receipt`.

- [ ] Write failing tests for 12D shape, finite values, secret-key rejection, freshness, deterministic classical state, IBM adaptation, Azure sanitization.
- [ ] Verify RED.
- [ ] Implement bridge contract and adapters.
- [ ] Verify GREEN.

### Task 4: Spark/Trinity state library

**Files:**
- Create: `tests/test_creature_spark.py`
- Create: `beastbox/creature/spark.py`

**Interfaces:**
- Produces `compose_creature_state(entropy12)`, `zero_state_report()`.

- [ ] Write failing tests asserting exact lengths 12/42/54, zero input, projection hashes, and balanced-54 metadata.
- [ ] Verify RED.
- [ ] Wrap the existing `compose_trinity_state` and state datatypes.
- [ ] Verify GREEN.

### Task 5: Loops, doctor, and CLI

**Files:**
- Create: `tests/test_creature_doctor_cli.py`
- Create: `beastbox/creature/loops.py`
- Create: `beastbox/creature/doctor.py`
- Create: `beastbox/creature/cli.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces `build_state_packet`, `doctor_project`, `cosmos-creature` CLI.

- [ ] Write failing tests for fresh-receipt state packets, doctor pass/fail, project creation CLI, weight inspection CLI.
- [ ] Verify RED.
- [ ] Implement loops, doctor, argparse CLI, and entry point.
- [ ] Verify focused GREEN.

### Task 6: Creator distribution kit and libraries

**Files:**
- Create: `COSMOS_CREATURE_KIT/README.md`
- Create: `COSMOS_CREATURE_KIT/QUICKSTART.md`
- Create: `COSMOS_CREATURE_KIT/ecosystem-manifest.json`
- Create: `COSMOS_CREATURE_KIT/libraries/README.md`
- Create: `COSMOS_CREATURE_KIT/weights/README.md`
- Create: `COSMOS_CREATURE_KIT/weights/native/README.md`
- Create: `COSMOS_CREATURE_KIT/weights/gguf/README.md`
- Create: `COSMOS_CREATURE_KIT/weights/adapters/README.md`
- Create: `COSMOS_CREATURE_KIT/weights/tools/inspect_weights.py`
- Create: `COSMOS_CREATURE_KIT/weights/tools/build_manifest.py`
- Create: `COSMOS_CREATURE_KIT/weights/tools/export_gguf.py`
- Create: `COSMOS_CREATURE_KIT/bridges/README.md`
- Create: `COSMOS_CREATURE_KIT/config/creature.example.json`
- Create: `COSMOS_CREATURE_KIT/config/secrets.example.env`
- Create: `COSMOS_CREATURE_KIT/examples/hello_creature.py`
- Create: `COSMOS_CREATURE_KIT/examples/classical_state.py`
- Create: `COSMOS_CREATURE_KIT/examples/ibm_receipt.py`
- Create: `COSMOS_CREATURE_KIT/examples/azure_receipt.py`
- Create template `creature.json` manifests under `templates/blank-creature`, `local-creature`, `ibm-creature`, `azure-creature`, `hybrid-creature`.
- Create: `COSMOS_CREATURE_KIT/evidence/README.md`

**Interfaces:**
- Distribution scripts import `beastbox.creature`; they do not fork runtime behavior.

- [ ] Add a filesystem contract test ensuring required kit files and template manifests exist.
- [ ] Verify RED.
- [ ] Add docs, examples, templates, and thin tool wrappers.
- [ ] Verify GREEN.

### Task 7: Package/CI verification and documentation integration

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`

**Interfaces:**
- CI invokes `cosmos-creature --help` after built-wheel installation.

- [ ] Update package-smoke command list and README creator-kit section.
- [ ] Run full CI on the feature branch.
- [ ] Confirm Python 3.10 and 3.12 tests are green and wheel install exposes `cosmos-creature`.
- [ ] Inspect failures and fix root causes without weakening tests.
- [ ] Open a PR only after fresh green verification evidence.
