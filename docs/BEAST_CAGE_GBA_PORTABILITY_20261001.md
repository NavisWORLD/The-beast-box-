# BEAST CAGE GBA — portable character, privacy boundary, deployment

**Branch:** `feature/beast-cage-guest-gba-export-20261001` based on current PR #169
head `cd7c45f`. Preserve the creator's existing 3D turntable, genuine stateless
RAWRPHØS guest route and previous source changes.

**Guest product:** `/beast-cage/guest` is a no-account character playground.
Buttons intentionally animate *illustrative game moods*, not fabricated real
sensing/model activity. `/beast-cage/talk` stays a separate actual bounded
guest model endpoint, with errors if the existing host isn't available.

**Portable export:** The guest downloads a self-contained ZIP with 4x64×64
4bpp GBA sprites, BGR555 16-color palette, generated C array header, editable
source art, portable C99 GBA renderer/sample, Codex AGENTS.md and v1
`companion.soul.json`/`BCG1` binary config. The default guest **never**
includes real memories or signal telemetry.

**Explicit authenticated owner option:** only `/workspace` Synapse Trace
shows opt-in export of a strictly validated, checkpoint-backed runtime receipt.
The user must click the consent box before the file is generated locally.
The whitelist is checkpoint sequence, SHA-256 and 12+12 finite numeric CNS/
synaptic vectors. There are no transcripts, auth tokens, private memory texts,
RAWPHØS weights, real hardware observations or new tool permissions.

**GBA reality:** A physical GBA does not execute the frontend's WebGL model
or a multi-million-parameter language model. The importable game asset/runtime
is independent of cloud. A future serial bridge or ROM integration requires
a real host, consented transport and target hardware tests.

**Verification:** CI runs real C99 syntax checking, full Next.js tests/build,
five device-size real Chromium guest browser sessions, download inspection
of actual ZIP and byte-level checks on sprite and compact snapshot layout.
Authenticated live checkpoint export and physical iPhone/GBA hardware must
be tested separately with the owner's private data/permission.

**Deploy:** Vercel's `main` auto-deploy is intentionally disabled in
`apps/beastbox-cloud/vercel.json`. Change to main through reviewed merge
and perform the existing one-time approved deploy guard sequence, then verify
the *new* public `/api/gba-release` marker and guest routes before restoring
the guard. Do not equate green preview checks with live production.
