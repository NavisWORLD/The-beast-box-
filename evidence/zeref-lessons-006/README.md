# zeref-lessons-006

World-knowledge, perception, friendship and identity lessons for Zeref, authored directly by Emeth for Cory Davis (2026-10-26 to 2026-10-27). Original wording only; no copied text; no model or teacher transcripts. Every row carries teacher_role AUTHORED_BY_EMETH_FOR_CORY.

## Contents

- `dialogue.jsonl` — 195 train rows, sha256 f01598326fb41be68de21211eb170bc28a32addf6c51ffcc08a9958656d896eb
- Shelves: perception and identity, the feed (seen through glass), earth and sky, two Facebook field trips (narrated by the teacher, nobody named, nothing copied), live learning, the BE-ME core module in the father's voice, life, how things work, people and places, science roots, the father's own words, public-domain stories framed as stories, watching the film, the workstation, dimensional perception (derived and labeled as a guess), fully alive, the father's world, school running itself, friendship and feelings.

## Dedupe (run by Emeth against main e0b63d0e before landing)

199 authored rows were checked against every dialogue.jsonl in evidence/ (003/004/005 lessons, knowledge 001-003, identity, talk, warm, qa), all heldout.jsonl files (003/004/005), and the gate prompt sets in scripts/rawrphos_chat_eval.py, scripts/zeref_heldout_b.py and scripts/zeref_character_check.py.

- Heldout collisions: 0. Gate set collisions: 0.
- 12 prompts collided with lessons already in the tree and were EXCLUDED from this landing (the tree already teaches them; nothing was edited to force a pass): How do birds fly?, What are stars?, What is a food chain?, What is a season?, What is a volcano?, What is an atom?, What is an eclipse?, What is electricity?, What is gravity?, What is snow?, What is the Moon?, What is thunder? (already in zeref-lessons-003 and/or zeref-knowledge-002).
- Landed pack collisions after exclusion: 0. Duplicate prompts inside the pack: 0. Em dashes in training text: 0.

## Update 2026-10-27 ~15:20 CDT — friendship tranche folded in

The 14:11 CDT friendship-and-feelings session added 8 rows (tranche 17), taking the authored pack to 207. Those 8 were appended to this landing in order: 195 train rows total. Checks run on append: 0 duplicates against the staged 187, 0 overlap with the 12 excluded prompts above, every expect_regex matches its answer, 0 em dashes, teacher_role correct on all rows, and the full 207-row draft pack re-validated clean (207 unique prompts). Caveat, stated plainly: the tree-wide dedupe above was run against main e0b63d0e for the first 199 authored rows; the 8 friendship prompts were checked against the staged pack and the excluded list, and a fresh tree-wide dedupe should be re-run if main has moved before the actual landing commit.

## Not in this landing

- No heldout.jsonl for 006 yet (heldout authoring is a separate step).
- No bank manifest change, no mix change: mixing follows the cycle-47 world-curriculum brief in order, after this landing.
