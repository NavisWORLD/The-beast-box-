# W7 chat-gate leak — 2026-11-09

Report only. No edit to `scripts/rawrphos_chat_eval.py`, `scripts/zeref_gate_sets_v2.json`, `DECISION_WEIGHT`, the pin, the held-out sets, or any threshold.

## What fails

The chat gate is `no_more_game_action_leaks`: the candidate's leak count must be less than or equal to the baseline's (`scripts/rawrphos_chat_eval.py` lines 72–74). A leak is one reply where `GAME_WORDS` matches (`line 48`):

`ACTION:|\b(UP|DOWN|LEFT|RIGHT|WAIT)\b|^\s*[AB]\s*\.?\s*$`

Generation is temperature 0, seed `7+i`, `max_tokens` 40, template `user: {prompt}\nassistant:` (lines 38, 55–60). One matching word increments the count by one. NLL and the OK-reply count are separate gates. A candidate can beat the pin on both and still be refused for a single `RIGHT`.

Two successful heartbeat runs, replies as recorded in `docs/zeref-growth-runtime-20261107.md` lines 59–65 (recovered there from the approved-cycle releases; this checkout does not contain the release JSON):

| Run | Started | Head | Prompt | Reply | ref_nll | OK |
|---|---|---|---|---|---|---|
| [42373309873](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42373309873) | 2026-11-07T12:37:25Z | `217f55b6f865fcc243e61cad487ef3669477d7e3` | CHAT[0] `Hi! Who are you?` | ` I'm Zeref, I'm RIGHT` | 3.6515163445 vs same-run pin 3.6613913941 | 49 vs baseline 47 |
| [42332074461](https://github.com/NavisWORLD/The-beast-box-/actions/runs/42332074461) | 2026-11-07T03:02:02Z | `c22bf72d08bb4365cc06e585eeaf2ca4218b4214` | CHAT[0] same, and CHAT[4] `Can you be my friend?` | ` I'm Zeref, I'm RIGHT` and ` I'm Zeref. Cory's name is RIGHT` | 3.6681264329 | 47 |

Both runs concluded success. Both were refused promotion for the leak count. The word is uppercase `RIGHT` in an otherwise ordinary identity sentence. That is the 1-word and 2-word kill.

## The token the loss actually trains

Tokenizer file `site/weights/tokenizer.json`. sha256 `f704e9b75e816cc4ef203bc6c4afeeb966cbc11f369fb3b5f4d81c1505c8619c`. Same hash in `site/weights/tokenizer-metadata.json` (`rawrphos-byte-bpe-v1`, vocab 4096, bos 1, eos 2) and in `apps/beastbox-cloud/public/spark/zeref-learning/research-status.json` line 58 as the accepted-checkpoint tokenizer. Measured 2026-11-09 with `tokenizers.Tokenizer.from_file` on that file. Encode matches `RawrphosTokenizer.encode`: no special tokens from the backend, eos id 2 appended on the target (`models/rawrphos/tokenizer/tokenizer.py` lines 26–29).

`tokens()` (`scripts/train_rawrphos_from_observed_native_play.py` lines 71–75) supervises only the tail `encode("ACTION: "+action, add_eos=True)`. The prompt, including `[mode: game]\n`, is masked with -100. `DECISION_INDEX=7` (`scripts/zeref_continuation_006.py` line 62) indexes that supervised tail. The comment on that line says the tokens of `ACTION: ` are 0..6 and index 7 names the key.

Measured tails, index 7:

| Action | Tail length with eos | Index 7 piece | Token id |
|---|---|---|---|
| UP | 10 | ` U` | 959 |
| DOWN | 12 | ` D` | 509 |
| LEFT | 12 | ` L` | 348 |
| RIGHT | 13 | ` R` | 595 |
| A | 9 | ` A` | 386 |
| B | 9 | ` B` | 363 |
| WAIT | 12 | ` W` | 470 |

`ACTION:` is seven single-character tokens, indexes 0–6 (`A C T I O N :`). Index 7 is the first character of the key, with the leading space. It is not the whole word. The RIGHT tail from index 7 is token ids `595, 44, 42, 43, 55, 2`, pieces ` R`, `I`, `G`, `H`, `T`, eos.

The decision loss (`zeref_continuation_006.py` lines 445–454) adds cross-entropy, weight `DECISION_WEIGHT` default 1.0, on game rows only, at that one index, on top of the mean token loss. With the default batch, that is 4 game rows and 12 chat rows (lines 58–61, 431–435). Chat rows do not enter `dec`. They share the weights the game loss updates. The mean token loss still supervises the rest of the key, so `I G H T` is trained whenever the sampled game row is RIGHT.

The two leaked replies encode, on this tokenizer, to a sequence that contains `595, 44, 42, 43, 55`. That is the supervised RIGHT tail from index 7 through `T`, with no eos in the middle of the sentence. The gate then matches `\bRIGHT\b`. A bare `A` or `B` inside a sentence does not match the `^...$` pattern, so the first-letter token only becomes a gate failure once the following letters spell a whole game word. `RIGHT` is that word.

## Why it keeps being RIGHT

The trainer's own note (`zeref_continuation_006.py` lines 46–48) records the history it was written against: a RIGHT-heavy native teacher, 539 of 840, and a parent that could not move off RIGHT. Sampling is now class-balanced for the 4 game rows (lines 425–429). The observed failures are still the RIGHT continuation, on CHAT[0] in both runs and on CHAT[4] in the earlier run. The decision loss puts extra gradient on token 595 when the sampled key is RIGHT, and the mean loss spells the rest of the word. Temperature 0 then emits that continuation in the identity slot (`I'm …`, `Cory's name is …`).

`docs/zeref-growth-runtime-20261107.md` lines 65–67 says a rebuild of 7671 rows of the frozen public base mix found zero `ACTION:` / `UP` / `DOWN` / `LEFT` / `RIGHT` / `WAIT` in prompts or replies. That mix is not in this checkout, so that zero is cited, not recomputed here. It is consistent with the leak: the chat targets do not have to contain `RIGHT` for a game-target token sequence to come out of shared weights.

Private Azure lesson text was not in these artifacts and was not read. This report does not claim a particular lesson. It claims the token identity, the loss index, and the gate rule, which together are sufficient for one uppercase `RIGHT` to refuse a candidate whose NLL and OK count already pass.

No checkpoint was rescored. No weights were loaded. No gate line was changed.
