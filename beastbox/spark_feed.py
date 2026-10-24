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
