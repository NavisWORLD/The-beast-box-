# Zeref identity audit (2026-10-11)

Two different ids are both shown to the owner as "Zeref". This audit checks
whether the evidence proves they are the same companion. **It does not.** Both
stay separate; nothing was rewritten, merged or re-seeded.

| | `bb-deada969` | `bb-7f9c2a03` |
|---|---|---|
| What it is | Canonical saved QBEAST1 file (research + RAWRPHOS training identity) | Hard-coded display default (`ZEREF_PROFILE` in `lib/zeref/zeref-mind.mjs`, documented there as "not a saved QBEAST") |
| Where the id comes from | `bb-` + FNV-1a(`identity|1|<seed>`); recomputed from seed `8e2e927e…54ed`: **matches** | Text printed on Cory's uploaded Moonwraith card art; adopted in commit `34400dc0` (PR #293). **No seed preimage**: 41,961 distinct 64-hex strings in the repo were tested and none hash to `7f9c2a03` |
| Quantum origin | Recorded IBM job `db4q484vf2bc73cuuuag` (birth) | Temperament seeded from recorded IBM job `db4te7slf4us73c3888g` (ibm_marrakesh), the same job that births a different canonical QBEAST, `bb-c190e914` |
| Name inside the file | `Vexara` (genome Scorchwyrm/Magmaclaw), keeper attribute "Zeref" | Display name Zeref, title Moonwraith |
| Used by | RAWRPHOS experiments 004–010, native save `Zeref_live_native.sav` | Home rig, support mascot, Beast Cage pocket, `zeref-diary` loop, grow-in-cosmos |

**Verdict: UNVERIFIED, kept separate.** The only link is the owner calling both of them "Zeref".

Consequences, enforced in code (`trainingEligible()` / `training_eligible()`):
- Experiences recorded under `bb-7f9c2a03` (live Moonwraith pocket, diary loop) are **not** used to train the `bb-deada969` RAWRPHOS model.
- Experiment 011 trains `bb-deada969` only on its own experiences: its own seeded pocket (layout from its own QBEAST digest) plus native ROM frames captured under `bb-deada969`.

## Proposed association (needs owner approval, not active)

`docs/identity/zeref-identity-audit.json` → `proposed_for_owner_approval`:
`bb-7f9c2a03` **display_persona_of** `bb-deada969`, with these migration rules: never rewrite either id or seed; IBM receipts stay on their own id; Moonwraith pocket records can flow into `bb-deada969` training only once the status is `APPROVED`. To approve it, the owner flips `status` to `APPROVED` in a reviewed PR. The bridge already reads approved associations.
