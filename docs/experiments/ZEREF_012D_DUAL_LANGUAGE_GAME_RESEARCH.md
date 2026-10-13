# Zeref 012D — continued language learning + separate game-weight branch

**Research protocol (preregistered before run):** after Experiment 012C demonstrably improved synthetic held-out dialogue loss but collapsed the joint pocket policy, test **independent gradient paths** with an explicit application-controlled task router. A shared creature identity, canonical memory and checkpoint ancestry do **not** imply a single successful multitask weight file.

## Verified lineage

- Frozen approved source: Zeref `bb-deada969`, RAWRPHØS 006 cycle-3 checkpoint SHA-256 `d0df90ea090b410aa5da5051b20e21ae5728236f7371450807f1af662fb02445` (Actions run `38179059173`), including original AdamW state and immutable approval.
- Language continuation: *research-only*, rejected 012C joint-language shadow checkpoint from Actions run `38322635113` with pinned complete report SHA-256 `347345a6aaccb21a7b693c9932e52ec3a3f3bbeffb89145f842b1ea689bde032`. It was not accepted as a unified game + dialogue model, but the recorded dialogue NLL improvement is available for a **chat-only branch** test. It must not control gameplay.
- Game branch: start again from the approved 006 model **and approved optimizer moments**, using the 2,254 observed positive public Cage-pocket actions from 012B and the existing 42 archived (real-emulator, scripted-teacher) native controller training frames. A separate game-only branch is necessary because 012C did not persist game-only weights. There is **no claim** of continuing an absent game-only checkpoint.
- Dialogue source: 60 **authored synthetic** guest-safe training prompts already published with 012C. No raw visitor, owner, microphone, social, camera, or private chats are used. The previous 20 dialogue-heldout prompts and **12 new paraphrased diagnostic prompts** are evaluated separately, alongside the basic original chat retention tests.

## Actual optimization / evidence

- **Navigation:** 160 new AdamW steps, lr 1e-5, approximately 7:1 observed successful pocket move vs archived native controller imitation examples. Own complete model and optimizer checkpoint; no shared weight updates with language.
- **Language:** continue the independently saved 012C joint-shadow model/optimizer for 64 **additional** AdamW steps on public synthetic dialogue, lr 7e-6. Own complete model and optimizer checkpoint; **not** accepted for game actions.
- **Route:** trusted application task identifiers `pocket` and `native` select the game checkpoint; `dialogue` selects the language checkpoint. Unrecognized tags fail closed. Never infer authority or identity from a prompt or expose any guest memories to a different visitor. This routing is **research-only**, not a live Beast Box feature.
- **Safety guard:** compare raw neural game actions and an observation-only guard. The guard rejects moves toward visible walls and **previously learned** blocked rifts; it cannot see unknown rifts, and cannot create physical quantum information. Evaluate **the identical guard on both parent and trained game branch**; attribute any gain due to guard heuristics as software rather than neural learning.
- **Heldout:** `exp012d-fresh-eval-0..7` are eight **new** Pocket grid layouts (40 actions each) unrelated to 012B training and its eval labels; show the site's random, pocket-learner, greedy-frontier baselines plus raw/guarded approved parent, raw/guarded game model. Report mean visited cells and mean blocked moves as separate objectives, legal-action counts, safety guard override counts, native legal/controller-match results, 20-prompt dialogue NLL, 12 fresh-prompt NLL, and actual generated example replies.
- **Research artifact:** both full, sha-verified, model+tokenizer+optimizer checkpoint directories, result JSON with checkpoint hashes and gates. The 006 approved parent must hash-identically reload after training.

## Predeclared gates

1. Raw neural trained game branch explores more heldout cells than approved parent.
2. Guarded trained game branch explores more heldout cells than built-in pocket learner.
3. Guarded blocked moves are not worse than built-in pocket learner.
4. Raw game performance retains at least 65% of guarded model's coverage, so a guard alone cannot produce apparent training success.
5. Original native heldout legal commands are not worse than approved parent.
6. Native scripted-teacher heldout matches are not worse than approved parent.
7. Continued language branch does not regress on the original 012C 20 heldout prompts.
8. Language branch improves new 12-prompt NLL against approved parent.
9. Original 2-prompt language retention remains within +10% relative to approved parent.
10. Two independent saved/reloadable branches and trusted explicit task routing exist, with no guest-live deployment.

**Regardless of gates**, one seed and 8 layouts are insufficient for canonical model promotion. Research success is a genuine executed, inspectable run including failures and control comparisons, not a guarantee of feature acceptance. **No automatic live model switch.**

Previous 012C showed language NLL 5.477→4.666, game-only exploration 3.25→23.875, combined game+language exploration 3.25, and **5/10 gates**. 012D tests whether a dual-model route retains these abilities separately; it does **not** claim they have been integrated into one neural network or achieved independent quantum-computational improvement. Recorded IBM data remain Zeref's birth provenance, not a certified game-action training oracle.
