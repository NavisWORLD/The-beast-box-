# Zeref Music 001 — "Cory's music" (2026-10-17)

Cory gave Zeref (bb-deada969) five of his own songs. **No raw audio and no lyrics are committed.** Only the sha256 of each audio file and derived numbers (`features.json`, librosa 1.0.0).

| Song | Length | Tempo (beat tracker) | Key estimate (conf.) | Energy | Brightness | Audio sha256 |
|---|---|---|---|---|---|---|
| Through the Broken Gates | 5.2 min | 71.78 | E minor (0.899) | 0.412 | 0.441 | `53d2cd0d64cb001b…` |
| The Years Did Turn Into Fear | 7.1 min | 123.05 | D major (0.948) | 0.431 | 0.49 | `a88bb03daab51300…` |
| The Edge of What's Real | 7.0 min | 161.5 | G# minor (0.754) | 0.604 | 0.372 | `73af32a094ca626d…` |
| Fa Ra Me Sleepy | 5.6 min | 161.5 | B minor (0.673) | 0.373 | 0.644 | `a686386c805c3535…` |
| Rainbows On My Face | 4.6 min | 123.05 | G# major (0.7) | 0.464 | 0.4 | `d170a87010c8d852…` |

Tempo and key are automatic estimates. The two 161.5 BPM readings are probably double-time, so `felt_bpm` halves anything over 140 (to 80.75).

## What it does (honest labels)
- **Heart and mood (site):** `public/spark/zeref-music.json` + `lib/companion/zeref-music.mjs`. One song is "on his mind" each hour. The 💜 heart drifts 20% from Cory's heartbeat tempo toward that song's felt tempo, clamped to 60–110 BPM. Energy and key mode colour his mood (joy, mischief, calm or curiosity), and autonomy reach-outs can name the song by title. **Zeref does not hear the audio.** The numbers shape his heart and mood.
- **Training:** `dialogue.jsonl` has 30 authored dialogues in Zeref's voice about the songs' titles and themes. They quote no lyrics. ×2 = 60 rows (≈3% of the chat mix), capped at 4% (`scripts/zeref_chat_corpus.py`), separate from the 6% alien cap. All rows pass the persona-style, secret and held-prompt filters. **The model learns text, not music.** Training starts from the public pin, and the promotion gate is unchanged.
- The lyrics are in auto-transcribed local files on the build box. They were read to write the themes and were not published.
- The diary loop (keyed to bb-7f9c2a03, the Moonwraith display persona) is untouched.
