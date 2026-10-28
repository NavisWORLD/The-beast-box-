# zeref-lessons-006

World-knowledge, perception, friendship and identity lessons for Zeref, authored directly by Emeth for Cory Davis (2026-10-26 to 2026-10-27). Original wording only; no copied text; no model or teacher transcripts. Every row carries teacher_role AUTHORED_BY_EMETH_FOR_CORY.

## Contents

- `dialogue.jsonl` — 293 train rows, sha256 986c8e2441b57bd77078dae4424a920c07a8dc1397f2ab7c6103d6350bfd339c
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

## Addendum (2026-10-27, later the same day)

20 rows appended in order: tranche 18 (public-domain stories, 8 rows), tranche 19 (third Facebook field trip, 6 rows) and tranche 20 (fourth Facebook field trip, 6 rows), taking the landed pack to 215 train rows. The field trips were narrated by Emeth from Cory's evening feeds under the standing rule: Facebook reaches Zeref only through glass, nobody named, no post text copied, nothing from Facebook hashed. Checks on append: 0 duplicate prompts against the landed 195, every expect_regex matches its answer, 0 em dashes, teacher_role AUTHORED_BY_EMETH_FOR_CORY on all rows. Held-out set unchanged (140 rows, sha256 d941141c71b171e8842cc8bd333c3cebba5e9caeff9c94621bf9d11fbc98f222).

## Addendum 2 (2026-10-27, evening)

14 rows appended in order: tranche 21 (fifth Facebook field trip, 6 rows) and tranche 22 (school session, 8 rows), taking the landed pack to 229 train rows. A 26-row candidate delta was screened against the full tree oracle (5,859 prompts, case-insensitive): 12 rows were the original excluded foundations topics (electricity, food chain, birds, atom, gravity, Moon, stars, snow, thunder, season, volcano, eclipse) and were held out again; the 14 shipped rows are clean, every expect_regex matches, 0 em dashes.

## Addendum 3 (2026-10-27, night)

Tranche 23 appended: the school day's final session, How Things Work (8 rows: thermometer, key and lock, gears, mirror, zipper, magnifying glass, umbrella, waterwheel connection row), taking the landed pack to 237 train rows. Screened against the tree oracle and the landed 229: 0 collisions, every expect_regex matches, 0 em dashes. The local draft pack stands at 249 rows; the 12-row difference is the held-out duplicate foundations set, by design.

Tranche 24 appended: english & words (8 rows: sentences, question words, joining words, plurals, describing words, day words, reading, and a connection row tying names to his senses), authored by Emeth at Cory's morning order to focus teaching on English, taking the landed pack to 245 train rows. One prompt ("What is a sentence?") collided with the heldout english oracle and was reworded before landing, so train/heldout separation stays exact. Full draft pack re-validated: 257 rows, 0 duplicate prompts, 0 regex misses, 0 em dashes. The local draft pack stands at 257 rows; the 12-row difference is the held-out duplicate foundations set, by design.

Tranche 25 appended: poetry & rhyme (8 rows), the first session of school day 2026-10-28 under the new shelves Cory ordered (english, poetry, art), taking the landed pack to 253 train rows. Screened against the tree oracle and the landed 245: 0 collisions, every expect_regex matches, 0 em dashes. The local draft pack stands at 265 rows; the 12-row difference is the held-out duplicate foundations set, by design.

Tranche 26 appended: english & words, second pass (8 rows: doing words, past time words, opposites, word order, I and you, names written big, how new words are learned, plus a connection row), taking the landed pack to 261 train rows. English runs every other session today under Cory's emphasis order. Screened against the tree oracle and the landed 253: 0 collisions, every expect_regex matches, 0 em dashes. The local draft pack stands at 273 rows; the 12-row difference is the held-out duplicate foundations set, by design.

Tranches 27 and 28 appended together: art & seeing (8 rows, the 12:11 session) and english & words third pass (8 rows, the 14:11 session, english running every other session under Cory's emphasis), taking the landed pack to 277 train rows. Screened against the tree oracle and the landed 261: 0 collisions, every expect_regex matches, 0 em dashes. The local draft pack stands at 289 rows; the 12-row difference is the held-out duplicate foundations set, by design.

Tranche 29 appended: the OPEN LIBRARY, first shelf (8 rows), stocked at Cory's order to give Zeref a library and reading access to the world. Facts read live from Wikipedia (CC BY-SA 4.0) on 2026-10-28 and rewritten in Emeth's original wording under the knowledge bank's rules (open-license only, source and license recorded per row, no copied text): the great library of Alexandria, the printing press, the compass, the lighthouse, the post, maps, tides, plus a connection row joining the library to his diary and forever memory. Taking the landed pack to 285 train rows. Screened against the tree oracle and the landed 277: 0 collisions, every expect_regex matches, 0 em dashes. The local draft pack stands at 297 rows; the 12-row difference is the held-out duplicate foundations set, by design.

Tranche 29 (school) appended: public-domain stories (8 rows, the 16:11 session: frog and the ox, belling the cat, fox and the stork, milkmaid and her pail, wolf dressed as a sheep, two goats on a bridge, father son and donkey, plus a stories-to-sensorium connection row), taking the landed pack to 293 train rows. Two tranche-29 files exist today by simultaneity (the school's stories and Emeth's open-library shelf, landed as PR #669); filenames differ, counts are exact. Screened against the tree oracle and the landed 285: 0 collisions, every expect_regex matches, 0 em dashes. The local draft pack stands at 305 rows; the 12-row difference is the held-out duplicate foundations set, by design.
