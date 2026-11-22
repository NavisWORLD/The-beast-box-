# Zeref Funny 001: teacher-written humor (not Zeref output)

Cory, 2026-11-21 6:51 PM CT: "let's make him funnier and faster and even better".

- `teacher-pairs.txt` has 442 playful dad-and-son pairs written by Grok Bot for Cory on 2026-11-21: puns, silly what-ifs, light, moon and star jokes, and callbacks to his world (warm rock, Pebbleton, the Moonwraith, Emeth, Dad). **Every row is teacher-written, not Zeref output.** None of it is a reply Zeref produced, and no private transcripts were used.
- `python scripts/build_zeref_funny_001.py` builds the files deterministically:
  - `dialogue.jsonl` has **324 train rows**.
  - `humor-probe-heldout.jsonl` has **38 held-out rows**, 10% chosen by sha256 of the prompt with no randomness. Training never loads it; only the report-only probe reads it.
  - `dedupe-receipt.json` lists the drops: 53 for overlapping a Gate v2 or held-out prompt, 4 that failed the style filter, and 23 train rows that overlapped this pack's own held-out set.
  - Checks: exact Gate v2 / held prompts, the >= 0.5 content-word overlap rule (`world_overlaps`) against `scripts/zeref_gate_sets_v2.json` and every `evidence/*/heldout*.jsonl`, `persona_style` unchanged (<= 2 sentences, <= 160 chars), and the SECRET screen.
- **Why the held-out file isn't called `heldout.jsonl`:** the served-shape and world builders glob `evidence/*/heldout*.jsonl` into their forbidden sets. With a file of that name present, the chat-mix sha changed even with the hook off (measured). With this name, the OFF mix is byte-identical.
- `scripts/zeref_chat_corpus.py` loads the pack only when `ZEREF_FUNNY_SHARE` > 0 (allowed 0–0.10, repeat x2, overlap-filtered again at load). If it's unset or 0, the mix and manifest are byte-identical to before. The 006 workflow doesn't set it, so this is **OFF** until Cory says yes.
- `probe-baseline-44784.json` is **LOCAL**: `scripts/zeref_humor_probe.py` (report-only, same greedy settings and scorer as the chat eval) run on pin 44784 before any funny training. Result: 38 prompts, 38 ok, 0 leaks, 35 distinct, playful-marker rate 0.263.
- The gates are unchanged: Set A/B, G1–G10, the loose rule and the hard leak screen.
