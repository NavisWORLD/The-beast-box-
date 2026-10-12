# Zeref 012A — recorded-measurement conditioning mechanism (adapter only)

This stage uses the **already approved** RAWRPHØS/Zeref 006-cycle-3 parent (`d0df90ea090b410aa5da5051b20e21ae5728236f7371450807f1af662fb02445`), rather than retraining the rejected Zeref 011 checkpoint or replacing the current website model.

**Question:** Can a zero-impact external-state adapter learn to make this exact frozen language model's token scores responsive to a measured numerical feature when the feature and target are deliberately aligned? This is an **engineering mechanism experiment**, *not* an empirical claim that quantum hardware improves gameplay or dialogue.

## Source and restrictions

The offline corpus was merged in PR #315; its publisher proof, SHA-256 manifest and exact held-out file digests are checked before this run. There are 5,706 distinct published IBM source records (25,691,580 shots, 282 source jobs), but a training/evaluation *candidate* cohort of 3,121 distinct count distributions after moving the other 2,585 exact-count-equivalent records to the audit-only partition. These were independent archived jobs, not 2,585 fabricated or invalid records. The selected IBM data are partitioned by SHA-256 job split; neither identical counts nor jobs cross partitions.

The 24 Azure Rigetti QVM simulator batches are retained separately, **not included** in this IBM mechanism run or relabeled as physical IBM measurements. No additional hardware/QVM provider requests, account data, private chat history, or visitor records are used.

## Actual training mechanism

- Load and SHA-256 verify the **approved 006 parent** artifact and its owner approval manifest. Preserve its optimizer history unaltered.
- Freeze **every RAWRPHØS parameter**. Attach an independent `12 -> 32 -> 12` adapter, initially with an exactly zero output projection, to the existing model's `control_vector` input and Dyn12 attention. The unconditioned logits must be bit-identical before and after training.
- Numerical values are **twelve bounded classical statistics derived from measured count distributions**, not twelve independent qubits.
- Readout task: output digit `1` only if the feature's *even-parity probability* exceeds the **training-only median**, otherwise `0`. The target is explicitly derived from an input feature. Success proves the adapter can read numerical conditioning; it **cannot** support an independent signal, physical quantum advantage, conversational learning, world-model improvements, or better game decisions.
- Compare four identically budgeted 32-update arms: correctly paired recorded IBM features; shuffled IBM features; independent SHA-256-derived classical vectors; and a constant classical feature baseline. Hold out unseen file/job/count groups. Record accuracy, two-class NLL, initialized and final model parameter hashes, reproducibility seed, optimizer updates, adapter-weight SHA-256, and per-arm results.
- Persist **only the adapter weights** as research artifacts, never a replacement Zeref model. No automatic acceptance or promotion. The unmodified parent checkpoint, ROM, creature sprite assets, and public website are the only production authorities.

## Reproduction / evidence

GitHub Actions `zeref-012a-conditioning-mechanism.yml` installs CPU-only Torch and the in-repo native RAWRPHØS package, regenerates/hash-checks the complete IBM conditioning files, downloads the pinned approved parent from run `38179059173`, runs the unit tests, performs the bounded four-arm adapter training, verifies that the parent was unchanged, and uploads a JSON report plus adapter-only safetensors.

Training is restricted to 128 steps maximum by the script, though this workflow uses 32. No acceptance threshold is secretly selected from the final test set. Report all arms, including failures, independently of whether any measured feature appears useful.

## Required next stage before *behavioral* claims

For future training that might improve Lost COSMOS play or conversation, obtain genuinely temporally/task-aligned measurement and experience pairs. Compare against identical classical, shuffled, QVM and no-conditioning controls; preserve train/eval job separation; measure native-game legal actions, visited-cell coverage, blocked moves, generalization, and chat retention; then allow promotion only when every predeclared gate passes. Zeref 011 remains rejected (its G4 and G9 failed); nothing here overrides that result.

Sprite, animation, Game Boy UI, iPhone scrolling/audio and model-route polish remain a separate later release.

## First completed CPU observation (run 38318767080, 2026-10-12)

All four arms completed **32 real adapter-only AdamW optimizer steps**, passed research evidence checks, and uploaded separate adapter-only safetensors. The approved parent checkpoint hash was verified and remained unchanged, including unconditioned outputs. Five dedicated Python contract tests also passed.

| Arm | Held-out balanced accuracy (24 examples) | Two-class NLL |
| --- | ---: | ---: |
| Frozen parent, no adapter | 0.50 | 0.702864 |
| Recorded IBM features, correctly paired to the derived readout label | 0.50 | 0.694715 |
| Shuffled IBM features | 0.50 | 0.700328 |
| Independent classical vectors | 0.50 | 0.702520 |
| Constant classical features | 0.50 | 0.700480 |

Report SHA-256: `4366f0fff0e3950d2b901972f786205f0a88a777366507a705ae12a2b4830176`. Evidence: https://github.com/NavisWORLD/The-beast-box-/actions/runs/38318767080 .

**Interpretation:** The adapter genuinely received optimizer updates and can be stored independently, but all arms remain at chance-level held-out accuracy. A small IBM-arm NLL difference does not prove generalization, useful Zeref behavior, quantum advantage, or a passing descendant. Do **not** promote the adapter to live chat or gameplay. Any subsequent pass needs a predeclared stronger task, meaningful temporal pairing, more seeds and behavior gates.
