# Private production recovery: existing Railway Hobby plan, no snapshot feature

**Operator-run procedure, not an executed backup receipt.** Current Railway inspection reports Hobby plan volume backups are unavailable. Existing deployment snapshot IDs do not attest a recoverable volume archive. The connector available to the assistant cannot execute in-container shell commands or make a private file transfer, so do not merge the backend PR on the strength of this document alone.

The running production image at the reviewed handoff SHA `c63df708eab85f0d427eca16bd2bb285254aef75` already contains `/app/apps/beastbox-cloud/bridge/export_bundle.py` and `beastbox.portable_state`. That export creates an SQLite online backup of `runtime.sqlite3` and a hash-bound continuity manifest; it does **not** contain all volume files, the encrypted owner credential vault, its host-only key, or all deployment configuration. A verified portable snapshot alone is NOT a whole-production rollback.

## Owner-only private access

Use your own trusted, encrypted computer (not GitHub Actions, a public console recording, a paste service, or a ChatGPT upload). Install/log in to the official Railway CLI and register your own SSH key if prompted. Railway documents `railway ssh` and encrypted `scp` at https://docs.railway.com/cli/ssh. The verified production service domain is `cosmos-owner-bridge-production.up.railway.app`.

Open a private terminal to the **existing** deployment without redeploying:

```sh
railway ssh -p 0f127a08-6074-4612-87bb-da8837f28fa1 -s cosmos-owner-bridge -e production
```

Within that private Railway shell, inspect the **filenames only** under `/srv/beastbox/data`; do not share the output. Confirm sufficient ephemeral free space. Use a unique filename rather than overwrite any existing archive:

```sh
umask 077
python /app/apps/beastbox-cloud/bridge/export_bundle.py \
  --root /srv/beastbox/data --output /tmp/beast-owner-portable-PRIVATE-UNIQUE.zip
```

Retain the resulting manifest and archive hashes privately. The script refuses unsupported/credential-bearing histories rather than silently exporting them. A failed export is a blocker, not a reason to bypass checks.

The owner vault is a separate `owner-connections.sqlite3` containing encrypted provider records. The private host has a configured `BEASTBOX_CONNECTION_VAULT_KEY` environment variable. **Never print that variable or store it alongside the archive.** If the vault file exists, use SQLite's online backup API in the same private shell to create a consistent encrypted-file snapshot without printing its rows:

```sh
python - <<'PY'
from pathlib import Path
import sqlite3
src=Path('/srv/beastbox/data/owner-connections.sqlite3')
dst=Path('/tmp/beast-owner-vault-PRIVATE-UNIQUE.sqlite3')
if not src.is_file() or dst.exists():
    raise SystemExit('Vault missing or destination already exists; stop and investigate')
with sqlite3.connect(f'file:{src}?mode=ro',uri=True) as live:
    with sqlite3.connect(str(dst)) as copy:
        live.backup(copy)
        ok=copy.execute('PRAGMA quick_check').fetchone()[0]
        if ok!='ok':
            raise SystemExit('Vault snapshot integrity check failed')
dst.chmod(0o600)
print('PRIVATE_VAULT_SQLITE_COPY_VERIFIED; no records printed')
PY
```

These examples are two validated **SQLite snapshot methods**, not proof that unrelated volume files and settings are covered. Inventory remaining files and produce a separate private preservation/recovery procedure for required non-database state. The host key and production environment configuration must be retained separately using existing trusted owner account controls, NEVER pasted into chat or a repository.

Immediately transfer the private files via Railway's documented encrypted SSH/SFTP interface to the owner's trusted encrypted machine (copy them into an existing private directory with restrictive permissions):

```sh
scp cosmos-owner-bridge-production.up.railway.app@ssh.railway.com:/tmp/beast-owner-portable-PRIVATE-UNIQUE.zip ./private-owner-archive.zip
scp cosmos-owner-bridge-production.up.railway.app@ssh.railway.com:/tmp/beast-owner-vault-PRIVATE-UNIQUE.sqlite3 ./private-owner-vault.sqlite3
```

Compare the local archive SHA-256 with the **original printed export receipt**. Store both copies away from the live Railway volume in owner-controlled encrypted storage, then remove the temporary container files only after confirmation. If SSH, SCP, storage, data size, or any missing companion state cannot be verified, keep the release blocked. Normal data transfer may count against Railway usage; do not provision new paid resources without explicit approval.

## REQUIRED: capture the OTHER operational databases and configuration

The portable ZIP contains **only** `runtime.sqlite3`. An integrated running Beast also uses `activation.sqlite3` for the durable work queue and hash-linked task audit, `owner-connections.sqlite3` for the encrypted cloud credential vault, and `cosmic-provider.json` for the selected provider profile. Some installations also have a separately sealed working DB, companion evidence or other state. Do not call a portable ZIP alone a complete production recovery.

**Before any file export**, use the actual owner interface's master stop and ensure all existing in-flight owner work is finished or explicitly reconciled. Stop starting owner chats, sensor persistence and new tasks during the capture maintenance window. Multi-file online SQLite backups are individually consistent but NOT automatically atomic across different databases when other processes continue writing. If quiescence cannot be demonstrated, no full-release recovery is established.

In your private existing Railway shell, back up the separate activation queue using the same standard Python SQLite online API (without printing task payloads). This can be executed after the owner vault snapshot above:

```sh
python - <<'PY'
from pathlib import Path
import sqlite3
src=Path('/srv/beastbox/data/activation.sqlite3')
dst=Path('/tmp/beast-owner-activation-PRIVATE-UNIQUE.sqlite3')
if not src.is_file() or src.is_symlink() or dst.exists():
    raise SystemExit('Queue database not available or destination exists; investigate, do not claim success')
with sqlite3.connect(f'file:{src}?mode=ro',uri=True) as live:
    with sqlite3.connect(str(dst)) as copy:
        live.backup(copy)
        if copy.execute('PRAGMA quick_check').fetchone()[0]!='ok':
            raise SystemExit('Queue snapshot integrity check failed')
        n=copy.execute("SELECT COUNT(*) FROM activation_tasks WHERE status='running'").fetchone()[0]
        if n:
            raise SystemExit('In-flight queue records present: reconcile before release')
dst.chmod(0o600)
print('PRIVATE_ACTIVATION_DB_COPY_VERIFIED; no task data printed')
PY
```

On the owner's encrypted machine, fetch this queue copy with Railway's authenticated `scp`, and preserve `cosmic-provider.json` if present using the same private SSH/SFTP route. Record exact SHA-256 hashes of the files privately and compare source to transferred copies. Independently inventory the whole `/srv/beastbox/data` directory **without pasting its contents into chat**, including evidence files and any `runtime.sqlite3.sealed` that exist. Back up and validate every required operational companion; keep host secrets separately in existing owner-controlled secret management, not alongside backups. If a required file is missing or you cannot verify the complete inventory, stop rather than claiming a full backup.

On the isolated restored directory, place the queue snapshot as `activation.sqlite3` after the portable-state import. Verify its `PRAGMA quick_check`, then open `beastbox.activation_queue.ActivationEngine` against the isolated path (with the original production version and matching host mode flags), call `verify_audit()`, inspect `status()` and `tasks()` privately, and close without running queued tasks. Match the separately recorded hashes and selected provider profile. Encrypted vault recovery must separately confirm the preserved host key works without displaying any credentials.

A complete sign-off needs two independent facts: (a) the portable substrate system ID and checkpoint match after isolated restoration, and (b) the queue audit, encrypted vault, provider profile and any other required state can also be independently restored. A verified ZIP by itself does not permit PR #165 to merge.

## Isolated recovery validation on the trusted computer

Use the actual production-source version of Beast Box (the pinned deployment commit above) with supported Python dependencies. Place the private archive outside the repository. Run this ONLY in a private shell; it does not access the production service:

```py
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import runpy
import zipfile

archive=Path('/PRIVATE/PATH/private-owner-archive.zip') # set your private path
api=runpy.run_path('apps/beastbox-cloud/bridge/export_bundle.py')
with zipfile.ZipFile(archive) as z:
    manifest_sha=hashlib.sha256(z.read('manifest.json')).hexdigest()
before=api['verify_archive'](archive,manifest_sha)
with TemporaryDirectory(prefix='isolated-beast-restore-') as temp:
    after=api['restore_archive'](archive,Path(temp)/'recovered',manifest_sha)
    assert before['checkpoint_sha256']==after['checkpoint_sha256']
    assert before['system_id']==after['system_id']
    assert after['restored'] is True
print(json.dumps({'isolated_state_recovery':'VERIFIED',
                  'checkpoint_matches':True,'no_private_rows_printed':True}))
```

Independently verify the copied encrypted vault database with `PRAGMA quick_check` and reconcile the separate host-held key without printing it. Check that the full set of required volume files/environment references has a tested recovery path. A newly created local snapshot that exists ONLY under `/tmp`, or a copied archive without an isolated test, does not meet the production release gate.

**Do not share private archives, keys, paths containing personal information, or raw command output in the PR.** Record only sanitized confirmation: archive off-host; matching SHA-256; isolated checkpoint restore passed; companion vault/settings covered and recoverable; no changes to running production. Confirm these facts before merging PR #165. The assistant cannot infer or forge these results.
