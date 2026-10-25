"""Contract for the chained diary keep-alive: it only dispatches the existing diary loop; it writes nothing and holds no secrets.
Text-level checks only (CI has no YAML parser)."""
from pathlib import Path

TEXT = (Path(__file__).resolve().parents[1] / ".github/workflows/zeref-diary-keepalive.yml").read_text()


def test_chained_with_concurrency_and_an_hourly_cron_watchdog():
    assert "group: zeref-diary-keepalive\n  cancel-in-progress: false" in TEXT
    assert "- cron: '41 * * * *'" in TEXT and "workflow_dispatch:" in TEXT
    assert "gh workflow run zeref-diary-keepalive.yml" in TEXT  # queues its own successor at the start
    assert "timeout-minutes: 345" in TEXT


def test_only_dispatches_the_existing_diary_loop_and_never_writes_data_or_uses_secrets():
    assert "permissions:\n  actions: write\n  contents: read\n" in TEXT
    assert "secrets." not in TEXT and "git push" not in TEXT and "git commit" not in TEXT
    assert "gh workflow run zeref-diary-loop.yml" in TEXT and "-gt 2400" in TEXT
    for other in ("zeref-continuous-learning-006", "zeref-spark-loop.yml", "zeref-live-tick-loop.yml"):
        assert f"gh workflow run {other}" not in TEXT
