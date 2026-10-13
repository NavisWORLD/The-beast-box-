# Zeref 012C — joint language + game learning (real model-weight trial)

**Experimental state:** bounded CPU research trial; no automatic product release, no canonical parent promotion.

## The question

The earlier 011 full-neural policy explored better but **failed blocked-move gate G4 and basic language-retention gate G9**. The approved parent remains the verified Zeref 006 cycle-3 checkpoint `d0df90ea090b410aa5da5051b20e21ae5728236f7371450807f1af662fb02445`, genuine saved optimizer state. The 012A independent adapter experiment completed real training but yielded **50% held-out accuracy for all four arms**, and did not improve game decisions. The 012B public pocket gameplay evidence established 2,254 outcome-selected **classical simulation** actions and **zero verified historical IBM-to-individual-game-action pairs**.

**012C trains real RAWRPHØS base neural parameters** on two supervised objectives concurrently: movement commands learned from verified Zeref pocket simulation outcomes, and generically useful short conversational answers. It specifically tests whether language rehearsal helps versus a game-only control **without claiming measured quantum behavior produces better dialogue**.

## Provenance and privacy

- **Approved Zeref:** fetch exact `zeref-006-canonical-37ca3f8f` artifact from GitHub run `38179059173`. Verify original `model.safetensors` SHA-256, `approval.json`, canonical lineage, genuine saved AdamW moments and tokenizer. Never select rejected 011 weights.
- **Movement:** fetch passed 012B action dataset `zeref-012b-game-alignment-38321516632` from GitHub run `38321516632`. Confirm its manifest digest, 32 training vs 24 unseen layouts, 3,840 simulation actions and **2,254 positive observed-movement action targets**. Only train-labelled records, no heldout prompts, no quantum-action associations.
- **Native skill:** fetch `zeref-011-evidence-38191707756` (prior real emulator instrumented capture) and verify all 56 original game-frame/controller-ack examples. Episodes 0–2 are scripted-imitation training (42 actions), episode 3 held out (14 actions). This is **archived real native observation**, not new gameplay or new achievements.
- **Dialogue:** `scripts/zeref_012c_joint_dialogue.py` contains 60 authored **synthetic teacher** training pairs and 20 disjoint heldout prompts over greeting, clarity, uncertainty, memory/state separation, quantum provenance, game strategy, playful tone, privacy, correction, and turn-taking. No actual visitor chat transcripts or owner-private lines. It does **not** train every guest to address a person as Cory or Dad.
- No new IBM hardware jobs, no Rigetti cloud jobs, no physical claims, no copying visitor chats/microphone/photos, and no mixing owner and guest memories. MODEL ≠ MEMORY ≠ STATE ≠ AUTHORITY.

## Predeclared trial arms and metrics

Three separately initialized-from-approved-parent candidates, **160 CPU AdamW updates per arm**, lr `1e-5`, genuine optimizer-state resume, same deterministic seed, eight examples per batch:

| Arm | Pocket targets | Public-language targets | Archived native controls |
|---|---:|---:|---:|
| Game only | 7 | 0 | 1 |
| Game + language | 3 | 4 | 1 |
| Game + language, shuffled game labels | 3 (shuffled) | 4 | 1 |

All three arms update their **actual neural model parameters**, not just a temporary memory vector. The joint arm is saved as a separate immutable hash-verified research shadow checkpoint and reloaded; the canonical parent is checked again from disk and unchanged. No product model is replaced.

Evaluate on **eight entirely different 012B pocket layouts**, each 40 actions, with the frozen parent and the three candidates, alongside the original random, pocket-learner and greedy-frontier policies. Report cells visited, blocked moves, legality, per-layout coverage, native teacher agreement, heldout native NLL, 20-prompt dialogue NLL, raw model responses for eight separate heldout prompts, and basic chat-retention NLL.

A **pilot pass** needs **all ten conditions**, predeclared before results:

1. Joint 20-prompt language heldout NLL not worse than approved parent.
2. Joint language heldout NLL better than game-only arm.
3. Basic chat-retention NLL within +10% of approved parent.
4. Joint heldout pocket coverage better than approved parent.
5. Joint heldout pocket coverage better than the site's pocket-learner.
6. Joint blocked-move count no worse than the pocket-learner.
7. Joint heldout native legal commands not worse than parent.
8. Joint heldout native scripted-teacher matches not worse than parent.
9. Joint native heldout NLL within +5% of parent (minimum allowed absolute `0.01` for near-zero baseline).
10. Joint pocket coverage better than matched joint-language arm with **shuffled game targets**.

**Regardless of these gates:** Eight layouts, one random seed and authored language targets are insufficient to approve the model as the next canonical parent or claim real conversational intelligence. Independent full 24-layout, multiple-seed, natural-language multi-turn and original ROM gameplay evaluations are still required. An optimizer completing successfully does not mean those gates passed.

## Execution

`/.github/workflows/zeref-012c-joint-game-language.yml` runs this bounded experiment on the pull request using CPU-only native RAWRPHØS, checked out from the existing repo. Artifact retention includes the saved research-only shadow checkpoint, optimizer state, all arm metrics and explicit rejected/passed gates. The workflow succeeds when training and evidence are reproducible **even if model-quality gates fail**, which are recorded as such—not hidden.

**Next work after this research stage:** complete the currently red shared-chat / model switching PR and Lost COSMOS native Act II branch, and independently repair iPhone speech, animation, creature sprite roster and handheld overlays without rewriting any existing assets.
