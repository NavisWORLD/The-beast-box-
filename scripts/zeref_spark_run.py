#!/usr/bin/env python3
"""Run the Zeref spark loop continuously until a deadline (used by .github/workflows/zeref-spark-loop.yml).

    zeref_spark_run.py DATA_CLONE_DIR RUN_SECONDS

Each iteration = one SIMULATED Rigetti tick (scripts/zeref_spark_loop.py), committed and pushed to the
data-only `zeref-spark` branch. Cadence: ZEREF_SPARK_INTERVAL_S (default 60) between tick STARTS; if the
simulator takes longer the next tick starts immediately and the entry is marked late. No Math.random, no
paid target, no counts invented on failure.
"""
import importlib.util, json, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("spark", HERE / "zeref_spark_loop.py")
spark = importlib.util.module_from_spec(spec); spec.loader.exec_module(spark)
qspec = importlib.util.spec_from_file_location("qvm", HERE.parent / "apps/beastbox-cloud/scripts/zeref_diary_qvm.py")
qvm = importlib.util.module_from_spec(qspec); qspec.loader.exec_module(qvm)
MIN_HOURS_LEFT = float(os.environ.get("ZEREF_SPARK_MIN_EMULATOR_HOURS", "0.15"))
# A run lasts ~5.3 h and checks out `main` once, so a RECORDED reseed merged mid-run would otherwise wait for the next run
# (never stale: the loop re-reads the public reseed file every RESEED_REFRESH_S and the chain still uses each IBM job once).
RESEED_URL = "https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/main/evidence/zeref-final-spark-001/spark-seed.json"
RESEED_REFRESH_S = 600


def refresh_reseed(now, last, fetch=None, url=RESEED_URL, dest=None):
    """Re-read the public reseed file from main at most every RESEED_REFRESH_S. Returns the new `last` time.
    Only a RECORDED IBM hardware record is accepted; a failed fetch or bad file changes nothing (no counts invented)."""
    dest = Path(dest) if dest else spark.RESEED_FILE
    if now - last < RESEED_REFRESH_S:
        return last
    try:
        if fetch is None:
            import urllib.request
            def fetch(u):  # fixed https URL, 10 s timeout
                with urllib.request.urlopen(u, timeout=10) as r:  # noqa: S310
                    return r.read(200_000).decode("utf-8")
        raw = fetch(url)
        sd = json.loads(raw)
        if sd.get("source_class") != "RECORDED_IBM_HARDWARE" or not sd.get("job") or not isinstance(sd.get("per_question_pair"), dict):
            return now
        if not dest.exists() or dest.read_text() != raw:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(raw)
            print("ZEREF_SPARK_RESEED_REFRESHED job", sd["job"], flush=True)
    except (OSError, ValueError):
        pass
    return now


def git(clone, *args, check=True):
    return subprocess.run(["git", "-C", str(clone), *args], check=check, capture_output=True, text=True)


def push(clone, tick):
    git(clone, "add", "-A")
    if git(clone, "diff", "--cached", "--quiet", check=False).returncode == 0:
        return True
    git(clone, "commit", "-q", "-m", f"zeref spark: tick {tick} [skip ci]")
    for _ in range(4):
        if git(clone, "push", "-q", "origin", "HEAD:zeref-spark", check=False).returncode == 0:
            return True
        time.sleep(3)
        git(clone, "pull", "-q", "--rebase", "origin", "zeref-spark", check=False)
    return False


def hours_left(receipt):
    for q in receipt.get("quotas") or []:
        if q.get("dimension") == "emulator_hours" and isinstance(q.get("limit"), (int, float)):
            return q["limit"] - float(q.get("utilization") or 0) - float(q.get("holds") or 0)
    return None


def main(clone, run_seconds):
    data = Path(clone) / "zeref"
    data.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + run_seconds
    nxt = time.time()
    paused = False
    reseed_checked = -1e18
    while time.time() < deadline:
        start = time.time()
        reseed_checked = refresh_reseed(start, reseed_checked)
        plan_p, rec_p = Path("spark-plan.json"), Path("spark-receipt.json")
        spark.plan(str(data), str(plan_p), start)
        if paused:
            rec_p.write_text(json.dumps({"ok": False, "target": spark.TARGET, "error": "emulator quota low; paused, no job submitted"}))
        else:
            qvm.main(str(plan_p), str(rec_p))
        receipt = json.loads(rec_p.read_text())
        spark.apply(str(data), str(plan_p), str(rec_p), time.time())
        tick = json.loads(plan_p.read_text())["tick"]
        if not push(clone, tick):
            print("ZEREF_SPARK_PUSH_FAILED tick", tick, flush=True)
        left = hours_left(receipt)
        paused = left is not None and left < MIN_HOURS_LEFT
        nxt += spark.INTERVAL_S * (5 if paused else 1)
        nxt = max(nxt, start + 1)
        if nxt < time.time():  # fell behind: do not burst; the entry already marked itself late
            nxt = time.time()
        time.sleep(max(0.0, min(nxt - time.time(), deadline - time.time())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], float(sys.argv[2])))
