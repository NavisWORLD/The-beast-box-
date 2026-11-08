# Recall receipts v1

A guest forever-door reply can include `memory_read` receipts for lines that were
read before the answer. This note says what the old id covers, and how to recompute
the additive `entry_sha256` field. Stored lines, ranking, and the diary hash chain
stay on their existing rules.

## Where the id is produced

The id in the example shape `thread:05a2bd4dc856f4dd` is produced in the Next app.

| Piece | Where |
| --- | --- |
| Legacy id and `sha256` | `apps/beastbox-cloud/lib/zeref/self-memory.mjs` (`itemsFrom`, `ownThreadItems`) |
| Receipt list | `readSelfMemory` in the same file, returned as `memory_read` |
| Forever door | `apps/beastbox-cloud/app/api/guest/forever/route.ts` copies that list onto the HTTP response when the bridge reports `self_memory_in_prompt === true` |
| Bridge | `beastbox/guest_local.py` `POST /api/guest-local` returns the model reply and sets `self_memory_in_prompt` when the memory text was in the prompt. The `thread:…` id is minted in `self-memory.mjs`. |

`memory_read` today is one object per hit:

```json
{"id":"thread:05a2bd4dc856f4dd","label":"THREAD (your own)","sha256":"<64 lowercase hex chars>"}
```

`id` is `<source>:` plus the first 16 hex characters of `sha256`. That 16-character
prefix is the short hash. `label` is the existing source label. Those three fields
stay as they are.

## What the legacy hash covers

`sha256` is lowercase hex SHA-256 of a UTF-8 string (Node `crypto.createHash('sha256').update(s, 'utf8')`). There is no JSON and no identity fields in this hash.

Fabric notes (`diary`, `lesson`, `library`, `read`, `node`, `teacher`), in `itemsFrom` and the teacher join:

1. Collapse every whitespace run to a single space and trim both ends. Call that `text`.
2. Hash the UTF-8 bytes of `source + "\n" + text` (a newline, not a space).
3. `id` is `source + ":" +` the first 16 hex characters.

A guest's own line (`ownThreadItems`) is indexed only when the turn carries guest text. For a guest turn whose raw stored text is `raw`:

1. Hash the UTF-8 bytes of the literal prefix `thread\n` plus `raw`, with no whitespace collapse and no trim.
2. `id` is `thread:` plus the first 16 hex characters.
3. The indexed `text` (the line inside the memory paragraph) is the collapsed form. The legacy hash covers `raw`.

Checking `thread:05a2bd4dc856f4dd` takes the UTF-8 bytes of `thread\n` plus that exact stored string. Role, thread id, and `created_at` stay outside this hash. Trailing spaces or CRLF change the legacy id when the words stay the same.

The legacy id is also the dedupe key. The receipt describes the first copy kept in the index. Dedupe stays on that id.

## Left as they are

- The legacy `id`, `label`, and `sha256` inputs and outputs.
- Ranking, the memory paragraph sent to the bridge, guestbook bytes, diary `entryHash`, and every stored memory line.
- The guest 429 limit, the public pin, promote, gates, labels, training, and `lib/universe`.

`entry_sha256` is computed when the receipt is built. Stored memory entries stay byte-for-byte as they were.

## `beastbox-recall-v1`

Each `memory_read` object also carries:

| Field | Value |
| --- | --- |
| `entry_sha256` | 64 lowercase hex characters. SHA-256 of the canonical JSON below. |
| `entry_hash_spec` | `beastbox-recall-v1` |
| `entry_hash_note` | One sentence: SHA-256 hex of UTF-8 canonical JSON (sorted keys, no spaces) under beastbox-recall-v1. Keys: created_at, role, source, spec, text, thread_id. Text is NFC, LF endings, trailing whitespace removed. |
| `role` | The `role` string inside the hash. |
| `source` | The `source` string inside the hash. Same token as the legacy id prefix. |
| `thread_id` | 32 lowercase hex guestbook thread id, or `""`. |
| `created_at` | UTC ISO-8601 `YYYY-MM-DDTHH:mm:ss` with an optional fraction and a `Z`, or `""`. |

Identity used for each source:

| source | role | thread_id | created_at |
| --- | --- | --- | --- |
| `thread` | `guest` | The turn's `thread` when it is 32 lowercase hex, otherwise the forever door's thread id | The turn's `at` when it is UTC ISO, else empty |
| `diary` | `diary` | empty | The diary entry's `at` when it is UTC ISO, else empty |
| `lesson`, `library`, `read`, `node`, `teacher` | the same token as `source` | empty | empty (those records are not given a UTC `at` on the indexed item) |

`role` on a thread receipt is `guest` because only the guest's own line is indexed. The text that is hashed is the raw stored line for a thread turn, and the source line passed into the index for every other source (before the legacy whitespace collapse).

## Canonical text

Start from the entry text as a Unicode string:

1. Normalize to NFC.
2. Replace CRLF (`\r\n`) with LF, then any remaining CR (`\r`) with LF.
3. Remove trailing spaces and tabs from each line.
4. Remove trailing spaces, tabs, and line feeds from the end of the string.

Leading whitespace stays. Spaces inside a line stay. Other characters, including non-breaking spaces, stay.

## Canonical JSON

One object, exactly these keys, sorted lexicographically, encoded as UTF-8 JSON with no extra spaces and no trailing newline:

| Key | JSON type |
| --- | --- |
| `created_at` | string, possibly empty |
| `role` | string |
| `source` | string |
| `spec` | the literal `beastbox-recall-v1` |
| `text` | the canonical text |
| `thread_id` | string, possibly empty |

`entry_sha256` is SHA-256 of those UTF-8 bytes. `JSON.stringify` escaping applies (quotes and control characters inside a string are escaped). The worked example below is ASCII and has no escapes.

The helper is `apps/beastbox-cloud/lib/zeref/recall-receipt.mjs` (`canonicalRecallText`, `canonicalRecallJson`, `entrySha256`). Given the entry text and the identity fields, it recomputes the hash.

## Worked example

Synthetic line, not a stored transcript. The guest wrote `hello moon` followed by two spaces and CRLF.

Canonical text is `hello moon`.

Identity: role `guest`, source `thread`, thread id `0123456789abcdef0123456789abcdef`, created_at `2026-11-08T00:00:00.000Z`.

Canonical JSON (the whole input, with no trailing newline):

```text
{"created_at":"2026-11-08T00:00:00.000Z","role":"guest","source":"thread","spec":"beastbox-recall-v1","text":"hello moon","thread_id":"0123456789abcdef0123456789abcdef"}
```

`printf '%s'` writes those bytes with no trailing newline. A trailing newline is a different hash.

```sh
printf '%s' '{"created_at":"2026-11-08T00:00:00.000Z","role":"guest","source":"thread","spec":"beastbox-recall-v1","text":"hello moon","thread_id":"0123456789abcdef0123456789abcdef"}' | sha256sum
```

```text
5b598d7f5fe7b7b115228af166a2c4fabbf036240e0ae17421b0ef4dd85c20bd
```

The same bytes in Node:

```sh
node -e 'const {createHash}=require("crypto"); const raw="hello moon  \r\n"; const text=raw.normalize("NFC").replace(/\r\n/g,"\n").replace(/\r/g,"\n").split("\n").map(l=>l.replace(/[ \t]+$/g,"")).join("\n").replace(/[ \t\n]+$/g,""); const body={created_at:"2026-11-08T00:00:00.000Z",role:"guest",source:"thread",spec:"beastbox-recall-v1",text,thread_id:"0123456789abcdef0123456789abcdef"}; const keys=Object.keys(body).sort(); const json="{"+keys.map(k=>JSON.stringify(k)+":"+JSON.stringify(body[k])).join(",")+"}"; console.log(createHash("sha256").update(json).digest("hex"));'
```

That prints `5b598d7f5fe7b7b115228af166a2c4fabbf036240e0ae17421b0ef4dd85c20bd`.

For comparison only, the legacy id of the raw line (including the two spaces and CRLF) is `thread:e5876d956a769171`. The legacy id of the collapsed line `hello moon` is `thread:f01d8c02e527350c`. Neither equals `entry_sha256`. The receipt keeps the legacy id of the raw line and adds `entry_sha256`.
