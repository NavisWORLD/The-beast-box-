"""Verify continuity survives an abrupt OS process exit and SQLite-safe backup."""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

def invoke(source: str, root: Path) -> dict:
    done = subprocess.run([sys.executable, "-c", source, str(root)],
        capture_output=True, text=True, timeout=35, check=True)
    return json.loads(done.stdout.strip())

def test_abrupt_process_restart_and_clean_backup_restore(tmp_path):
    root = tmp_path / "original"
    writer = """
import hashlib, json, os, sys
from pathlib import Path
from beastbox.durable import DurableRuntime
from beastbox.providers import ReferenceTextProvider
service = DurableRuntime(Path(sys.argv[1]), ReferenceTextProvider())
text = "Synthetic cobalt notebook: no owner information."
identifier = service.store_external_memory(text)["memory_id"]
service.archive_memory(identifier, reviewer="fixture-operator", reason="restart test")
state = service.inspect()
assert not service.memory.search("cobalt notebook")
payload = {key: state[key] for key in ("system_id","sequence","checkpoint_sha256","memory_digest","state_sha256")}
payload["identifier"] = identifier
payload["text_sha256"] = hashlib.sha256(text.encode()).hexdigest()
print(json.dumps(payload), flush=True)
os._exit(0)  # No runtime.close(): simulate a power/process crash after durable commit.
"""
    reader = """
import hashlib, json, sys
from pathlib import Path
from beastbox.durable import DurableRuntime
from beastbox.providers import ReferenceTextProvider
from beastbox.cosmic_web import CosmicApp
root = Path(sys.argv[1])
service = DurableRuntime(root, ReferenceTextProvider())
state = service.inspect()
assert not service.memory.search("cobalt notebook")
row = service.memory.db.execute("SELECT id,text,metadata_json FROM memories WHERE text LIKE ?",
                               ("%Synthetic cobalt notebook%",)).fetchone()
assert row and json.loads(row["metadata_json"])["archived"] is True
payload = {key: state[key] for key in ("system_id","sequence","checkpoint_sha256","memory_digest","state_sha256")}
payload["identifier"] = row["id"]
payload["text_sha256"] = hashlib.sha256(row["text"].encode()).hexdigest()
service.close()
assert CosmicApp(root).authority.allowed("cloud") is False
print(json.dumps(payload), flush=True)
"""
    original = invoke(writer, root)
    resumed = invoke(reader, root)
    assert resumed == original
    backup = tmp_path / "restored"
    backup.mkdir()
    source = sqlite3.connect(root / "runtime.sqlite3")
    destination = sqlite3.connect(backup / "runtime.sqlite3")
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    restored = invoke(reader, backup)
    assert restored == original
