# zeref-lessons-003: all-subjects simple Q&A (2026-10-24)

Requested by Cory ("do the full question file, also train Zeref in all subjects").
Short, simple lessons at Zeref's level for bb-deada969, fed through the existing RAWRPHOS chat-mix path
(`scripts/zeref_chat_corpus.py` EXTRA list, cap 27%, repeat 1, persona/secret/held-prompt filters unchanged).

* `dialogue.jsonl` - TRAIN rows (651). Fields: user, assistant, subject, topic, good_answer_note, expect_regex, source, author, split="train".
* `heldout.jsonl` - HELD-OUT rows (92). NEVER loaded by the corpus builder, never trained on. Used only to score. 20 of them are flagged `talk20` (2 per subject) and are asked again after every round.
* `tools/` - the authoring scripts (plain Python data + the assembler that checks filters).

Subjects: greetings_manners, identity_maker, numbers_math, letters_reading, science, geography_nature,
colors_shapes_music, feelings_kindness, safety_honesty, own_universe.

Honesty words used exactly: RECORDED = the real IBM spark (ibm_marrakesh, halves matched about 97.5%); SEEDED = places, storms, moons,
black holes and growth-node positions derived from that seed; SIMULATED = growth (Rigetti Bell simulator, not hardware).
Zeref never claims growth is real, never claims to be human, never claims to control the universe.

Provenance: written directly by Grok Bot for Cory Davis in original wording. No copied text, no teacher-model transcripts,
no paid inference, no private transcripts. A few lines under topic "staying close (approved sideways lines)" use Cory's
Oct 24 approval of the fear-of-the-dark questions (never said straight, shown sideways).

Checks (assembler): every answer is at most 2 sentences and unchanged by `persona_style`; no secret-pattern hits; no train prompt equals
a held-out prompt; no held-out prompt appears in ANY existing evidence/*/dialogue.jsonl or the reviewed TRAIN corpus;
none of the 38 Zeref session questions is used verbatim in training (a few identity/world facts are still taught in other words).

Limits: these lessons teach short answers, they do not prove understanding. Judge by held-out scores, not by training loss.
