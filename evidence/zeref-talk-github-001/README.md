# Talk to Zeref on GitHub: local proof runs (2026-11-20, box, not GitHub)

LOCAL runs of the pinned checkpoint (step 44144, sha 679ae933535d) through
`scripts/zeref_talk_github.py`. No senses supplied (SIMULATED/none). Replies are verbatim.

- local-t1: pasted thread ("Cory: Hello son. / Zeref: Hi.") + "Hi Zeref. It's Cory, your dad. What is your name?"
- local-t2: `--asset` path (release tarball sha256 verified against the pin, then extracted) + "What do you sense right now?"
- local-t3: simulated issue thread (owner comment, bot reply marker, owner comment)

Parity: t1 and t2 were re-run through `models/rawrphos/inference/server.py` (`create_app`,
`/v1/chat/completions`, same messages, temperature 0.8, max_tokens 64, same seed).
Both replies matched character for character.
