from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from beastbox.cypher.agent import CoderAgent
from beastbox.cypher.gguf import inspect_gguf
from beastbox.cypher.models import ModelSpec, assert_loopback
from beastbox.cypher.registry import ModelRegistry
from beastbox.cypher.workspace import Workspace


class FakeModel:
    def __init__(self, replies): self.replies = iter(replies)
    def chat(self, messages): return next(self.replies)
    def complete(self, prompt): return self.chat([{"role": "user", "content": prompt}])


def test_registry_roundtrip(tmp_path: Path):
    reg = ModelRegistry(tmp_path / "models.json"); spec = ModelSpec(alias="test", backend="ollama", model="qwen:latest"); reg.register(spec); assert reg.get("test").model == "qwen:latest"; assert reg.remove("test") is True


def test_loopback_restriction():
    assert_loopback("http://127.0.0.1:11434"); assert_loopback("http://localhost:8080/v1")
    with pytest.raises(ValueError): assert_loopback("https://example.com/v1")


def test_workspace_blocks_escape_and_dry_run_agent(tmp_path: Path):
    (tmp_path / "hello.py").write_text("print('old')\n", encoding="utf-8"); ws = Workspace(tmp_path)
    with pytest.raises(ValueError): ws.resolve("../escape")
    model = FakeModel([json.dumps({"action": "read", "path": "hello.py"}), json.dumps({"action": "write", "path": "hello.py", "content": "print('new')\n"}), json.dumps({"action": "finish", "message": "done"})])
    result = CoderAgent(model, ws, apply=False, max_steps=4).run("change greeting"); assert result.final == "done"; assert (tmp_path / "hello.py").read_text(encoding="utf-8") == "print('old')\n"; assert "hello.py" in result.changed_paths


def test_workspace_apply_creates_backup(tmp_path: Path):
    (tmp_path / "hello.py").write_text("old\n", encoding="utf-8"); ws = Workspace(tmp_path); out = ws.write("hello.py", "new\n"); assert (tmp_path / "hello.py").read_text(encoding="utf-8") == "new\n"; assert out["backup"]; assert (tmp_path / str(out["backup"])).read_text(encoding="utf-8") == "old\n"


def _gguf_string(value: str) -> bytes:
    raw = value.encode("utf-8"); return struct.pack("<Q", len(raw)) + raw


def test_minimal_gguf_metadata(tmp_path: Path):
    blob = bytearray(b"GGUF"); blob += struct.pack("<IQQ", 3, 0, 2); blob += _gguf_string("general.architecture") + struct.pack("<I", 8) + _gguf_string("llama"); blob += _gguf_string("llama.context_length") + struct.pack("<I", 4) + struct.pack("<I", 4096); path = tmp_path / "tiny.gguf"; path.write_bytes(blob); info = inspect_gguf(path); assert info["architecture"] == "llama"; assert info["context_length"] == 4096
