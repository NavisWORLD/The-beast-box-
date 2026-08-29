# CI / Actions hierarchy

The repository contains **209** recorded GitHub Actions workflows. Most are historical experiment protocols. They are retained for reproducibility.

This hardening run does **not** delete historical workflows.

## First-class maintained lanes

These are the current product / security / package lanes:

| Lane | File | Class |
| --- | --- | --- |
| Product CI | `.github/workflows/product-ci.yml` | REQUIRED PRODUCT |
| Canonical package CI | `.github/workflows/ci.yml` | REQUIRED PRODUCT |
| Cosmic Cypher smoke | `.github/workflows/cypher-smoke.yml` | REQUIRED PRODUCT |
| Package smoke | `.github/workflows/package.yml` | REQUIRED PRODUCT |
| Security audit | `.github/workflows/security-audit.yml` | REQUIRED PRODUCT |
| Release | `.github/workflows/release.yml` | RELEASE |

`product-ci.yml` is path-filtered to product files. Canonical `ci.yml` still runs on `main` and selected productization branches and includes the sealed-evidence immutability guard.

## What actually auto-fires on a normal main product commit

Observed on `f9babdacbf7a1d3d722b2b10f31c8aee79b9e8eb` (v0.3.2 merge to main):

| Workflow | Event | Required for product release |
| --- | --- | --- |
| Product CI | push | yes |
| CI | push | yes |
| Repository security audit | push | yes |
| Cosmic Cypher smoke | push | yes |
| Quantum API smoke | push | no (optional / experimental) |

The other ~204 workflow files did **not** start on that product commit. They are already branch-filtered, `workflow_dispatch`, or otherwise gated. The noisy surface is inventory size, not 209 jobs per commit.

## Scientific / evidence protocols

Class: `EXPERIMENTAL` / `MANUAL` / `NOT REQUIRED FOR CURRENT PRODUCT RELEASE`

- `cosmos-final-*.yml`
- `full-gauntlet.yml`
- `quantum-smoke.yml`

These are not required for an ordinary product install.

## Historical / archived lineage

Class: `HISTORICAL` / `ARCHIVED-LINEAGE` / `NOT REQUIRED FOR CURRENT PRODUCT RELEASE`

Retained in place:

- `zeref-*` talk, heartbeat, R12, memory-replay, dad/son, checkpoint workflows
- `d001-*` descendant proofs
- `autonomous-hands-*`
- `networked-cage*`
- `cns7-*` IBM ignition inspect/recovery
- `qc67-*`, `hf-*` publish/probe
- `macos-zeref.yml`, `rust.yml`

## Why they were not bulk-rewritten

Many historical workflows encode the exact branch, inputs, and confirmation flags of a sealed experiment. Converting ~200 files from their recorded triggers to `workflow_dispatch` would change how those protocols can be re-fired and is a separate migration.

Safe current control:

- first-class product lanes are named and documented
- `product-ci.yml` is path-scoped
- historical experiment workflows are not advertised as product CI
- product commits should be reviewed against product-ci + canonical ci + security-audit
- observed auto-trigger set on a normal main product push is five workflows, not two hundred

Bulk rewriting of historical workflow YAML remains optional hygiene, not a reason to withhold the product surface.
