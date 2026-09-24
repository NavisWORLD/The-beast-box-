# RAWRPHØS 18K — experimental owner-only inference candidate

**Status:** candidate for optional evaluation, **NOT a passed quality promotion**. Cory Davis explicitly requested preservation and an updated Beast Box experiment. Do not assert the live deployment is updated until the exact Railway deployment and authenticated owner interaction are verified.

## Immutable source and evidence

- Training stage 008: https://github.com/NavisWORLD/The-beast-box-/actions/runs/36008364848
- Full 17.1K–18K immutable research archive (all ten 100-step checkpoints, optimizer/RNG/scheduler and evidence): https://github.com/NavisWORLD/The-beast-box-/releases/tag/rawrphos-native-research-step-00018000-run-36008364848
- Pinned 18K single-checkpoint inference package: https://github.com/NavisWORLD/The-beast-box-/releases/tag/rawrphos-native-experimental-inference-step-00018000-run-36008364848
- Model ID `rawrphos-native`, training step `18000`.
- Exact checkpoint / weight SHA-256: `20932937afb3e0e1b62a4e5f38f92170046ae2928b437dc31b8a37d6538e701e`.
- Inference archive SHA-256: `ca7da2f59b0f1aba54e2e5928e113d47d4b2da8ca48283db78500d03e39c8ec9`.
- Original 14K production rollback source: merge `e802885b3d2037c171ff312133d48ae7d26d32bd`, original 14K release remains published.
- 18K candidate is still the 3,909,956-parameter native PHOS/dyn12 model; **the separate ~10M architecture is not trained or included**.

## Measured behavior and known failures

The 18K run completed 1,000 real optimizer steps from the exact 17K parent; held-out assistant-reply loss **3.5436649966**, perplexity **34.5934721001** on this specific held-out dataset. The historical 12K conversational baseline was loss **5.2396**, perplexity **188.6**. These measurements are not general-capability scores.

The frozen **mechanical promotion gate failed 10/11**: owner-context repeated trigram fraction **0.1533224401**, above the existing maximum **0.15**. No gate was lowered or rewritten. Chat EOS 12/12; owner EOS 11/12. In the frozen samples the model answered **`no`** instead of the required `blue`, misanswered a multi-turn color question, and gave an unrelated answer to an uncertainty question. Human relevance/coherence review is not complete. **Do not call it promoted, production-quality, smart, or generally coherent.** An owner-only opt-in experiment is a separate deployment decision; a successful deployment smoke test does not reverse its failed quality gate.

## Deployment boundaries

The **Vercel app is a frontend/BFF**, not the CPU model host; the native model is loaded by the private Railway `cosmos-owner-bridge` on the loopback `127.0.0.1:8767`. The existing frontend API contract requires no new frontend code for the model catalog to show its label. Vercel connector access to `zerefs-end` returned 403 at preparation time, so an authenticated live Vercel UI check must not be claimed without restored access.

The optional model keeps the existing `rawrphos_native` owner choice and explicit error handling; all other providers must remain. The proposed label is `RAWRPHØS Native — Experimental 18K (quality gate failed)`. It must not bypass owner auth, enable tool grants, invent chat responses, or change durable COSMOS state. Because the same model ID is used, **existing selected RAWRPHØS owners can receive new experimental weights after a swap**; this behavior requires an informed rollout/rollback decision. This repo change must not by itself trigger a production rebuild.

Before merge and Railway rollout:
1. Confirm exact inference archive/download SHA, checkpoint metadata and optimizer chain; run native/bridge regression tests.
2. Pass real authenticated 18K local HTTP inference, owner model selection and chat, existing SmolLM and remote provider tests, full Docker image build, and verify resource budget and available rollback.
3. Confirm Railway production is based on merge `e802885...` and current settings preserve `/srv/beastbox/data`, variables, original provider choice, and existing Docker path.
4. Explicitly record that deploying this unpromoted model is for **owner-only experimentation**, not satisfaction of the original promotion gate; preserve the 14K image and release for rollback.
5. Check Railway deployment is actually `SUCCESS`, confirm its commit SHA and private server reports step `18000` and exact checkpoint SHA, then run authenticated owner chat before claiming availability on the website. Vercel UI may remain unverified until connector access is restored.

**Training remains paused at 18K until preservation and rollout are resolved.** Resuming to 20K must not mutate the deployed 14K model or reuse a different tokenizer/dataset for an optimizer-exact phase.
