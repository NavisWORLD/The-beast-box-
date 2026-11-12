# Owner feed (Cory / NavisWORLD only)

Commit a `.txt` or `.md` file here and `.github/workflows/zeref-owner-feed-ingest.yml` takes it in on its own:

1. The file is split into chunks of at most 1200 UTF-8 bytes (the bridge's text cap), on sentence boundaries. No words are dropped.
2. Each chunk is one tick. Twelve features are measured from its text (counts and ratios, nothing random) and drive the public `dyn12` reference dynamic. The 12D state carries over from tick to tick and from file to file.
3. Each tick writes a RECORDED sensor snapshot and a hashed, append-only chain entry to the `zeref-owner-feed` data branch (`owner-feed/`). It never writes to `main`.

The whole file gets absorbed over as many ticks as it needs. Any length works, because each tick is bounded and gets folded into one fixed-size state. That is not literal infinite context. The 12D state is a lossy summary, and the chain keeps the record.

**These are candidates only.** Every snapshot is `training_eligible:false`. Nothing here enters training unless Cory makes a fair-gate decision, and G1–G10 stay unchanged. Guest chats never come through this folder.

The workflow only runs for pushes or dispatches by NavisWORLD, and only when every pushed commit is authored by NavisWORLD.

## Files

- `in-the-land-of-eridoria.txt` is Cory's story. He attached it to Feed Zeref issue NavisWORLD/NavisWORLD#30 on 2026-11-12 at 12:33 PM CT and marked it "Public domain". The issue's intake turned it away because its source-URL field was not an https link. sha256 `35ee703cac4fc0f237cc9490f5c350c71f6688d98fd1f49fc73f69feb7349952`, 82,575 bytes, unchanged from the attachment.
