# Beast Box Endsupdate — isolated successor candidate

**Status: experimental; no production promotion.** Starting Beast Box main: `8f90e440f0f4ceba502b1a3f8637507491fb23b0` (v0.7.1).

The source under this directory is a Git-blob-identical snapshot of the 1,325 tracked files from that commit, plus a *separate* `cst_candidate/` mathematical research module. The original `beastbox/dyn12.py`, `cns.py`, memory, model, host authority and release evidence are not modified. Git history remains in the parent repository; the copied files are **not a second independent Git history**. The clone is a source snapshot, not proof of every product surface's portability.

## Run in isolation

```sh
cd Endsupdate
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -p test_cst_candidate.py -v
python run_experiment.py
python -m pytest tests -q
```

The complete copied Python distribution has the same dependency and optional services as the v0.7.1 release. Invoke its launchers only from within `Endsupdate/`, configure a NEW data directory, and never point an experimental instance at protected production memory. Install optional dependencies and local model weights separately. Verify the full copied test suite, native platforms and actual devices in an authorized environment before advertising independent release readiness.

`cst_candidate/` is NOT wired into `beastbox/` or installed as part of the existing runtime's package. It has no authorization/tool interface. There is deliberately no candidate-to-dyn12 adapter: the inputs are physical simulation quantities, not dyn12 computational features. An adapter must not be invented to force a comparison.

See `ARCHITECTURE.md`, `MATH_AUDIT.md`, `CORRECTED_CST_SPEC.md`, and `RELEASE_READINESS.md`.

## Reference-only guarded local continuity smoke

The optional `isolated_runtime.py` launcher accepts only `init`, `chat`, or `inspect`, uses the deterministic reference provider, writes only to `Endsupdate/.endsupdate-data/`, rejects symlink data roots, and does not forward secrets or model/provider endpoint variables. It does not grant shell or tool authority or automatically run IBM jobs. From inside Endsupdate:

```sh
python isolated_runtime.py init
python isolated_runtime.py chat 'hello, continue from the retained context'
python isolated_runtime.py inspect
```

For a new-process check, invoke `chat` and `inspect` as separate commands. These are software continuity smoke tests, **not** real A→B→A inference. This path-level guard is not an operating-system sandbox: run as a low-privilege user in a dedicated container/VM for stronger file isolation. Other copied launchers retain their legacy behaviors, and must not be treated as guarded by this entry point.

Source audit: `MATH_LINEAGE.md`. Additional numerical control: `run_diagnostics.py` (after `run_experiment.py`); its Decimal arithmetic re-sums rounded float64 telemetry rather than evaluating physical source inputs with arbitrary precision.

The baseline `README.md` is intentionally preserved exactly as the original Beast Box source to satisfy its product/documentation contracts. This separate document contains successor-specific information.

## Verification appendix

For a complete checkout, verify the original and copied Git source identities:

```sh
cd Endsupdate
python verify_source_snapshot.py
python -m unittest discover -s tests -p test_source_snapshot.py -v
```

The gate pins `main` baseline SHA `8f90e440f0f4ceba502b1a3f8637507491fb23b0`; the original root remains exact, and the candidate may change only two explicitly declared original source paths (`.gitignore` and the copy-specific historical-evidence receipt guard). Source additions are permitted under `Endsupdate/`. It requires the Git history to be available (`fetch-depth: 0` in CI). It reports source identity, **not** scientific validity.

A separate CI matrix builds a candidate wheel and installs it into a fresh virtual environment, verifying that its import resolves from `site-packages` outside the checkout. Native platform and full product checks remain independent gates.
