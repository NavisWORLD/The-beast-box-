"""Zeref's live Rigetti SIMULATED spark as a routing source for the quantum band.

Reads the `latest.json` written by scripts/zeref_spark_loop.py (data-only `zeref-spark` branch, loop
.github/workflows/zeref-spark-loop.yml). Only the last successful simulator counts are used; a tick that
failed does not hide the age of the last good counts (the quantum band goes stale on the routing window
rather than being refreshed with invented numbers). Always labeled SIMULATED.
"""
from __future__ import annotations

import json
import time
import urllib.request
from typing import Any, Mapping

from .routing import QVM_TARGET, rigetti_source

SPARK_URL = "https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/zeref-spark/zeref/latest.json"
BEAST_ID = "bb-deada969"


def spark_source(latest: Mapping[str, Any] | None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """(routing source or None, status). Status always says what the loop is doing, including late/failed."""
    if not isinstance(latest, Mapping) or latest.get("beast_id") != BEAST_ID or latest.get("simulated") is not True:
        return None, {"state": "missing", "reason": "no Zeref spark record"}
    good = latest.get("last_ok")
    status = {"state": "ok" if latest.get("status") == "ok" else "failed", "tick": latest.get("tick"),
              "late": bool(latest.get("late")), "late_by_s": latest.get("late_by_s"),
              "consecutive_failures": latest.get("consecutive_failures"), "label": latest.get("label"),
              "interval_target_s": latest.get("interval_target_s")}
    if not isinstance(good, Mapping):
        return None, {**status, "state": "missing", "reason": "no successful simulator tick yet"}
    record = {"target": latest.get("target", QVM_TARGET), "counts": good.get("counts"), "shots": good.get("shots"),
              "job_id": good.get("job_id")}
    src = rigetti_source(record, float(good["at_epoch"]))
    src["provenance"].update(tick=good.get("tick"), beast_id=BEAST_ID, continues_from=latest.get("continues_from"))
    return src, {**status, "last_ok_tick": good.get("tick")}


def fetch_latest(url: str = SPARK_URL, timeout: float = 4.0) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 (fixed https URL)
            return json.loads(resp.read(200_000))
    except (OSError, ValueError):
        return None


def age_seconds(latest: Mapping[str, Any] | None, now: float | None = None) -> float | None:
    if not isinstance(latest, Mapping) or not isinstance(latest.get("at_epoch"), (int, float)):
        return None
    return round((time.time() if now is None else now) - float(latest["at_epoch"]), 1)


TICKS_URL = "https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/zeref-spark/zeref/ticks.jsonl"


def load_ticks(path_or_url: str, limit: int = 400) -> list[dict[str, Any]]:
    """Last `limit` successful spark ticks (file path or https URL). Failed ticks are skipped, never filled in."""
    try:
        if path_or_url.startswith("https://"):
            with urllib.request.urlopen(path_or_url, timeout=20) as resp:  # noqa: S310 (fixed https URL)
                raw = resp.read(40_000_000).decode("utf-8", "replace")
        else:
            with open(path_or_url, encoding="utf-8") as fh:
                raw = fh.read()
    except OSError:
        return []
    out = []
    for line in raw.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("beast_id") == BEAST_ID and row.get("simulated") is True \
                and row.get("status") == "ok" and isinstance(row.get("growth_source"), dict):
            out.append(row)
    return out[-limit:]


def tick_condition54(row: Mapping[str, Any]) -> dict[str, Any]:
    """Route ONE recorded spark tick (SIMULATED) into the 54 numbers (D1-D12 + the 42 band slots).
    Only the quantum band (and the D-slots it feeds) is live; every other slot is masked to exactly 0.0,
    and the receipt says so. Returns {cond54, tally, receipt_sha256}."""
    from .routing import route
    g = row["growth_source"]
    record = {"target": g.get("target", QVM_TARGET), "counts": g.get("counts"), "shots": g.get("shots"),
              "job_id": g.get("job_id")}
    at = float(row["at_epoch"])
    routed = route({"quantum_rigetti": rigetti_source(record, at)}, now=at + 1.0)
    return {"cond54": [float(v) for v in routed["d12"] + routed["d42"]], "tally": routed["tally"],
            "receipt_sha256": routed["receipt_sha256"], "tick": row.get("tick")}
