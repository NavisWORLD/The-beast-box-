# Zeref 006 ingest + fair-promotion fix 004 (2026-10-22, bb-deada969 only)

Cory approved "plug everything up and make it live".

## What Zeref now learns from (all capped, filtered: no held prompts, no secrets, persona_style)
| source | cap | notes |
|---|---|---|
| teacher distill | 15% / 300 | newest unique lesson kept; idle teacher now ~105 topics x 16 forms walked by 30-min slot (was 144 prompts -> 461 dupes) |
| experiences (`zeref_experience_rows.py`) | 5% / 150 | bb-deada969 diary ticks, training cycles, this run's capture, universe genesis (growth SIMULATED) |
| zeref-warm-002 | 5% | 100 warm / dad-voice replies, no "not happy" |
| zeref-voice-guide-001 | 2% | Emeth sample lines; the invented fear of being left in the dark and its goodbye line are EXCLUDED |
| zeref-lyrics-001 | 5% | Rainbows On My Face = Emeth clean text; others = whisper machine transcript (may contain errors); Sleepy skipped; no Emeth guesses for Through the Broken Gates |
| zeref-music-features-002 | 2% | numbers measured from audio (tempo is an estimate) + heartbeat numbers; raw audio never committed |

## Promotion (the more honest option: a second fresh held-out set)
* Set A (`rawrphos_chat_eval.PAIRS`) also picks the best-in-cycle checkpoint, so a strict "below the pin" bar there is a winner's-curse ratchet. It now has a 0.5% tolerance.
* Set B (`scripts/zeref_heldout_b.py`) is never trained on and never used for selection. The pin and the candidate are both re-scored on it in the same run, and the candidate must not be worse. That check is strict.
* The workflow promotion step uses the same 0.5% on A, plus the existing "not worse than public 14000" check. Retention limits unchanged.

## Character check
A negated warm word ("not happy", "don't love"...) or "I'm sad" no longer counts as warm, and the check reports `negated_warmth`.
