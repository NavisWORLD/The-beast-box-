# W5 cap census — 2026-11-09

Base: `origin/main` `0995ff2fb32115fd6c97daf18caf3a9f8363c3cf`.
Pattern: PR #845, commit `dd679b809` (`forever door: append-only full thread archive + own-thread retrieval of turns past the 40-turn window`). The window stays small. The archive is append-only. A reader reaches the full record.
This change deletes no stored blob, file, or archive line. Records already dropped before an archive existed are not reconstructed.

Tests run 2026-11-09T18:00:51Z, from `apps/beastbox-cloud`:

```
node --test tests/forever-archive.test.mjs tests/zeref-classroom.test.mjs tests/beast-talk.test.mjs tests/zeref-loop.test.mjs tests/companion-local.test.mjs tests/living-core-roam.test.mjs tests/god-core-behavior.test.mjs tests/companion-tabs.test.mjs tests/world-live.test.mjs
```

Result: 72 pass, 0 fail.

```
PYTHONPATH=. python3 -m pytest tests/test_guest_hebbian_archive.py -q --tb=short
```

Result: 3 passed (repo root).

No live URL. These caps are stores and windows. They are not a deployed page.

## Converted in this change

The window size is unchanged. The archive is the record a reader can recompute.

| Cap | Window (unchanged) | Archive and reader | Lines |
|---|---|---|---|
| Guestbook thread | `MAX_THREAD_TURNS=40`. `appendExchange` still clips the window copy to 700 / 1200. | `appendArchive` stores the full `guestText` and `reply`. `readArchive` parses every line. The old `MAX_ARCHIVE_READ_BYTES` (8_000_000) cutoff that returned `[]` is gone. | `apps/beastbox-cloud/lib/cosmos/forever-store.mjs` 32, 85–92, 110–131, 140–142 |
| Guest events | `events.jsonl` tail `MAX_GUEST_EVENTS=300` | Monthly shard written first. `readGuestEventArchive` reads every `beastbook-guest-event/v1` line. Counts only, no guest text. | same file 33, 180–214 |
| Classroom experiences | Tail `MAX_CLASS_RECORDS=2000`, thread `MAX_CLASS_TURNS=40`. Tail text stays clipped at 1200. | Shard line adds `teacher_text_full` / `reply_full` when the original is longer. `readClassArchive` reads the shards. | `apps/beastbox-cloud/lib/cosmos/classroom-store.mjs` 28–29, 60, 68–104 |
| Loop moments | `KEEP_MOMENTS=24` | `moment_archive` appends every moment for the life of the loop state. `verifyMoments(archive)` is what the test checks. | `apps/beastbox-cloud/lib/loop/loop-chain.mjs` 25, 102–108 |
| Companion memory (JS) | `search` `k` is the prompt window | `CompanionMemory.add` no longer `slice(-200)`. The array is the record. | `apps/beastbox-cloud/lib/companion-local.mjs` 137 |
| Companion memory (Python) | `search()` `k` is the window. `MAX_RECORDS=200` remains as a retired constant. | `add` appends. The JSON file keeps every record. | `beastbox/companion_local/memory.py` 17–18, 84 |
| Talk log | `MAX_LOG=24` | `beastbox-talk-log-archive-v1:` appends by id. `readTalkArchive` returns it. An empty write clears the window key only. Quota failure does not delete the stored archive. Same function in both copies. | `apps/beastbox-cloud/lib/companion/beast-talk.mjs` 369–408 and `apps/beastbox-cloud/public/spark/shared/beast-talk.mjs` 366–404. Panel list still cuts at `public/spark/chat-popup.mjs` 242 before the write; the archive keeps rows from earlier writes. |
| Spark emotion diary | Display `slice(-30)` | `beastbox-emotion-diary-archive-v1:<seed>` appends. Quota failure leaves the stored archive. | `apps/beastbox-cloud/public/spark/app.mjs` 100–116 |
| Companion session chat | Prompt window 80 turns. Display text of the visitor line is `slice(0, 400)`. | `chatArchive` keeps the full visitor string and every reply. `exportSession` / `importSession` round-trip the archive. Both copies. | `apps/beastbox-cloud/lib/companion/session.mjs` 193–203, 220, 235–236 and `apps/beastbox-cloud/public/spark/shared/session.mjs` |
| Behavior log | `events` window 32, `memory` window 24 (validator contract) | `eventsArchive` and `memoryArchive` append. `kind_full` is archive-only; the window `kind` stays `slice(0, 32)`. Both copies. | `apps/beastbox-cloud/lib/companion/behavior.mjs` 72–83 and `apps/beastbox-cloud/public/spark/shared/behavior.mjs` 83 |
| Pocket journal | Combo display `slice(0, 60)` | `keys` is no longer `slice(-4000)`. `combosArchive` keeps every combo. | `apps/beastbox-cloud/lib/zeref/pocket-journal.ts` 20–25 |
| Living-core creations | Draw list `MAX_CREATIONS=12` | `beastbox-lc-creations-archive-v1` appends on each `saveCreations`. `readCreationsArchive`. A creation is kept only if some save saw it while it was still in the window. | `apps/beastbox-cloud/lib/living-core/roam-brain.mjs` 75–85 |
| Guest Hebbian prompt | `load()` stays `MAX_TURNS=40` plus `MAX_THREAD_CHARS`, TTL, and `max_guests` | `guest_archive` was already INSERT-only. `retrieve()` returns up to `k` older archive turns by word overlap, oldest first. `guest_local.py` prepends them to `history`. `assemble_messages` still cuts oldest first to fit the model. | `beastbox/guest_hebbian.py` 47, 49, 287–305, 355–366. `beastbox/guest_local.py` 271 |

`moment_archive`, session `chatArchive`, and behavior archives live in the process or the exported session object. They are not a new disk chain. See the proposal below for persisting moments beside the diary.

## Already append-only before this change (PR #845 and the diary file)

- Guestbook archive prefix check: `forever-store.mjs` 149 (`body.startsWith(old)`).
- Monthly shard helper: `forever-store.mjs` 160–177.
- Diary summary `summarize` is a reader window (`zeref-diary.mjs` 265–271, `entries.slice(-limit)`). It does not rewrite `diary.jsonl`.

## Proposals — not changed

These can drop, hide, or clip a record, and this PR does not touch them.

1. **Diary thought clip, hashed.** `apps/beastbox-cloud/lib/zeref/zeref-diary.mjs` 234: `thought.text.trim().slice(0,280)` before the line is hashed. A longer thought is not in the chain. Changing the hashed field changes every later diary line. Proposal: an append-only sibling file for the full thought, not a rewrite of the chain. Not this seat's edit.

2. **Public diary read cap, fail-closed.** `beastbox/lived_chain_public.py` 108 and 139–154: `_DIARY_MAX_BYTES = 16_000_000`. A larger `diary.jsonl` publishes no head. The file itself is not truncated. Proposal: stream the chain when it crosses 16MB. Not a drop-oldest, and not changed.

3. **Model context windows.** `beastbox/guest_hebbian.py` 39, 43–44, 96, 111, 122, 127, 182, 202, 210: `MAX_CONTEXT_TOTAL=1300`, `MAX_ASSEMBLED_BYTES=1900`, `MAX_REPLAY_MESSAGES=28`, and the 32-message server cap. These are the prompt the model accepts. `retrieve()` feeds older turns into that window. Raising the window is a model-contract change and is not done.

4. **Hebbian fast weights.** `beastbox/guest_hebbian.py` 5–12. The matrix is an in-process activation rebuilt from the thread. The server has no channel to store it. The thread archive is the record. Not converted, because there is no matrix to append.

5. **Training-export windows.** `apps/beastbox-cloud/scripts/zeref-cloud-sync.mjs` 18 and 24 take the newest 1500 lesson blob names. Line 37 takes the newest 400 diary lines for `--experiences-out`. The Azure blobs and `diary.jsonl` stay. Widening the export changes what a growth round trains on. Left to the growth seat.

6. **Teacher pairs, local.** `apps/beastbox-cloud/lib/companion/teacher-distill.mjs` 17, 47–48 and `public/spark/shared/teacher-distill.mjs` same lines: `MAX_LOCAL_PAIRS=200`, `writePairs` stores `rows.slice(-200)`. This is a local lesson store that drops the oldest. It feeds training review. Not converted here, so the training-mix window stays exactly as it is.

7. **Private-chat import and merge.** `lib/companion/private-chat.mjs` 22 (`slice(-64)`) and 32 (`mergePrivateChat` returns `slice(-24)`), same lines under `public/spark/shared/private-chat.mjs`. The cloud record is the source. The device copy is a window. Not changed: the merge return is the stored device list, and lengthening it changes an unverified import.

8. **Sensor notes.** `lib/companion/sensory-bridge.mjs` 64, `lib/companion/session-store.mjs` 11 and 40, `components/beast-session.tsx` 58 and 66, `components/live-senses.tsx` 137: observation lists `slice(-8)`, and the note text is `slice(0, 180)`. UI windows, not the diary. Proposal: an archive key beside the 8-line display. Not changed.

9. **Applied-growth id window.** `lib/companion/session.mjs` 122 and the public copy: `localGrowth.applied` `slice(-64)`. Dropping an old id can let the same event apply again. Not an archive candidate. Not changed.

10. **Blob listing cap.** `apps/beastbox-cloud/lib/cosmos/azure-blob.mjs` 103 and 114: `listBlobs` default `max=5000`, then `names.slice(0, max)`. A prefix with more than 5000 names hides the rest, so `readClassArchive` / `readGuestEventArchive` would miss shards. Monthly shards do not approach that count. Proposal: page with `NextMarker` until the marker is empty. Not changed.

11. **Loop moments on disk.** `moment_archive` dies with the process. Persisting it into `diary.jsonl` would change the hashed life chain. Proposal: a sidecar jsonl that is not a diary line. Not written.

12. **Browser quota.** `localStorage.setItem` can throw. The new archives catch that and leave the previous archive bytes in place. They cannot grow past the browser quota. A visitor clearing site data removes the device copies. That wipe is outside this code.

13. **Guestbook window clip of the carried prefix.** `appendArchive` carries `windowTurns` as they already are (`forever-store.mjs` 147). Those window turns were clipped at 700/1200 when `appendExchange` wrote them. New exchanges archive the unclipped text (line 142). Turns that left the window before the archive existed are not recovered.

## What was not touched

Gates, thresholds, eval sets, held-out sets, labels, and `apps/beastbox-cloud/lib/rawrphos-public-pin.json`. No `Math.random`. No QPU. No data deleted.
