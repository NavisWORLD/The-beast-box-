from __future__ import annotations

import os
import signal
from pathlib import Path

import beastbox.arms.cli as arms_cli


class FakeLauncher:
    def __init__(self) -> None:
        self.pid = 424242
        self.wait_calls: list[int] = []
        self.kill_called = False
        self.terminate_called = False

    def poll(self):
        return None

    def terminate(self) -> None:
        self.terminate_called = True

    def kill(self) -> None:
        self.kill_called = True

    def wait(self, timeout: int):
        self.wait_calls.append(timeout)
        return 0


def test_terminate_launcher_signals_process_group_so_cleanup_trap_can_run(monkeypatch) -> None:
    launcher = FakeLauncher()
    calls: list[tuple[int, int]] = []

    def fake_killpg(pid: int, sig: int) -> None:
        calls.append((pid, sig))

    monkeypatch.setattr(os, "killpg", fake_killpg)

    arms_cli._terminate_launcher(launcher)  # type: ignore[arg-type]

    assert calls == [(launcher.pid, signal.SIGTERM)]
    assert launcher.terminate_called is False
    assert launcher.kill_called is False
    assert launcher.wait_calls == [30]


def test_host_reclaims_workspace_after_cage_shutdown(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(argv, *, check):
        calls.append(list(argv))
        assert check is True

    monkeypatch.setattr(arms_cli.subprocess, "run", fake_run)
    work = tmp_path / "workspace"
    work.mkdir()

    arms_cli._restore_workspace_access(work)

    owner = f"{os.getuid()}:{os.getgid()}"
    assert ["sudo", "chown", "-R", owner, str(work)] in calls
    assert ["sudo", "chmod", "700", str(work)] in calls
