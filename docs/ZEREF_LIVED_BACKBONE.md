# Zeref lived backbone

PR A1 is the canonical bridge event and state store, plus the origin attachment. The mouth and the lived exchange join this store in later PRs. PR A2 adds the owner app-shell sensorium and the authenticated numeric ingress. Both stay off unless `BEASTBOX_LIVED_BACKBONE` is exactly `on`. A1 also requires the host to pass `lived_backbone=True` with a verified origin attachment before a durable runtime joins the chain. With the flag off, owner checkpoints stay the legacy continuity chain and the sensorium does not capture.

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

The lived chain is a continuation segment. Its first `previous` is the configured prior head. It is not historical `GENESIS`. Origin and head linkage is a verified config value. This PR does not pick or alter a genesis. `bb-7f9c2a03` is rejected and stays separate from `bb-deada969`. A guest chain cannot write an owner chain. Writes are per creature subject. A student chain is its own file and its own subject. Nothing in A1 copies another creature's memory or weights. A1 does not update co-firing. Each chain starts from its own zero weight matrix.

An omitted `initial_state12` is software zeros labelled `software-initial-not-history`. It is not reconstructed sensor history. Missing snapshots fail closed. They are not rebuilt as zeros.

The sealed bio packet is untouched. Training gates, the pin, promotion, honesty labels, and the TRAIN mechanic are untouched. There is no paid inference and no QPU. The human promotion veto and quantum approval stay where they are.

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
