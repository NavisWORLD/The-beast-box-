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

Budget remains the owner's existing $5/month hosting/trial ceiling. This run
uses available workspace CPU only. No GPU/QPU/paid model calls are authorized.
