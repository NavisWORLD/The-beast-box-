#!/usr/bin/env python3
"""Fallback for `ollama pull` when Ollama's own redirect guard refuses the blob CDN.

Some sandboxes/proxies use fake-IP DNS (198.18.0.0/15). Ollama >= 0.3x then rejects the
registry's redirect to Cloudflare R2 with "redirect target not allowed ... non-public".
This script fetches the SAME public manifest + blobs from registry.ollama.ai with curl,
verifies every blob's SHA-256 against the manifest digest, and lays them out exactly like
`ollama pull` does under $OLLAMA_MODELS (blobs/sha256-<hex>, manifests/registry.ollama.ai/...).
Usage: ollama_registry_pull.py MODELS_DIR name:tag [name:tag ...]
"""
import hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path

REG = "https://registry.ollama.ai"
ACCEPT = "application/vnd.docker.distribution.manifest.v2+json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pull(models: Path, ref: str) -> None:
    name, _, tag = ref.partition(":")
    tag = tag or "latest"
    repo = name if "/" in name else f"library/{name}"
    raw = subprocess.run(["curl", "-fsSL", "--retry", "3", "-H", f"Accept: {ACCEPT}",
                          f"{REG}/v2/{repo}/manifests/{tag}"], check=True, capture_output=True).stdout
    manifest = json.loads(raw)
    blobs = models / "blobs"; blobs.mkdir(parents=True, exist_ok=True)
    for layer in [manifest["config"], *manifest["layers"]]:
        digest = layer["digest"]; hexd = digest.split(":", 1)[1]
        target = blobs / f"sha256-{hexd}"
        if target.exists() and target.stat().st_size == layer["size"] and sha256(target) == hexd:
            print(f"  ok (cached) {digest[:19]} {layer['size']:>12,d} B"); continue
        part = target.with_suffix(".partial")
        print(f"  fetching    {digest[:19]} {layer['size']:>12,d} B", flush=True)
        subprocess.run(["curl", "-fSL", "--retry", "5", "-C", "-", "-s", "-o", str(part),
                        f"{REG}/v2/{repo}/blobs/{digest}"], check=True)
        got = sha256(part)
        if got != hexd:
            part.unlink(missing_ok=True)
            raise SystemExit(f"SHA-256 mismatch for {digest}: got {got}")
        os.replace(part, target)
    mdir = models / "manifests" / "registry.ollama.ai" / repo
    mdir.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=mdir)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    os.replace(tmp, mdir / tag)
    print(f"{ref}: installed, all {1 + len(manifest['layers'])} blobs SHA-256 verified")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    root = Path(sys.argv[1])
    for ref in sys.argv[2:]:
        pull(root, ref)
