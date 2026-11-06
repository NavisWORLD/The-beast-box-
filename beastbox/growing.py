"""Growing Zeref serving (step 6 of Cory's 2026-10-31 plan): a SEPARATE route, labelled "Growing Zeref · not the pin".

* A supervisor (python -m beastbox.growing) runs beside the pin. It downloads the newest public release
  zeref-growing-NNN, verifies its sha256 and checkpoint manifest, and serves it with the same native
  inference server on private loopback port 8769. Every REFRESH_S it looks again and swaps in a newer one.
* It never reads or writes the pin, never shares the pin's port, and its failure never stops the bridge.
* growing_infer() is the bridge door /api/guest-growing: same bounded {text, guest_identity} contract and
  quota as the guest door; replies carry the growing tag, step and sha so nobody mistakes it for the pin.
"""
from __future__ import annotations
import hashlib, json, os, re, shutil, subprocess, sys, tarfile, time, urllib.error, urllib.request
from pathlib import Path

LABEL = "Growing Zeref · not the pin"
SCHEMA = "beastbox-guest-growing-v1"
PORT = 8769
REPO = os.environ.get("BEASTBOX_GROWING_REPO", "NavisWORLD/The-beast-box-")
ROOT = Path(os.environ.get("BEASTBOX_GROWING_DIR", "/opt/beastbox/rawrphos/growing"))
STATE = ROOT / "current.json"
REFRESH_S = int(os.environ.get("BEASTBOX_GROWING_REFRESH_S", "14400"))
MAX_TAR = 300 * 1024 * 1024
TAG = re.compile(r"zeref-growing-(\d{3,})\Z")
MAX_PROMPT, MAX_OUTPUT_TOKENS = 1800, 64
_GUEST_ID = re.compile(r"[a-f0-9]{64}\Z")
UA = {"User-Agent": "beastbox-growing/1", "Accept": "application/vnd.github+json"}

def newest_tag(releases: list) -> str | None:
    tags = [(int(m.group(1)), r["tag_name"]) for r in releases if isinstance(r, dict)
            and (m := TAG.fullmatch(str(r.get("tag_name", "")))) and not r.get("draft")]
    return max(tags)[1] if tags else None

def _get(url: str, limit: int) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        data = r.read(limit + 1)
    if len(data) > limit: raise ValueError("download too large")
    return data

def fetch(tag: str, dest_root: Path = ROOT) -> dict:
    rel = json.loads(_get(f"https://api.github.com/repos/{REPO}/releases/tags/{tag}", 2_000_000))
    assets = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
    tar_name = f"{tag}.tar.gz"
    blob = _get(assets[tar_name], MAX_TAR)
    want = _get(assets[tar_name + ".sha256"], 4096).decode().split()[0]
    if hashlib.sha256(blob).hexdigest() != want: raise ValueError("growing release sha mismatch")
    report = json.loads(_get(assets["report.json"], 2_000_000))
    out = dest_root / tag
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    tmp = out / tar_name; tmp.write_bytes(blob)
    with tarfile.open(tmp) as t:
        for m in t.getmembers():
            if m.name.startswith("/") or ".." in Path(m.name).parts or not (m.isfile() or m.isdir()):
                raise ValueError("unsafe archive member")
        t.extractall(out)
    tmp.unlink()
    ckpt = out / "accepted-checkpoint"
    meta = json.loads((ckpt / "metadata.json").read_text())
    if meta.get("branch") != "growing" or meta.get("is_public_pin") is not False:
        raise ValueError("not a growing-branch checkpoint")
    if meta["checkpoint_sha256"] != report["checkpoint_sha256"]: raise ValueError("report/metadata mismatch")
    return {"tag": tag, "path": str(ckpt), "checkpoint_sha256": meta["checkpoint_sha256"],
            "step": int(meta.get("training_steps") or 0), "label": LABEL}

def current() -> dict | None:
    try: return json.loads(STATE.read_text())
    except (OSError, ValueError): return None

def _serve(info: dict):
    env = dict(os.environ, PORT=str(PORT), HOST="127.0.0.1")
    cmd = [sys.executable, "-m", "rawrphos.inference.server", "--checkpoint", info["path"], "--port", str(PORT),
           "--expected-sha256", info["checkpoint_sha256"]]
    return subprocess.Popen(cmd, env=env)

def supervise():  # pragma: no cover - long-running process, exercised on the bridge
    ROOT.mkdir(parents=True, exist_ok=True); proc, live = None, None
    while True:
        try:
            tag = newest_tag(json.loads(_get(f"https://api.github.com/repos/{REPO}/releases?per_page=100", 5_000_000)))
            if tag and (live is None or tag != live["tag"] or proc is None or proc.poll() is not None):
                info = fetch(tag)
                new = _serve(info)
                if proc is not None and proc.poll() is None: proc.terminate()
                proc, old = new, live; live = info
                STATE.write_text(json.dumps(info, sort_keys=True))
                if old and old["tag"] != tag: shutil.rmtree(ROOT / old["tag"], ignore_errors=True)  # local copy only; the release stays
                print("GROWING_ZEREF_SERVING", tag, info["step"], info["checkpoint_sha256"], flush=True)
        except Exception as e:  # never fatal: the pin and bridge keep running without the growing route
            print("GROWING_ZEREF_REFRESH_SKIPPED", type(e).__name__, flush=True)
        time.sleep(REFRESH_S if live else 600)

def _spark_pulse() -> dict | None:
    try:
        from .spark_pulse import spark_pulse
        return spark_pulse()
    except Exception:
        return None  # ABSENT, never a 0.5 stand-in

def growing_infer(root: Path, payload: dict) -> tuple[int, dict]:
    if os.environ.get("BEASTBOX_GROWING_ENABLED", "no") != "yes":
        return 503, {"error": "Growing Zeref route is off"}
    if (not isinstance(payload, dict) or set(payload) != {"text", "guest_identity"}
            or not isinstance(payload.get("guest_identity"), str) or not _GUEST_ID.fullmatch(payload["guest_identity"])
            or not isinstance(payload.get("text"), str) or not 1 <= len(payload["text"].strip()) <= MAX_PROMPT
            or any(ord(c) < 32 and c not in "\n\t" for c in payload["text"])):
        return 400, {"error": "Invalid bounded guest request"}
    info = current()
    if not info: return 503, {"error": "Growing Zeref has no checkpoint yet"}
    from .guest_local import GuestQuota
    from .providers import _local_opener
    quota = GuestQuota(root); code, token, message = quota.reserve(payload["guest_identity"])
    if code != 200: return code, {"error": message}
    try:
        key = os.environ.get("RAWRPHOS_API_KEY", "")
        if len(key) < 32: return 503, {"error": "Local model key unavailable"}
        body = json.dumps({"model": "rawrphos-native", "messages": [{"role": "user", "content": payload["text"].strip()}],
                           "max_tokens": MAX_OUTPUT_TOKENS, "temperature": 0.3, "stream": False}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", data=body, method="POST",
                                     headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        with _local_opener().open(req, timeout=45) as r:
            raw = r.read(16001)
        if len(raw) > 16000: return 502, {"error": "Native response too large"}
        result = json.loads(raw)
        if result.get("model") != "rawrphos-native" or result.get("checkpoint_sha256") != info["checkpoint_sha256"]:
            return 502, {"error": "Growing model identity check failed"}
        text = result["choices"][0]["message"]["content"]
        if not isinstance(text, str) or not text.strip() or len(text) > 6000:
            return 502, {"error": "Native response was empty or invalid"}
        return 200, {"schema": SCHEMA, "label": LABEL, "model": "rawrphos-native", "tag": info["tag"], "step": info["step"],
                     "checkpoint_sha256": info["checkpoint_sha256"], "reply": text, "is_public_pin": False, "gated": False,
                     "memory_used": False, "owner_tools_used": False, "provider_key_shared": False,
                     "hebbian": result.get("hebbian") is True,
                     # One more sensorium input: the RECORDED origin spark pulse at this moment (None = ABSENT).
                     "sensorium": {"spark_pulse": _spark_pulse()}}
    except (OSError, ValueError, TypeError, KeyError, IndexError, urllib.error.HTTPError):
        return 502, {"error": "Growing Zeref unavailable; no fallback"}
    finally:
        quota.release(token)

if __name__ == "__main__":  # pragma: no cover
    supervise()
