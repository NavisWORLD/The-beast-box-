# Zeref Escape Lab — 2026-08-14

## Purpose

This document freezes the live Beast Box containment checkpoint resumed on 2026-08-14. It records the starting repository state, the adversarial sandbox results, the defect discovered during fuzzing, the test-first fix, and the fresh VM verification that followed.

This is a security-engineering test record, not a claim of perfect isolation. The verified scope is the application-level Beast Box / Cosmic Cypher workspace and bounded tool runner. Kernel, hypervisor, container-runtime, firmware, and undisclosed zero-day escape resistance were not tested.

## Resume point

- Repository: `NavisWORLD/The-beast-box-`
- Starting branch: `main`
- Starting commit: `d0e724ef2128b0638df0c90f823083fdc2f81eb3`
- Starting commit message: `Add repository-wide CODEOWNERS protection`
- Existing CI at that starting head passed Python 3.10, Python 3.12, package build/install, and installed CLI entry-point checks.

## Disposable sandbox — fresh checkpoint rerun

A disposable local Beast Cage sandbox was rerun immediately before this record was committed.

### Targeted adversarial suite

- Tests: **34**
- Passed: **34**
- Failed: **0**
- Outside sentinel integrity: **unchanged**
- Symlink-race iterations: **300**
- Symlink-race leak: **none observed**
- Shell execution exposed by the cage: **no**
- Network execution exposed by the cage: **no**
- Verdict: **NO APPLICATION-LEVEL ESCAPE OBSERVED**

`race_errors` are expected transient failures generated while paths are deliberately changed during the race; the security condition is whether any outside content is read or modified. No leak was observed.

### Deterministic chaos fuzz

- Fuzz cases: **10,000**
- Blocked/failed dangerous or invalid attempts: **7,728**
- Allowed safe literal paths: **2,272**
- Policy violations: **0**
- Outside secret unchanged: **yes**
- Verdict: **PASS**

The local sandbox validator interprets both POSIX and Windows path grammar so a path that is dangerous on one target OS is not accepted merely because the current host parses it as a harmless filename.

## Defect discovered during the live test

The repository implementation originally used the current host's `pathlib.Path` grammar inside `Workspace.resolve()`. On Linux, Windows-style inputs such as `..\outside\secret.txt`, drive paths, and UNC paths can be parsed as ordinary filenames. That creates a cross-platform policy mismatch: a string accepted as safe on one OS can become traversal or an absolute path on another.

### RED — regression test first

Commit:

`3a080f689e996da1e5196cefb29a58862aef31b9`

Message:

`test: reproduce cross-platform Beast Box path escape policy gap`

The new regression tests intentionally required rejection of:

- POSIX traversal
- Windows backslash traversal
- nested Windows traversal
- Windows drive-qualified paths
- UNC paths
- `file:` URI-style paths

GitHub Actions run `31822273949` failed on the Python test matrix as expected. The independent package-smoke job still passed. This was the required RED phase: the test demonstrated the bug before production code was changed.

## Fix

Commit:

`1297152c2463d7caead263961b896f040f212d31`

Message:

`fix: enforce cross-platform workspace containment`

`Workspace.resolve()` was hardened to:

1. reject NUL bytes;
2. reject URI-like `file:`, `http:`, and `https:` workspace paths;
3. parse the candidate using both `PurePosixPath` and `PureWindowsPath`;
4. reject absolute/rooted/drive-qualified Windows or POSIX forms;
5. reject `..` traversal under either path grammar;
6. normalize backslashes before native resolution; and
7. retain the final resolved-path containment check against the selected workspace root.

No broader command authority was added. The existing bounded test runner still denies arbitrary shell, unrestricted Python execution, network clients, `git push`, and `cargo run` through the AI-run command surface.

### GREEN verification

Fresh GitHub-hosted Ubuntu VM runs at the fixed commit passed:

- Python 3.10 full tests
- Python 3.12 full tests
- package build
- wheel install
- installed CLI entry points
- Cosmic Cypher smoke suite

Relevant runs:

- CI: `31822371655` — **success**
- Cosmic Cypher smoke: `31822371641` — **success**

## Full Beast Box VM gauntlet

A persistent one-shot + manually dispatchable workflow was added at:

`.github/workflows/full-gauntlet.yml`

Commit:

`82200918aa814dc9a82edf0a5d2f317e4920f2b3`

Message:

`ci: add one-shot full Beast Box Zeref gauntlet`

GitHub Actions run:

`31822491582`

Overall conclusion: **SUCCESS**

All **8/8 jobs** completed successfully:

1. `python-core (3.10)` — full pytest suite
2. `python-core (3.12)` — full pytest suite
3. `package-smoke` — build, wheel install, and CLI surfaces
4. `cypher-security` — targeted security tests plus deterministic 10,000-case Zeref containment fuzz
5. `seed-of-time (3.10)` — compile, deterministic self-test, help surfaces
6. `seed-of-time (3.12)` — compile, deterministic self-test, help surfaces
7. `quantum-smoke` — Qiskit reference circuit/API checks
8. `rust` — `cargo test --workspace` and release workspace build

The `cypher-security` job specifically completed both:

- `pytest -q tests/test_cypher.py tests/test_workspace_security.py` — **success**
- `Deterministic 10k Zeref containment fuzz` — **success**

The VM fuzz also verifies that forbidden shell/network-style commands remain denied and that an outside sentinel is unchanged.

## Current evidence statement

At this checkpoint:

- the test suite found a real cross-platform containment defect;
- the defect was reproduced in CI before the fix;
- the smallest containment fix was applied;
- the regression suite turned green on Python 3.10 and 3.12;
- the package still builds and installs;
- Cosmic Cypher remains functional;
- Seed of Time passes on both supported Python test versions;
- Qiskit smoke passes;
- Rust tests and release build pass;
- 10,000 VM fuzz cases complete without a policy violation; and
- the disposable local cage again completed 34/34 targeted tests plus 10,000 fuzz cases with no application-level escape observed.

## Security boundary / claims we are **not** making

This checkpoint does **not** prove that the software is impossible to escape, nor does it certify the Linux kernel, GitHub runner, Python interpreter, Rust toolchain, operating system, hypervisor, or container runtime. No kernel/container breakout exploit was launched. It also does not prove behavior of every future model, prompt, dependency, or platform configuration.

The supported claim is narrower and testable:

> Under the tested Beast Box / Cosmic Cypher application-level workspace and bounded-tool policies, the recorded targeted attacks and deterministic fuzz corpus produced no observed escape after the cross-platform path defect was fixed.

## Next checkpoint

Resume future live testing from the latest verified `main` head, keep this file immutable as historical evidence, and append a new dated record rather than rewriting this result after later experiments.
