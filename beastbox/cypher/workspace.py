from __future__ import annotations

import difflib
import json
import os
import shlex
import shutil
import subprocess
import time
import uuid
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable

_DEFAULT_IGNORES = {".git", ".venv", "venv", "node_modules", ".cosmic-cypher", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "target"}
_BINARY_SUFFIXES = {".gguf", ".bin", ".pt", ".pth", ".safetensors", ".onnx", ".sqlite", ".sqlite3", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".tar", ".gz", ".7z"}


class Workspace:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.exists() or not self.root.is_dir():
            raise NotADirectoryError(self.root)
        self.state_dir = self.root / ".cosmic-cypher"

    def resolve(self, relative: str | Path) -> Path:
        text = os.fspath(relative)
        if "\x00" in text:
            raise ValueError("workspace paths may not contain NUL bytes")
        low = text.lower()
        if low.startswith(("file:", "http:", "https:")):
            raise ValueError("URI-like workspace paths are not allowed")
        posix = PurePosixPath(text)
        windows = PureWindowsPath(text)
        if posix.is_absolute() or windows.is_absolute() or windows.drive or windows.root:
            raise ValueError("workspace paths must be relative")
        if ".." in posix.parts or ".." in windows.parts:
            raise ValueError("path escapes the selected workspace")
        raw = Path(text.replace("\\", "/"))
        path = (self.root / raw).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("path escapes the selected workspace") from exc
        return path

    def tree(self, relative: str | Path = ".", *, max_entries: int = 400) -> list[str]:
        base = self.resolve(relative)
        out: list[str] = []
        if base.is_file():
            return [str(base.relative_to(self.root)).replace(os.sep, "/")]
        for current, dirs, files in os.walk(base):
            dirs[:] = [d for d in sorted(dirs) if d not in _DEFAULT_IGNORES]
            c = Path(current)
            for name in sorted(files):
                p = c / name
                out.append(str(p.relative_to(self.root)).replace(os.sep, "/"))
                if len(out) >= max_entries:
                    out.append("... tree truncated ...")
                    return out
        return out

    def read(self, relative: str | Path, *, max_bytes: int = 250_000) -> str:
        p = self.resolve(relative)
        if not p.is_file():
            raise FileNotFoundError(p)
        if p.suffix.lower() in _BINARY_SUFFIXES:
            raise ValueError(f"refusing to treat binary/model file as source text: {relative}")
        size = p.stat().st_size
        if size > max_bytes:
            raise ValueError(f"file is {size} bytes; exceeds read limit {max_bytes}")
        return p.read_text(encoding="utf-8", errors="replace")

    def search(self, needle: str, *, limit: int = 50) -> list[dict[str, object]]:
        if not needle:
            return []
        hits: list[dict[str, object]] = []
        low = needle.lower()
        for rel in self.tree(max_entries=2500):
            if rel.startswith("..."):
                continue
            p = self.resolve(rel)
            if p.suffix.lower() in _BINARY_SUFFIXES or p.stat().st_size > 500_000:
                continue
            try:
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for number, line in enumerate(lines, 1):
                if low in line.lower():
                    hits.append({"path": rel, "line": number, "text": line[:500]})
                    if len(hits) >= limit:
                        return hits
        return hits

    def diff(self, relative: str | Path, content: str) -> str:
        p = self.resolve(relative)
        old = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        rel = str(Path(relative)).replace(os.sep, "/")
        return "".join(difflib.unified_diff(old.splitlines(keepends=True), content.splitlines(keepends=True), fromfile=f"a/{rel}", tofile=f"b/{rel}"))

    def write(self, relative: str | Path, content: str) -> dict[str, str | None]:
        p = self.resolve(relative)
        diff = self.diff(relative, content)
        backup: str | None = None
        if p.exists():
            stamp = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
            dest = self.state_dir / "backups" / stamp / p.relative_to(self.root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
            backup = str(dest.relative_to(self.root)).replace(os.sep, "/")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": str(p.relative_to(self.root)).replace(os.sep, "/"), "backup": backup, "diff": diff}

    def mkdir(self, relative: str | Path) -> str:
        p = self.resolve(relative)
        p.mkdir(parents=True, exist_ok=True)
        return str(p.relative_to(self.root)).replace(os.sep, "/")

    def append_event(self, event: dict) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with (self.state_dir / "sessions.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True, default=str) + "\n")

    def run(self, argv: Iterable[str], *, timeout: int = 180) -> dict[str, object]:
        args = [str(x) for x in argv]
        if not args:
            raise ValueError("empty command")
        self._validate_test_command(args)
        started = time.time()
        proc = subprocess.run(args, cwd=self.root, capture_output=True, text=True, timeout=timeout, shell=False)
        return {"argv": args, "returncode": proc.returncode, "stdout": proc.stdout[-20_000:], "stderr": proc.stderr[-20_000:], "seconds": round(time.time() - started, 3)}

    @staticmethod
    def _validate_test_command(args: list[str]) -> None:
        exe = Path(args[0]).name.lower()
        if exe in {"pytest", "ruff", "mypy"}:
            return
        if exe in {"python", "python3", "py"}:
            if len(args) >= 3 and args[1] == "-m" and args[2] in {"pytest", "unittest", "compileall", "py_compile"}:
                return
            raise PermissionError("AI-run Python is limited to test/compile modules; run other Python commands yourself")
        if exe == "cargo":
            if len(args) >= 2 and args[1] in {"test", "check", "build", "fmt", "clippy"}:
                return
            raise PermissionError("AI-run cargo is limited to test/check/build/fmt/clippy")
        if exe == "git":
            if len(args) >= 2 and args[1] in {"status", "diff", "log", "show", "grep"}:
                return
            raise PermissionError("AI-run git is read-only; commit/push remain owner actions")
        if exe in {"npm", "pnpm", "yarn"}:
            tail = args[1:]
            if tail and tail[0] in {"test", "build", "lint"}:
                return
            if len(tail) >= 2 and tail[0] == "run" and tail[1] in {"test", "build", "lint", "check", "typecheck"}:
                return
            raise PermissionError("AI-run package scripts are limited to test/build/lint/check/typecheck")
        raise PermissionError("command is outside Cosmic Cypher's bounded test runner; execute it manually if you intend to grant broader host authority")

    @staticmethod
    def shell_display(argv: Iterable[str]) -> str:
        return " ".join(shlex.quote(str(x)) for x in argv)
