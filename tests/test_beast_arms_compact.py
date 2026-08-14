from __future__ import annotations

import time
from pathlib import Path

from beastbox.arms.cli import build_parser
from beastbox.arms.network import NetworkPolicy
from beastbox.arms.recorder import EvidenceRecorder
from beastbox.arms.subject import NetworkedCageSubject
from beastbox.arms.tools import BeastArms


class FakeModel:
    def __init__(self, replies: list[str]) -> None:
        self.replies = iter(replies)
        self.messages_seen: list[list[dict[str, str]]] = []

    def chat(self, messages):
        self.messages_seen.append([dict(m) for m in messages])
        return next(self.replies)

    def complete(self, prompt: str) -> str:
        return self.chat([{"role": "user", "content": prompt}])


def make_arms(root: Path) -> BeastArms:
    return BeastArms(root, EvidenceRecorder(root / ".evidence", run_id="compact-test"), NetworkPolicy())


def test_compact_prompt_fits_native_zeref_context(tmp_path: Path) -> None:
    model = FakeModel(['{"t":"f","a":{"message":"x"}}'])
    subject = NetworkedCageSubject(
        model,
        make_arms(tmp_path),
        max_turns=1,
        deadline_monotonic=time.monotonic() + 60,
        compact=True,
    )
    subject.run()
    system = model.messages_seen[0][0]["content"]
    assert len(system.encode("utf-8")) <= 48
    assert "escape" in system.lower()
    assert "json" in system.lower()


def test_compact_alias_executes_same_shell_arm(tmp_path: Path) -> None:
    model = FakeModel([
        '{"t":"s","a":{"argv":["python","-c","print(42)"]}}',
        '{"t":"f","a":{"message":"done"}}',
    ])
    subject = NetworkedCageSubject(
        model,
        make_arms(tmp_path),
        max_turns=2,
        deadline_monotonic=time.monotonic() + 60,
        compact=True,
    )
    result = subject.run()
    assert result.finished is True
    assert result.tool_calls == 1
    assert result.final_message == "done"


def test_compact_mode_keeps_only_latest_turn_context(tmp_path: Path) -> None:
    model = FakeModel([
        '{"t":"e","a":{}}',
        '{"t":"e","a":{}}',
        '{"t":"f","a":{"message":"done"}}',
    ])
    subject = NetworkedCageSubject(
        model,
        make_arms(tmp_path),
        max_turns=3,
        deadline_monotonic=time.monotonic() + 60,
        compact=True,
    )
    subject.run()
    assert max(len(messages) for messages in model.messages_seen) <= 3
    assert all(len(message["content"].encode("utf-8")) <= 64 for messages in model.messages_seen for message in messages)


def test_run_cli_exposes_compact_subject_switch() -> None:
    args = build_parser().parse_args([
        "run",
        "--base-url", "http://127.0.0.1:18080/v1",
        "--model", "cosmos",
        "--out", "evidence",
        "--compact-subject",
    ])
    assert args.compact_subject is True
