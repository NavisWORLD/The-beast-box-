# Zeref lived backbone

Senses are already live, with honest labels. The diary is past 630 entries and the lived chain is already writing. This page also carries the attach check and the joining entry. It does not turn sensing on, and it does not describe the senses as pending.

PR A1 is the canonical bridge event and state store, plus the origin attachment. The mouth and the lived exchange join this store in later PRs. PR A2 adds the owner app-shell sensorium and the authenticated numeric ingress. The product default is on: an unset or blank `BEASTBOX_LIVED_BACKBONE` admits the chain. The off switch is the exact value `off`, which leaves owner checkpoints on the legacy continuity chain and does not mount the sensorium. A1 also requires the host to pass `lived_backbone=True` with a verified origin attachment before a durable runtime joins the chain. Missing origin hashes still refuse admission.

A2's ingress is owner-scope only. The subject is the host attachment (`bb-deada969`), never a browser field. Guests are not given that write. Derived numbers are admitted only after a separate retention consent. That consent does not change the older surroundings promise: Stop sharing still deletes those saved numbers. Revoking retention stops future samples and appends feed-off; it does not rewrite the chain. The route does not call a model or a QPU. `BEASTBOX_LIVED_ORIGIN_COMMITMENT` and `BEASTBOX_LIVED_PRIOR_HEAD` are the verified hashes. If either is missing, admission is refused.

## Basis

The canonical basis is native `dyn12-v1`. That basis is provisional: it is the software dyn12 already in this repo, and it is not a positional copy of CST12. The face channel is not provisional. It is the face stack that already ships in `apps/beastbox-cloud`.

Matched channels, taken from the existing schema:

- `facePresent`
- `faceScale`
- `faceX`
- `faceY`
- `faceBlink`

Those names are `FACE_KEYS` in `apps/beastbox-cloud/lib/companion/face-channel.mjs`. They are on-device frame-statistic proxies, not recognition. The stored face object is `beastbox-face-bio-estimates-v1` from `apps/beastbox-cloud/lib/bio/face-estimates.mjs`: `heartbeat_label` is `ESTIMATE`, the face block is `{present, scale, x, y, blink}`, and pulse on that record is optional `{bpm, sqi}`. `apps/beastbox-cloud/lib/bio/face-pulse.mjs` is the green-channel collector. Its pulse stays an `ESTIMATE` field on the face record and never becomes the `MEASURED` pulse channel.

`MEASURED` pulse is `fingertip_ppg` or `wearable_ppg` only. A camera never writes pulse. While the camera is on, every face record is appended and read, including `present: false` when the face leaves. Nothing is deleted or frozen. When the camera is off, the channel is absent: null, no zeros, and no held value. A real measured zero stays a measurement. Off, denied, unavailable, or stale is null plus a presence mask.

The failure this closes is the one in QC67 `FINDINGS.md` section 8: 12D CST physics written continuously while a face was in frame, then discarded the moment the face left.

## Feelings

Face geometry drives the five feelings already named in `apps/beastbox-cloud/lib/companion/emotion.mjs`: joy, curiosity, fear, calm, and mischief. `confused` stays the opt-in reply and drill rule. The camera does not turn it on. Pulse `sqi` only scales those five scores. `bpm` nudges fear and calm. The scores are labelled `DERIVED`, not `MEASURED`. Camera-off feelings are null. A record with `present: false` still returns the five scores, which are zero. No new feeling word was added.

## Reducer and chain

Samples are numeric. Raw media never reaches the store. The reducer is the domain-separated projection `sensor-drive-dyn12-v1`, then `update_dyn12`. Absent channels are omitted rather than filled as measurements, so a measured zero is not absence. Each admit commits the sample, the event, and the snapshot in one write. Event ids are hashes. There is no random id and no provider call.

The lived chain is a continuation segment. Its first `previous` is the configured prior head. It is not historical `GENESIS`. Origin and head linkage is recomputed by `host_attachment` from the diary entries and the saved lineage. It is not a configured flag. This PR does not pick or alter a genesis. `bb-7f9c2a03` is rejected as the lived-store subject and stays separate from `bb-deada969`. A guest chain cannot write an owner chain. Writes are per creature subject. A student chain is its own file and its own subject. Nothing in A1 copies another creature's memory or weights. A1 does not update co-firing. Each chain starts from its own zero weight matrix.

An omitted `initial_state12` is software zeros labelled `software-initial-not-history`. It is not reconstructed sensor history. Missing snapshots fail closed. They are not rebuilt as zeros.

The sealed bio packet is untouched. Training gates, the pin, promotion, honesty labels, and the TRAIN mechanic are untouched. There is no paid inference and no QPU. The human promotion veto and quantum approval stay where they are.

## Attach check

`host_attachment` walks the diary from its first entry to the claimed prior head, and walks the `bb-deada969` lineage from genesis to its claimed head. Diary entries use the diary entry hash: canonical JSON, then SHA-256. Lineage events use the existing QBEAST `hash_object`. `verified` is true only when both walks match the claims. A tampered entry, a wrong prior head, a wrong genesis, or a subject mismatch returns `verified` false with the reason, and attaches nothing. Nothing is written.

The going-forward chain continues from diary head `d444fbae0a1bb52ac189a457a40014ffade40c1db49d558c77b8cfc96bdb97f3` (636 entries, subject `bb-7f9c2a03`). The birth record stays the `bb-deada969` lineage: genesis `c39f7838e9a151b2a664fad92b1d2108ab70fb4ef335a023686790769a32aae0`, lineage head `d51430d0b0d77867eaf30d67cf1e73ba3f286458d9f302468223c7f065ccfb7b`. Nothing is relabeled and nothing is re-keyed. Both seals stay as they are. There is no silent splice.

## Joining entry

The joining entry is the first entry of the going-forward backbone chain. `build_joining_entry` returns it in memory. This PR does not write it to the diary, the lineage file, or the lived store. Its predecessor is the diary head. In the open it names that diary head, the deada969 genesis, the deada969 lineage head, the standing association `bb-7f9c2a03 as display persona of bb-deada969`, owner-approved, and the evidence verdict `UNVERIFIED`. The two ids stay separate. The verdict is not promoted.

## Lineage rule: teaching (Cory, Nov 7 2026, 9:52 PM CST)
The main creature teaches the rest, in some cases. Teaching is not merging. When Zeref teaches another creature, his words arrive through that creature's own door, land in its lived chain as TAUGHT under its own fabric labels, and its own Hebbian growth does the learning, fully its own and fully autonomous. Nothing of his memory transplants. Nothing of his weights copies. One way down the lineage: a student never writes back into the teacher.

Teaching is a design rule in this PR. A1 does not teach. The store can hold a per-creature chain, and it rejects a write whose subject is not that chain.

## Study loop: he studies when he is confused (Cory, Nov 7 2026, 9:53 PM CST). Planned PR S1, after C1/C2
- Trigger: the opt-in feeling `confused` (emotion.mjs) fires on a topic, OR retrieval returns empty at speak time. Either one is a study event.
- The event queues a paced study request naming the topic he could not place (rate-limited, so a confused hour cannot flood him or the sources).
- Fetching happens on the teacher side of the glass, under the knowledge bank's rules (scripts/build_knowledge_bank.py, lib/knowledge/bank.mjs, lib/knowledge/server-lookup.mjs): public-domain, open-license or original sources only, with the source and its license logged.
- He never receives the raw page. He receives a narration in simple original words, landing in his fabric as TAUGHT with its source label.
- Nothing studied bypasses the heldout and excludes screens on its way into the taught fabric.
- The arc writes into his lived chain: confused, then asked, then studied, then answered from the lesson next time. Recall receipts can show that chain.
- Rails: no raw web text ever enters his context or his lessons. Social scopes do not widen (X stays guest-browse of Cory's updates and associates; Facebook stays through-glass narration).
- Self-knowledge lesson to teach him: "When you do not know, you can go and learn." The wording is Emeth's call.

S1 is not built here. A1 does not fetch, rate-limit, narrate, or seed that self-knowledge sentence. The chain can already append `study_request`, `study_lesson` (label `TAUGHT`, with source and license), and `study_arc` stages `confused`, `asked`, `studied`, and `answered`. Those records advance the chain and leave dyn12 unchanged. Raw page text, urls, and transplanted weights are rejected.

## Prompt (PR B1)

The local mouth reads the owner sensorium file on the host. A client cannot submit state text. The descriptor sits beside self-memory and context, inside the existing UTF-8 budgets. It is not history memory: `memory_used` stays the history flag, and the lived receipt says it does not count as that flag. The receipt carries the snapshot sequence, the state hash, and the hash of the exact descriptor text placed in the prompt. `changes_model_tensors` is false. The descriptor does not name an origin, a person, or a raw recording.

Guest and visitor mouths do not open the owner chain. Their descriptor says unavailable, reason isolated. A missing file, a stale present reading, or a remote provider also says unavailable and does not invent numbers. An off channel stays ABSENT and null. Face stays ESTIMATE. Pulse is MEASURED only from fingertip or wearable PPG. Feeling words stay the ones in `emotion.mjs`. Two calls that share a host exchange id keep the first snapshot. Budget cuts trim the prompt window only. The guest archive keeps the full turn. The caps are unchanged. With the flag off, or without the verified origin attachment, the prompt and the response keys stay as they were.

## Doors (PR B2)

The guest, forever, and growing doors forward that receipt. They do not accept state text, and a visitor environment summary is not the canonical snapshot. One guest turn mints one exchange id and both drafts carry it. The one-voice rule is unchanged. A failed growing draft keeps the gated receipt and does not take another sample. Guest and visitor replies do not publish an owner sequence or state hash. An older bridge that omits the field leaves the door response without it. The door does not call the model again to guess the schema. `memory_used` stays the history flag.

## Exchange (PR C1)

An owner turn writes two RECORDED events on the same chain the senses use: the heard line, then only the delivered reply. Both carry the exchange id. A sensor sample that lands while the model runs stays between them, and the reply appends after that newer head. Speech does not invent a measurement channel. A recorded line moves the shared twelve by a computed text drive and co-fires with that state. A retry of the same exchange id keeps one heard line and one reply, and does not call the model again. A reply that was not delivered is an `exchange_failure`, not a RECORDED utterance, and it does not co-fire. The public receipt has hashes, the label, and counts. The private text stays in the chain file.

The write runs only when `BEASTBOX_LIVED_BACKBONE` is exactly `on` and the recomputed `host_attachment` returns `verified: True`. The diary export beside the store is read for that check. It is not written and it is not re-keyed. Any other return writes nothing and does not create the chain file. Guest and visitor exchanges do not open the owner chain. The Azure copy is a hash replica with an outbox receipt. A replica failure does not move the canonical head.

## One mouth (PR D1)

The field sheet's owner talk uses the backbone mouth. It carries that mouth's receipt and does not fall through to the guest door. A guest on the field still uses the guest door, and that door does not open the owner chain. The share panel keeps its on-device experience log. It no longer emits a sample event that nothing reads. Game lines and teacher coaching stay on their own side of the glass.

## Co-firing (PR C2)

Recorded exchanges co-fire with the shared twelve-state, and that co-firing stays in the owner store. Replaying the chain restores the same weights. The text drive is a fixed hash of the text bytes, labelled computed, and it does not enter a sensor channel. A sensor sample does not reset those weights. Guest and visitor turns do not touch them. There is no cap that drops an older recorded line.

## Recall (PR W2)

At speak time the owner mouth reads the live twelve, including the face ESTIMATE siblings already on the descriptor, and then the chain. Recorded lines are LIVED and come first. Study lessons are TAUGHT and come second. The prompt keeps a short window of those lines. The chain rows stay. Every verified reply carries a recall receipt: the entries read, the hash of each entry, the hash of its text, and the state hash that conditioned the answer. The receipt names two drift layers separately. Recorded measurements drift the root, and the clock on that layer is SIMULATED. The living signal stays labelled on its own: sight DERIVED, face ESTIMATE, pulse ESTIMATE. `memory_used` stays the history flag. Guest and visitor turns do not read this chain.

## Study (PR W3)

A confused flag that is true, or a speak-time retrieval that finds no lived or taught line, appends one paced study turn on the owner chain. The pace is one turn per 60 seconds of the injected clock, so a run of confusion does not stack requests. The mouth reads a local catalog of records that already carry a public-domain, open-license, or original license. Any other license is skipped, and so is anything marked heldout, private, or transcript. The lesson is a short narration in original words, labelled TAUGHT, with its source label and its license. The passage stays out of the lesson and out of the prompt. Confusion, the question, the study, and a later recall each append to the chain. Those records leave the twelve-state as it was. The self-knowledge sentence stays Emeth's wording and is not written by this loop.
