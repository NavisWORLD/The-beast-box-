# COSMOS 006: independently trained dyn12 causal ablation (preregistered)

**Question:** Does the native dyn12 attention mechanism improve heldout in-context associative retrieval compared with (1) independently trained standard attention and (2) independently trained, deliberately shuffled-state attention, with identical starting tensors, data, hyperparameters and optimization steps? A positive observation is a synthetic candidate effect, not a proven novel intelligence advantage.

This fixes the prior #147 confound: changing attention mode at inference in an already dyn12-trained model is not a trained-standard baseline. Here all three actual existing RawrphosLM attention modes are trained independently from exactly matched initialized parameter tensors. Standard mode has *inactive allocated state parameters*, so equal total allocation does not imply equal active capacity or measured FLOPs; shuffled-state is a distinct state-active control, not a perfect mechanistic match.

## Locked fixtures and budgets

The native source code in scripts/cosmos_dyn12_controlled_006.py is the protocol. Vocabulary 24; each episode binds three randomly drawn unique keys to three independently random unique values, then asks for one of the episode-specific earlier values. No fixed key-to-value mapping can be memorized. A withheld four-key episode distribution is an additional sequence-length-shift test.

Use exactly seeds **11, 29 and 47**. Each generates 1,536 distinct train, 128 distinct development, 256 distinct hidden test and 128 distinct four-binding-shift episodes without any repeated full example across splits. Training sees only train tuples; all test labels are used only in final scoring. No validation-guided early stopping, source alteration or tuning to favorable results.

Model: native 2-layer RawrphosLM, hidden width 64, four heads, 12 carried state dimensions, sequence length at most 16, vocabulary 24. For every arm use the exact same initial tensor hash for a seed, exact same 1,440 train minibatch examples in the same order, exactly 120 AdamW updates, batch 12, learning rate 0.003, no weight decay and clip-norm 1, single-thread CPU. Three arms per seed are dyn12, standard and shuffled_state.

Before training require demonstrably active dyn12 state, gate and sigma gradients; nonzero initial dyn12-versus-standard logits; causal earlier logits invariant to a changed future token; and normalized active-gate attention. Fail a mechanistically inert result before inspecting heldout scores. After training report accuracy and target cross-entropy on dev, test and shifted episodes and a diagnostic *same-dyn12-trained-weights* zero_gate/shuffled_state intervention. Inference interventions must not be counted as separately trained controls.

## Preregistered, deliberately conservative observation gate

An exploratory synthetic candidate pattern requires dyn12 test accuracy at least **0.03 absolute above both trained standard and trained shuffled_state in ALL three seeds** and dyn12 mean four-key shift accuracy no more than **0.02 absolute below** standard. Report all signed per-seed differences whether favorable, null or negative. Code CI must pass with negative outcomes. With three correlated seeds on one synthetic task, passing this gate would **not** prove general reasoning benefit, scientific novelty, statistical significance or 12D superiority.

The next gate, if warranted by these results, requires a larger independent external task suite; separately trained models matched for active capacity and FLOPs, multiple independently frozen real-data corpora and independent reproduction. This study does not test consciousness, autonomous generative correction, physical quantum advantage or new language capability.

Only actual source in the verified repository, scratch **toy research models** and publicly available synthetic data. No original published weights mutated; no owner memory, external training corpus, paid GPUs, cloud inference API, provider deployment or automated promotion. CI CPU matrix has bounded resource limits and preserves full original numeric per-seed receipts and a combined report.
