# CI hierarchy

The repository contains dozens of GitHub Actions workflows. Only a few are ordinary product CI.

## Required product CI

- `.github/workflows/ci.yml`
- `.github/workflows/product-ci.yml`
- `.github/workflows/cypher-smoke.yml`
- `.github/workflows/security-audit.yml`
- `.github/workflows/package.yml`

## Release CI

- `.github/workflows/release.yml`
- productization receipt: `python scripts/productization_receipt.py --check-only`
- sealed-evidence guard: `git diff --exit-code c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f -- evidence/final-whole-organism-001/`

## Scientific / evidence CI (manual or explicit protocol)

- `cosmos-final-scientific-closure.yml`
- `cosmos-final-organism-ignition.yml`
- `cosmos-final-*.yml`
- `full-gauntlet.yml`
- `quantum-smoke.yml`

## Historical / archived workflows (retain, do not advertise)

Zeref talk gauntlets, dad/son runs, networked-cage, HF publish triggers, D001 proofs, autonomous-hands kits, rust CST, macOS DMG.
