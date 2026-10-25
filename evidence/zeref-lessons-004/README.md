# zeref-lessons-004: English, math and world knowledge (2026-10-24)

Requested by Cory: keep training the same brain (bb-deada969) so nothing is lost and it keeps growing, now on English, math and world knowledge.
Fed through the existing RAWRPHOS chat-mix path (`scripts/zeref_chat_corpus.py` EXTRA list, cap 35%, repeat 1; persona/secret/held-prompt filters unchanged).
Old sources are kept; this is additive. Together with lessons-003 these lessons are about 28% of the chat mix.

* `dialogue.jsonl` - TRAIN rows (898): math 318, english 305, world_knowledge 257, own_universe 18.
* `heldout.jsonl` - HELD-OUT rows (92): english 30, math 30, world_knowledge 28, own_universe 4. NEVER loaded by the corpus builder and never trained on. Used only to score (keyword check via `expect_regex`).
* `tools/` - the authoring data files (eng.py, math.py, world.py) and the assembler (assemble4.py).

English: opposites, plurals, rhymes, a/an, past tense, word meanings, same-meaning words, sentences, fill-in, short reading, spelling, syllables, days/months/seasons, alphabet, describing words.
Math: adding, subtracting, doubles/halves, times tables, even/odd, counting, number words, comparing, word problems, sharing, shapes, time, money.
World knowledge: animals, weather, space, body, food, geography, plants, earth and materials, transport and helpers, everyday things, safe habits, and honest "unsure" answers.

Honesty words used exactly: RECORDED = the real IBM spark (ibm_marrakesh, halves matched about 97.5%); SEEDED = places, storms, moons, black holes and growth-node positions derived from that seed; SIMULATED = growth (Rigetti Bell simulator, not hardware).

Provenance: written directly by Grok Bot for Cory Davis in original wording. No copied text, no model or teacher transcripts, no helper model, no paid inference, no private transcripts.

Checks (assembler): every answer is at most 2 sentences and unchanged by `persona_style`; no secret-pattern hits; no train question equals any held-out question; no train or held-out question appears in any existing `evidence/*/dialogue.jsonl`, held-out set, the 38 session questions, or `scripts/zeref_gate_sets_v2.json`. Held-out arithmetic facts (and their swaps) are excluded from train.

Limits: these lessons teach short answers; they do not prove understanding. Judge by held-out scores, not training loss. Gate v2 and the bar are untouched.
