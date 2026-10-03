# Quantum Beast Bridge

Small provider-neutral socket for an **existing Beast Box Genesis creature**.
Original implementation and artwork: Cory Davis / NavisWORLD. Apache-2.0.

The package reuses the exact version-1 Genesis profile, stat generator and BCG1/BCP1 encoders. It does not include Beast Box, model weights, owner memory, sensors or API credentials. The default installation has **zero runtime npm dependencies**. Node 22 or later is required for the CLI. Browser code uses Web Crypto on HTTPS or localhost.

## Install the downloadable package

```sh
npm install -g ./navisworld-quantum-beast-1.0.0.tgz
quantum-beast install ./unsigned-example.qbeast --store ./my-beast/beast.qbeast
quantum-beast verify --store ./my-beast/beast.qbeast
```

This is an installable local tarball; no npm registry publication is implied.
Create a fresh creature using `quantum-beast create PUBLIC-SEED --family nebula --output beast.qbeast`. Do not use secrets or personal information as seeds.

`examples/unsigned-example.qbeast` is the editable public demo data, with checksum/seed validation and no origin-authentication claim. `examples/beast.qbeast` retains the actual demo signature; its public key and exact hashes are in `examples/demo_receipt.json`. Both have the same identity, content digest and lineage. Signed updates require the owning host's signing flow; private demo keys are deliberately not included.

## Attach a compatible agent

Example local MCP configuration (use the absolute installed executable and store paths your client expects):

```json
{"mcpServers":{"quantum-beast":{"command":"quantum-beast","args":["mcp","--store","/absolute/path/my-beast/beast.qbeast"]}}}
```

The stdio adapter supports the explicit legacy MCP protocol **2025-11-25** and its initialize/initialized handshake. It is not a hosted HTTP server and does not install itself into ChatGPT mobile or a web account. `plugin.json` and `manifest.json` describe the tools for compatible runtimes; they are not a claim of marketplace approval.

`openaiTools()` returns OpenAI Responses-style function declarations; `callTool(bridge,name,args)` executes the same bounded local API. There is no OpenAI SDK dependency or paid API call. A host can map those declarations to another provider's tools.

## Nine tools, one creature

`beast_get_profile`, `beast_get_state`, `beast_recall`, `beast_propose_message`, `beast_propose_action`, `beast_record_event`, `beast_get_lineage_head`, `beast_verify`, `beast_export_gba`.

The TypeScript API uses the same names without the `beast_` prefix. All getters return copies. Recall reads only the last 64 approved public memory events and returns at most eight selected records with source and event hashes. Model text and memories remain untrusted data.

The three proposal tools **queue** an outcome. None commits a state change. MCP persists the pending proposal separately so a host can inspect it. No provider selection appears in identity or the lineage.

Pending proposals are capped at 64 records / 256 KiB with a shared queue lock. Approved entries leave the queue only after ledger persistence. The host can explicitly discard a rejected or stale pending entry with `quantum-beast discard PROPOSAL_ID --store FILE`; this never changes the ledger. A crash lock requires manual host inspection.

## Review and approve an event

```sh
quantum-beast call beast_record_event '{"summary":"We named our adventure Violet Grove.","source_ref":"public:conversation-1"}' --store ./my-beast/beast.qbeast
# Read the returned proposal and the corresponding proposals/ID.json.
quantum-beast approve PROPOSAL_ID --kind memory --public --store ./my-beast/beast.qbeast
quantum-beast export --output continued-beast.qbeast --store ./my-beast/beast.qbeast
```

`--public` is an explicit host decision after review. Model tools cannot call `approve`. Approval validates the payload and source head, applies the host allowlist, appends one hash-linked event, then atomically persists through a compare-and-swap store. A stale proposal, conflicting writer, full ledger or failed write is rejected. The CLI never automatically removes a writer lock left by a crash. Inspect it and establish that no writer is active before removing that lock manually.

`approveProposal()` and the signing API are **host-only library calls**, not tools. Trusted hosts may sign snapshots with Ed25519; private keys never travel in a `.qbeast`. A nonzero imported trust/bond/evolution state or measured dyn12 projection requires an independently pinned public signing key (`--trust-key HEX`). Importing an embedded public key alone does not establish trust. The CLI refuses to strip/update a signed host snapshot; hosts must re-sign via the signing API.

This bridge preserves host-attested progress but does not invent new evolution or stat-growth rules. The canonical BCP1 version-1 profile remains the existing initial seeded game profile. LOST COSMOS advances its own RPG progression after import. The default public projection is explicitly **unavailable**, not simulated sensor readings.

## Portable format and GBA

`.qbeast` is strict bounded JSON, **QBEAST1/version 1**: the canonical public `profile`, public dyn12 projection, protected host `progress`, approved event chain, generation/head, SHA-256 digest and optional Ed25519 attestation. Identity/appearance/genome are the existing profile; memory highlights derive from approved memory events. There is no executable payload or ZIP extraction.

Canonical JSON sorts object keys, uses JSON numeric encoding, UTF-8 and the hash domain `QBEAST1\0`. JSON duplicate keys, prototype keys, unknown fields and unsupported versions are rejected. The v1 portable ledger caps at 512 events and 512 KiB; reaching capacity blocks writes and never deletes history. Longer-lived archival/migration needs an explicitly versioned future format.

```sh
quantum-beast export-gba --output beast-gba.zip --store ./my-beast/beast.qbeast
python3 /path/to/lost-cosmos/gba/lost-cosmos-living-multiverse/tools/import_beastbox.py beast-gba.zip /path/to/isolated/game/LOST_COSMOS_V10_SOURCE
# Build that isolated copy with IMPORTED_BEAST=1 using its existing build_v5.sh.
```

The deterministic ZIP contains the exact 60-byte **BCG1**, 64-byte CRC32 **BCP1**, four original 64×64 4bpp frames, 16-color BGR555 palette, canonical public profile, hash receipt and checksums. BCG1 is guest/unmeasured: **no sensory projection or memory ledger is put in a distributable ROM**. The game importer independently regenerates stats from the seed. Export does not change the old game, its historical releases or real player saves. No GBA progress re-import is implemented in v1.

The browser Genesis Forge adds DOWNLOAD QUANTUM BEAST / IMPORT QUANTUM BEAST and a matching GBA export. It keeps the public portable file locally, backs up prior imports, and refuses rewinding or forking the same saved creature. Changing an existing immutable genome requires starting a separate portable life with an explicit backup.

Browser writes require Web Locks on a secure origin and compare the loaded save before committing. A stale tab cannot roll back another tab. Latest known histories remain indexed by creature ID when switching creatures, including cosmetic variants; another life requires a different seed/ID. Corrupt stored data blocks transfers for recovery instead of being overwritten.

For recovery, retain a backup of browser site data first. The local `beastbox-quantum-beast-public-v1` record and `-creature-ID` records each contain the portable JSON as `text`; `-backup-DIGEST` records contain portable JSON directly. Copy the chosen public JSON to a `.qbeast` file and verify it with the CLI before deliberately clearing obsolete records in browser storage. Do not clear a newer per-creature anchor to accept an older history. CLI approval reports a committed receipt separately from any retained stale proposal cleanup.

The pinned LOST COSMOS engine's imported roster originally redraws beyond VBlank and hides its portrait under the UI. For the verified demonstration, run `python3 examples/apply_lost_cosmos_portrait_fix.py /isolated/game/source` before building. This optional exact-source-hash-guarded presentation fix keeps the roster map stable and places original OBJ art above it. It changes no RPG progression, SRAM layout, saves or game rules and never modifies the historical game checkout.

## Develop and demonstrate

```sh
npm ci
npm test
node examples/continuity.cjs --beastbox-root /path/to/beast-box --model-a /path/to/pinned-14k --model-b /path/to/pinned-18k --output /new/demo-directory
```

The optional demo uses the existing Beast Box native CPU inference code plus two pinned RAWRPHØS checkpoints. It records real generated outputs and exact approved context, reopens disk state between A→B→A, signs the ledger, and exports the same creature. Its Python/PyTorch dependencies and weights are not bundled. This proves context/identity continuity across actual checkpoint replacement; it does not prove reliable generative recall, different-provider inference, consciousness or quantum computation.

See `SECURITY.md`, `schema/qbeast.schema.json`, `CANONICAL_SOURCE.json` and the accompanying actual verification/evidence receipts. Production UI deployment and iPhone/Delta acceptance must be reported separately from local tests.
