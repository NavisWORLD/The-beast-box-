# Synapse Flash / portable state

**Normal language:** Copy a checked snapshot, then continue your story in a new
state directory. **Engineering:** SQLite backup, versioned manifest, SHA-256 and
checkpoint validation. **Evidence:** the `Portable state Linux to Windows` workflow
exports from an installed Linux wheel and imports on a Windows runner. Only a
successful attached handoff receipt establishes that run's platform result.

This is a **portable directory**, suitable for copying onto authorized removable
storage. It is not the separate [Synapse OS USB disk flasher](https://github.com/NavisWORLD/Synapse-os-/blob/main/FLASH_USB.md).
These commands do not format USB drives or install an operating system.

```bash
beastbox runtime export ./portable-story --data-dir ./my-beast
# Retain the printed manifest_sha256 separately from the copied directory.
beastbox runtime verify-portable ./portable-story --sha256 MANIFEST_HASH
# Copy the entire directory to the destination machine, then verify it there.
beastbox runtime import ./portable-story --sha256 MANIFEST_HASH --data-dir ./restored-beast
beastbox runtime inspect --data-dir ./restored-beast
beastbox runtime chat "Recall the code word" --data-dir ./restored-beast
```

A snapshot contains exactly `runtime.sqlite3` and `manifest.json`. It preserves
memory, software state, routing and provenance. It excludes `.env`, model/provider
settings, credential stores, model binaries, arbitrary files and host authority.
The new runtime defaults to no tool permission; the owner must grant any supported
capability again. Imported manifests cannot supply file paths or permissions.

Exports use a consistent SQLite snapshot and an atomic same-parent directory
rename after verification. Imports verify the source, copy into a private staging
directory, verify the copied bytes, then rename into a fresh destination. Failures
remove staging files and leave existing data unchanged. Existing destinations are
rejected, including empty directories: choose a new name. Keep the previous state
until the restored state is verified; rollback means selecting that previous store.
Paths through symlinks or `..` are refused. Version 1 supports snapshots up to
256 MiB and the current `continuity-checkpoint-v1` schema.

## Privacy and practical limits

The database is plaintext. Conversation text may contain sensitive information.
Export refuses recognizable private keys/GitHub tokens and exact matches to known
configured credential variables. This is **not a universal secret detector**; do
not paste credentials into chat. Export cannot redact history without changing its
hashes, so suspected credential content fails closed rather than being rewritten.

Hashes detect corruption against the separately retained expected hash; they are
not signatures. A privileged host can replace both the story and its receipts.
Use owner-controlled local directories. Atomic rename does not guarantee survival
of power loss or arbitrary USB/network filesystem behavior. USB media, physical
machines and every filesystem are not certified by a hosted-runner test. Safely
eject removable storage and verify again after copying. No infinite memory promise.
