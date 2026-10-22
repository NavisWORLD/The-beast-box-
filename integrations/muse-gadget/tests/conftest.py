import json
import shutil
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT))

from beastbox_musegadget.config import Config  # noqa: E402


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def snapshot(tmp_path) -> Path:
    target = tmp_path / "snapshot.json"
    shutil.copy(FIXTURES / "beast_snapshot.json", target)
    return target


@pytest.fixture
def cfg(tmp_path, snapshot) -> Config:
    dead = free_port()
    return Config(snapshot=str(snapshot), state_dir=str(tmp_path / "state"),
                  ollama_host=f"http://127.0.0.1:{dead}", bridge_url=f"http://127.0.0.1:{dead}")


@pytest.fixture
def fixture_session() -> dict:
    return json.loads((FIXTURES / "beast_snapshot.json").read_text())
