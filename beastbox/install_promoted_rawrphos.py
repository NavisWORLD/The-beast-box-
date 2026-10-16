"""Build-time installer for a PR-reviewed public RAWRPHOS promotion.

Reads apps/beastbox-cloud/lib/rawrphos-public-pin.json. With no promotion it does
nothing (the pinned 14000 stays). With a promotion it downloads the cited public
GitHub release asset, verifies the tarball sha256 from the pin, extracts it, and
verifies model.safetensors against the pinned checkpoint sha256. Never runs on a
chat request; any mismatch fails the build so the previous deployment stays live.
"""
from __future__ import annotations
import hashlib, json, shutil, sys, tarfile, tempfile, urllib.request
from pathlib import Path
from beastbox.rawrphos_local import PIN_PATH, STEP, SHA, BASE_STEP

REPO = "NavisWORLD/The-beast-box-"

def main(dest: str) -> int:
    pin = json.loads(PIN_PATH.read_text())
    promo = pin.get("promotion")
    if promo is None or STEP == BASE_STEP:
        print("RAWRPHOS_PUBLIC_PIN=14000 (no promotion)")
        return 0
    tag = promo["release_tag"]; asset_sha = promo["release_asset_sha256"]
    url = f"https://github.com/{REPO}/releases/download/{tag}/{tag}.tar.gz"
    with tempfile.TemporaryDirectory() as tmp:
        tarpath = Path(tmp) / "c.tar.gz"
        with urllib.request.urlopen(url, timeout=120) as r, open(tarpath, "wb") as f:
            shutil.copyfileobj(r, f)
        if hashlib.sha256(tarpath.read_bytes()).hexdigest() != asset_sha:
            raise SystemExit("promoted release asset sha256 mismatch")
        with tarfile.open(tarpath) as t:
            t.extractall(tmp, filter="data")
        ck = Path(tmp) / "accepted-checkpoint"
        if hashlib.sha256((ck / "model.safetensors").read_bytes()).hexdigest() != SHA:
            raise SystemExit("promoted checkpoint sha256 mismatch")
        meta = json.loads((ck / "metadata.json").read_text())
        if meta.get("training_steps") != STEP or meta.get("checkpoint_sha256") != SHA:
            raise SystemExit("promoted checkpoint metadata mismatch")
        out = Path(dest)
        if out.exists(): shutil.rmtree(out)
        shutil.copytree(ck, out)
    print(f"RAWRPHOS_PUBLIC_PIN={STEP} {SHA}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
