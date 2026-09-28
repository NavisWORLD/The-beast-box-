# RAWRPHØS progress

- Branch: `feature/rawrphos-native-model-001`.
- Starting main: `d2ae2c9f140a9ccdbf0eaa4268eeace67a50212a`.
- The interrupted session's scratch implementation and local commit `549e975`
  did not survive. Remote branch and Library search contained no recoverable
  RAWRPHØS artifact. No prior RAWRPHØS training is claimed.
- PR #98 is still open at `7bc8899903e012e173ac48ded616df578004e48f`.
  This branch does not merge or overwrite that independent interface work.
- Published PHOS source recovered again from QC67; native model construction
  remains isolated in this directory. Historical weights remain untouched.
- Recovery boundary persisted remotely at `dab63d70902de9e3604f817f6f5e301594f4d9fb`.
- Architecture milestone: 8 tests passed on actual PyTorch CPU: all five controls
  are causal; full versus chunked KV/state cache agrees; gradients are finite and
  nonzero; probability normalization, padding and invalid contexts are checked.
- Native model weights are still untrained at this milestone.
- Training milestone: 3 tests passed covering UTF-8 BPE, corpus exclusion and
  deterministic splits, actual optimizer updates, exact split-run CPU resume,
  and corrupted checkpoint rejection. Combined model suite: 11 passed.
- CPU resource probes measured 1,861,620 / 3,909,956 / 13,509,112 parameter
  configurations. These probes use random tokens and are not quality results.
- Selected candidate: 3,909,956 parameters, 6 layers, width 256, 4 heads, 4096
  byte-BPE vocabulary target; 6000 steps x 1024 tokens = 6,144,000 planned tokens.
  The measured 13.5M configuration was substantially slower; it is not promoted
  as trained. Actual training progress will be recorded separately.
- Next executable action: finish corpus build, train from random initialization,
  and preserve each verified checkpoint. No production release or deployment.

## Training-ready milestone

- Existing regression suite: 1,138 passed (historical anchor commit fetched).
- New suite: 14 passed, including actual one-step fixture weight updates,
  authenticated API generation, no-fallback rejection and DurableRuntime restart.
  These fixture results are not the main model training result.
- Public corpus: 45,472 training documents and 5,052 held-out documents;
  105 exact duplicates and one empty document excluded. Sources, licenses and
  hashes are recorded in `data/acquisition.json` and `data/dataset_manifest.json`.
- Full near-duplicate build initially stalled on excessive candidate intersections.
  Profiling located the cost. Two-of-four minhash signatures and a necessary
  length bound reduce work while retaining an explicitly probabilistic screen.
  Complete rebuild: 25.824 seconds; near-duplicate behavioral test passes.
- Next executable action: run `python -m rawrphos.training.train` with committed
  configurations for the 3,909,956-parameter native candidate.

Budget remains the owner's existing $5/month hosting/trial ceiling. This run
uses available workspace CPU only. No GPU/QPU/paid model calls are authorized.


## First durable native CPU training receipt — September 22, 2026

- Source commit trained: `d13d5a917b76891f36cd2b4e13dee88e3b45922c`.
- GitHub Actions run: https://github.com/NavisWORLD/The-beast-box-/actions/runs/35782780734
- Pinned source acquisition, reconstructed corpus manifest and all split hashes: passed.
- Full native model test suite, including actual weight-update/resume tests: passed.
- **Real model optimizer steps:** 100. **Training tokens:** 102,400.
- Last observed training loss: `5.645643`; held-out validation loss: `5.907733`.
- SHA-256 of `model.safetensors`: `46e2f7d611eb5b959fef1bc754b8d55be2f7b21cff221a6c48f4d2f77d47bda8`.
- Recovery bundle SHA-256: `b515204207903d77225c14031171ccbf2d872624553e3b538f68283ba727eced`.
- Immutable run-specific [step-100 recovery release](https://github.com/NavisWORLD/The-beast-box-/releases/tag/rawrphos-native-step-00000100-run-35782780734) includes weights, tokenizer, optimizer state, RNG state, manifest, checksums, and a verified generated-output receipt.
- The training run continues toward the committed 6,000-step target; this milestone is **not** full training completion or a production release.
