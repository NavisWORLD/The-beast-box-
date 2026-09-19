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
