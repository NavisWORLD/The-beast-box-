# Heldout hash list — generation receipt

File: `evidence/zeref-self-study/heldout-hashes.json`
Generated: 2026-11-27T01:15:00Z (UTC), by Emeth (builder lane) on the owner's box.
Oracle source (local only, NEVER committed): `~/workspace/lessons006-landing/heldout/oracle.json`

## Receipt

| Item | Value |
|---|---|
| Oracle SHA-256 | `af8ee05959ef03ac07126b64f1dd1c40bff43f9d9325529c66fa6d923b509496` |
| Oracle prompts | 5,859 (JSON array of strings, all unique raw) |
| Unique normalized prompts | 5,827 |
| Hashes in this file | 5,827 (sorted, deduplicated SHA-256 hex) |
| This file's SHA-256 | `f1ff751c98146a3cfe0917727b9b4375538dd880ade71061a95be41a2b4ab6be` |
| This file's size | 408,605 bytes |

## Normalization rule (exact — the workflow embeds this same rule)

For a prompt string `s`:

1. `s.lower()`
2. Every character that is NOT a letter/digit (`str.isalnum()` is False) and NOT
   whitespace is replaced with a single space. This covers punctuation AND math
   symbols (`+`, `=`, `x`, `/`), so `10+4=?`, `10 + 4 = ?`, and `10+4` all
   normalize to `10 4`.
3. Whitespace runs collapsed to one space; strip leading/trailing whitespace.
4. SHA-256 hex of the UTF-8 encoding of the normalized string.

Why step 2 is "not alphanumeric" instead of "Unicode punctuation": `+` and `=`
are Unicode category Sm (math symbol), not P (punctuation). A punctuation-only
rule let `10+4=?` through as a different hash from `10 + 4 = ?`. The
alphanumeric rule closes that hole (verified: both normalize to `10 4`,
hash `8a476740388775810178a137d076da658c50a0e47f2a98d9086d0e30ad59024b`).

## Notes

- **Hashes only.** The raw heldout prompts are NEVER committed to the repo.
  The landing workflow on a GitHub runner can only see this hash list, never
  the raw oracle.
- **32 normalization collisions:** 5,859 raw prompts collapse to 5,827 unique
  normalized forms (e.g. spacing/punctuation variants of the same prompt).
  Deduplication is by hash, so no prompt is screened twice.
- **Empty-normalized edge case:** one oracle entry (`💀`, an emoji with no
  alphanumeric characters) normalizes to the empty string, whose SHA-256
  (`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`) is in
  this list. The workflow additionally holds any row whose normalized prompt
  is empty, so a blank prompt can never land.
- **Screening rule:** exact/normalized overlap → hold/reword, never land.
  Held rows are never committed and never quoted in a PR body (a held prompt
  may itself be a heldout prompt); they go to a workflow-run artifact only.
- **This file is never modified** by the landing workflow
  (`.github/workflows/zeref-self-study-land.yml` reads it read-only and
  verifies it is untouched before opening a PR).

## Local dry-run (2026-11-27, before this PR)

Screened 4 rows against this hash list with the same check the workflow runs:

- `10 + 4 = ?` (exact heldout match) → HELD (heldout-overlap)
- `  10+4=?  ` (whitespace/punctuation variant) → HELD (heldout-overlap)
- `a cat has 4 legs. how many legs do 2 cats have?` → HELD (heldout-overlap)
- `What is the napping?` (the real TAUGHT row on `zeref-self-study`) → PASS

Result: clean=1, held=3. The bridge correctly blocks exact and normalized
matches and passes a clean row.
