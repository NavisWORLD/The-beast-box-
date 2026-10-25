"""Contract for the chained diary keep-alive: it only dispatches the existing diary loop; it writes nothing and holds no secrets."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / ".github/workflows/zeref-diary-keepalive.yml").read_text()
WF = yaml.safe_load(TEXT)
ON = WF.get("on") or WF[True]


def test_chained_with_concurrency_and_an_hourly_cron_watchdog():
    assert WF["concurrency"] == {"group": "zeref-diary-keepalive", "cancel-in-progress": False}
    assert ON["schedule"] == [{"cron": "41 * * * *"}] and "workflow_dispatch" in ON
    assert "gh workflow run zeref-diary-keepalive.yml" in TEXT  # queues its own successor at the start
    assert WF["jobs"]["keepalive"]["timeout-minutes"] == 345


def test_only_dispatches_the_existing_diary_loop_and_never_writes_data_or_uses_secrets():
    assert WF["permissions"] == {"actions": "write", "contents": "read"}
    assert "secrets." not in TEXT and "git push" not in TEXT and "git commit" not in TEXT
    assert "gh workflow run zeref-diary-loop.yml" in TEXT and "-gt 2400" in TEXT
    for other in ("zeref-continuous-learning-006", "zeref-spark-loop.yml", "zeref-live-tick-loop.yml"):
        assert f"gh workflow run {other}" not in TEXT
