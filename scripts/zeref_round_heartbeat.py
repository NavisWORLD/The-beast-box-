#!/usr/bin/env python3
"""Round heartbeat (DIAGNOSTIC, report-only, never a gate input).

Added 2026-11-18 (Emeth, under Cory's engine/gate fix delegation) after a run
of 006 rounds died with the runner vanishing ~45 minutes into the training
step: a dead runner never uploads its step log, so each failure left no
evidence of where training was or what the machine looked like. The training
step now runs the trainer in the background and calls this once a minute; it
samples the trainer's RSS, free memory and disk, and the tail of the trainer's
own printed progress, and pushes one small JSON to the zeref-round-heartbeat
branch, which survives the runner. Remove once the kill mechanism is known.
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

LOG = "build/zeref-006/trainer.log"
OUT = "build/zeref-006/heartbeat.json"
BRANCH = "zeref-round-heartbeat"


def trainer_rss_mb():
    try:
        out = subprocess.run(["pgrep", "-f", "zeref_continuation_006.py"],
                             capture_output=True, text=True, timeout=5).stdout.split()
        if not out:
            return None
        total = 0
        for pid in out:
            with open(f"/proc/{pid}/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        total += int(line.split()[1])
        return total // 1024
    except Exception:
        return None


def mem_available_mb():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return None


def last_progress():
    batch = None
    lines = []
    size = 0
    try:
        with open(LOG, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 262144))
            text = f.read().decode("utf-8", "replace")
        for line in text.splitlines():
            if "ZEREF_" in line:
                lines.append(line[:300])
                if "ZEREF_006_BATCH=" in line:
                    try:
                        batch = json.loads(line.split("ZEREF_006_BATCH=", 1)[1])
                    except Exception:
                        pass
        return batch, lines[-3:], size
    except Exception:
        return None, [], 0


def main():
    batch, lines, log_bytes = last_progress()
    hb = {
        "schema": "zeref-round-heartbeat-v1",
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "ts": time.time(),
        "trainer_rss_mb": trainer_rss_mb(),
        "mem_available_mb": mem_available_mb(),
        "disk_free_mb": None,
        "log_bytes": log_bytes,
        "last_batch": batch,
        "last_lines": lines,
    }
    try:
        hb["disk_free_mb"] = shutil.disk_usage(".").free // (1024 * 1024)
    except Exception:
        pass
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w") as f:
            json.dump(hb, f, indent=1, sort_keys=True)
    except Exception:
        pass
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        return 0
    api = f"https://api.github.com/repos/{repo}/contents/heartbeat.json"
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    try:
        sha = None
        req = urllib.request.Request(api + f"?ref={BRANCH}", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                sha = json.load(r).get("sha")
        except Exception:
            sha = None
        payload = {"message": f"heartbeat run {hb['run_id']}", "branch": BRANCH,
                   "content": base64.b64encode(
                       json.dumps(hb, indent=1, sort_keys=True).encode()).decode()}
        if sha:
            payload["sha"] = sha
        req = urllib.request.Request(api, data=json.dumps(payload).encode(),
                                     headers=headers, method="PUT")
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
