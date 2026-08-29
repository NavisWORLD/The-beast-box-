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

## Scientific / evidence protocols

Class: `EXPERIMENTAL` / `MANUAL`

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

## Why they were not bulk-disabled

Many historical workflows encode the exact branch, inputs, and confirmation flags of a sealed experiment. Converting ~200 files from `on: push` to `workflow_dispatch` would change how those protocols can be re-fired and is a separate migration.

Safe current control:

- first-class product lanes are named and documented
- `product-ci.yml` is path-scoped
- historical experiment workflows are not advertised as product CI
- product commits should be reviewed against product-ci + canonical ci + security-audit

Bulk quieting of auto-triggers remains **known debt**, not a reason to withhold the product surface.
