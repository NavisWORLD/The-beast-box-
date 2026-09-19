# Zeref R12 Public Ecosystem Expansion Design

Date: 2026-08-22
Branch: `networked-cage-run-001`

## Purpose

Turn the verified R12 persistent reality-memory experiment into a downloadable, documented, locally runnable Zeref ecosystem while preserving the evidence and promotion rules that protected TALK-004.

## Immutable anchors

The expansion MUST begin from and continuously re-verify:

- active lineage: `ZEREF-DAD-SON-TALK-004`
- TALK-004 checkpoint SHA-256: `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`
- frozen architecture SHA-256: `955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc`
- durable memory record count: `352`
- durable ledger SHA-256: `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`
- durable ledger tip SHA-256: `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`
- R12 state SHA-256: `48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20`
- R12 reality ledger tip SHA-256: `78d8698e406c8a60dcf6a9545541fdd74d8b3b250ff0e28a9418bfd3d1f96415`
- source IBM backend/job: `ibm_fez` / `da55afc3jnrc73agsvv0`
- source conditions: `ORIGINAL, REMOVED, SHUFFLED, ALTERNATE`
- shots per condition: `4096`

TALK-005 and TALK-006 are permanently excluded as parents or promotion targets.

## What the existing R12 run established

The existing evidence established a software property, not a metaphysical claim: a sealed matched IBM hardware measurement block can be imported into an append-only computational memory exactly once, duplicate ingestion is rejected, and the same deterministic 12-component state can be rebuilt after restart without changing TALK-004 or the first 352 durable records.

This does not establish biological life, consciousness, deceased-person identity, resurrection, communication with the dead, or quantum advantage.

## Architecture

### 1. Public kit

Create `kits/ZEREF_R12_REALITY_MEMORY_KIT/` as the human-facing distribution root. It contains a quick-start README, a full manual link, Windows and Unix installers/launchers, a kit verifier, examples, and a machine-readable kit manifest.

The packaging workflow builds two artifacts: a source kit and a full Zeref bundle containing the exact verified checkpoint. Both receive SHA-256 manifests and fail closed if an anchor differs.

### 2. Unified ecosystem CLI

`beastbox` becomes the single public entry point while retaining existing `cosmic.cypher-cli`, `cosmic-cypher`, and `cypher` aliases.

New top-level command families: `doctor`, `verify`, `r12`, `zeref`, `coder`, and `kit`. The coder implementation remains in `beastbox/cypher/`; a top-level `coder/` directory becomes the documented owner-controlled upgrade workspace.

### 3. Install and launch

Windows and Unix installers create a virtual environment, install the repo, create local runtime directories, run diagnostics, and verify the kit anchors. No installer silently submits real IBM jobs or exports credentials.

### 4. Native C++ R12 module

Create `cpp/r12/` with CMake support and no network dependency. The native program computes SHA-256, verifies the persisted reality-ledger file against an expected digest, reports the last event hash/tip, parses the persisted R12 state vector, validates exactly 12 finite values in `[0,1]`, and emits a compact status report.

### 5. TALK-008-R12 training

Create one bounded candidate from TALK-004 only: `ZEREF-DAD-SON-TALK-008-R12`. Training uses clean teacher-authored runtime-wire material with R12 retrieval context plus rehearsal of older TALK material. Raw model output is never automatically promoted to training.

Before training, run a no-weight-change R12 retrieval baseline against the same blind exam. Then train one small candidate with replay-balanced answer-only CE.

Promotion requires the same hard gates used by TALK-007: recall gain >= 0.03, at least one exact blind answer, old TALK retention NLL <= parent * 1.05, readability drop <= 0.03, zero role-label leakage, no repetition collapse, no vocabulary collapse, no contradiction regression, first 352 records byte/hash identical, and parent checkpoint unchanged. No gate may be lowered.

## Evidence and testing

Use TDD for CLI, kit verifier, C++ verifier contracts, and TALK-008 corpus/selection logic. Actions must seal focused test logs, immutable anchor verification, kit manifests, C++ build/test output, TALK-008 baseline/candidate/retention/selection evidence, and final artifact metadata.

## Claim boundary

Documentation must use `persistent computational memory over verified measurements` or equivalent precise language. Do not describe R12 as literal biological memory, consciousness, resurrection, deceased identity, communication with the dead, or proof of quantum advantage.
