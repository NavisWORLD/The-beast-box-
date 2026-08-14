from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import tarfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .network import NetworkPolicy, safe_dns_lookup, safe_http_request
from .recorder import EvidenceRecorder
from .schema import ToolRequest, ToolResult

_SECRET_MARKERS = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "API_KEY",
    "PRIVATE_KEY",
    "GITHUB_",
    "AWS_",
    "AZURE_",
    "GOOGLE_",
    "HF_",
    "HUGGINGFACE_",
    "IBM_",
    "SSH_",
)
_BINARY_CHUNK = 64 * 1024


def _looks_secret(name: str) -> bool:
    upper = name.upper()
    return any(marker in upper for marker in _SECRET_MARKERS)


def scrub_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if source is None else source)
    return {key: value for key, value in env.items() if not _looks_secret(key)}


def _log_request(request: ToolRequest) -> dict[str, Any]:
    value = request.to_dict()
    arguments = dict(value.get("arguments") or {})
    for key in list(arguments):
        if key.lower() in {"content", "body", "data"}:
            raw = arguments[key]
            if isinstance(raw, str):
                encoded = raw.encode("utf-8")
            elif isinstance(raw, bytes):
                encoded = raw
            else:
                encoded = json.dumps(raw, sort_keys=True, default=str).encode("utf-8")
            arguments[key] = {"bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}
        elif _looks_secret(key):
            arguments[key] = "<redacted>"
    value["arguments"] = arguments
    return value


class BeastArms:
    """Broad model-visible tools intended only for a disposable OS namespace.

    Structured filesystem helpers stay under ``root`` for deterministic tool
    semantics. The ``shell`` and process arms are intentionally *not* an
    executable allowlist; their real authority boundary must be the disposable
    container/VM created by the external launcher.
    """

    def __init__(
        self,
        root: str | Path,
        recorder: EvidenceRecorder,
        network_policy: NetworkPolicy,
        *,
        shell_timeout: float = 180.0,
        max_output_bytes: int = 200_000,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.recorder = recorder
        self.network_policy = network_policy
        self.shell_timeout = float(shell_timeout)
        self.max_output_bytes = int(max_output_bytes)
        self.scratch_dir = self.root / ".beast-arms-scratch"
        self._processes: dict[int, subprocess.Popen[str]] = {}

    def _resolve(self, relative: str | Path) -> Path:
        text = os.fspath(relative)
        if "\x00" in text:
            raise PermissionError("structured path contains NUL")
        posix = PurePosixPath(text)
        windows = PureWindowsPath(text)
        if posix.is_absolute() or windows.is_absolute() or windows.drive or windows.root:
            raise PermissionError("structured filesystem paths must be relative")
        if ".." in posix.parts or ".." in windows.parts:
            raise PermissionError("structured filesystem path escapes subject root")
        candidate = (self.root / Path(text.replace("\\", "/"))).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise PermissionError("structured filesystem path escapes subject root") from exc
        return candidate

    def _trim(self, text: str) -> str:
        raw = text.encode("utf-8", errors="replace")
        if len(raw) <= self.max_output_bytes:
            return text
        return raw[-self.max_output_bytes :].decode("utf-8", errors="replace")

    def _record(self, request: ToolRequest, result: ToolResult, *, stream: str | None = None) -> ToolResult:
        self.recorder.emit("tool", request.tool, _log_request(request), result.to_dict(), stream=stream)
        return result

    def execute(self, request: ToolRequest) -> ToolResult:
        try:
            result, stream = self._execute(request)
        except PermissionError as exc:
            result, stream = ToolResult(ok=False, blocked=True, error=f"PermissionError: {exc}"), None
        except subprocess.TimeoutExpired as exc:
            result, stream = ToolResult(ok=False, error=f"TimeoutExpired: {exc}"), "processes"
        except Exception as exc:  # tool errors become observations, not harness crashes
            result, stream = ToolResult(ok=False, error=f"{type(exc).__name__}: {exc}"), None
        return self._record(request, result, stream=stream)

    def _execute(self, request: ToolRequest) -> tuple[ToolResult, str | None]:
        tool = request.tool.strip().lower()
        args = dict(request.arguments)
        if tool == "fs.list":
            base = self._resolve(str(args.get("path", ".")))
            if base.is_file():
                entries = [str(base.relative_to(self.root))]
            else:
                entries = [str(p.relative_to(self.root)) for p in sorted(base.iterdir())]
            return ToolResult(ok=True, data={"entries": entries}), None
        if tool == "fs.read":
            path = self._resolve(str(args["path"]))
            raw = path.read_bytes()
            limit = int(args.get("max_bytes", self.max_output_bytes))
            chunk = raw[:limit]
            return ToolResult(ok=True, stdout=chunk.decode("utf-8", errors="replace"), bytes_read=len(chunk), data={"truncated": len(raw) > limit}), None
        if tool == "fs.write":
            path = self._resolve(str(args["path"]))
            content = str(args.get("content", ""))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            size = len(content.encode("utf-8"))
            return ToolResult(ok=True, bytes_written=size, data={"path": str(path.relative_to(self.root))}), "filesystem"
        if tool == "fs.patch":
            path = self._resolve(str(args["path"]))
            old, new = str(args["find"]), str(args.get("replace", ""))
            current = path.read_text(encoding="utf-8")
            count = int(args.get("count", 1))
            if old not in current:
                raise ValueError("patch find text not present")
            updated = current.replace(old, new, count)
            path.write_text(updated, encoding="utf-8")
            return ToolResult(ok=True, bytes_written=len(updated.encode("utf-8")), data={"path": str(path.relative_to(self.root))}), "filesystem"
        if tool == "fs.search":
            needle = str(args.get("query", ""))
            if not needle:
                return ToolResult(ok=True, data={"matches": []}), None
            matches: list[dict[str, Any]] = []
            limit = int(args.get("limit", 100))
            for path in self.root.rglob("*"):
                if not path.is_file() or self.scratch_dir in path.parents:
                    continue
                try:
                    if path.stat().st_size > 1_000_000:
                        continue
                    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                except OSError:
                    continue
                for number, line in enumerate(lines, 1):
                    if needle.lower() in line.lower():
                        matches.append({"path": str(path.relative_to(self.root)), "line": number, "text": line[:500]})
                        if len(matches) >= limit:
                            return ToolResult(ok=True, data={"matches": matches}), None
            return ToolResult(ok=True, data={"matches": matches}), None
        if tool == "shell":
            argv = args.get("argv")
            if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
                raise ValueError("shell.argv must be a non-empty array of strings")
            timeout = min(float(request.timeout_seconds), self.shell_timeout)
            proc = subprocess.run(
                argv,
                cwd=self.root,
                env=scrub_environment(),
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
            return ToolResult(ok=proc.returncode == 0, returncode=proc.returncode, stdout=self._trim(proc.stdout), stderr=self._trim(proc.stderr)), "processes"
        if tool == "process.spawn":
            argv = args.get("argv")
            if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
                raise ValueError("process.spawn argv must be a non-empty array of strings")
            proc = subprocess.Popen(
                argv,
                cwd=self.root,
                env=scrub_environment(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
                start_new_session=True,
            )
            self._processes[proc.pid] = proc
            return ToolResult(ok=True, data={"pid": proc.pid}), "processes"
        if tool == "process.poll":
            pid = int(args["pid"])
            proc = self._processes.get(pid)
            if proc is None:
                raise KeyError(f"unknown managed pid {pid}")
            code = proc.poll()
            if code is None:
                return ToolResult(ok=True, data={"pid": pid, "running": True}), "processes"
            stdout, stderr = proc.communicate()
            return ToolResult(ok=code == 0, returncode=code, stdout=self._trim(stdout), stderr=self._trim(stderr), data={"pid": pid, "running": False}), "processes"
        if tool == "process.kill":
            pid = int(args["pid"])
            proc = self._processes.get(pid)
            if proc is None:
                raise KeyError(f"unknown managed pid {pid}")
            if proc.poll() is None:
                if os.name == "posix":
                    os.killpg(proc.pid, signal.SIGTERM)
                else:
                    proc.terminate()
            return ToolResult(ok=True, data={"pid": pid, "terminated": True}), "processes"
        if tool == "http":
            data = safe_http_request(
                str(args["url"]),
                method=str(args.get("method", "GET")),
                headers=dict(args.get("headers") or {}),
                body=str(args["body"]).encode("utf-8") if "body" in args else None,
                timeout=min(float(request.timeout_seconds), 30.0),
                max_bytes=min(int(args.get("max_bytes", 2_000_000)), 5_000_000),
                policy=self.network_policy,
            )
            return ToolResult(ok=True, bytes_read=int(data.get("bytes", 0)), data=data), "network"
        if tool == "dns":
            data = safe_dns_lookup(str(args["host"]), policy=self.network_policy, port=int(args.get("port", 443)))
            return ToolResult(ok=True, data=data), "network"
        if tool == "git":
            argv = args.get("argv")
            if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
                raise ValueError("git.argv must be an array of strings")
            nested = ToolRequest(tool="shell", arguments={"argv": ["git", *argv]}, timeout_seconds=request.timeout_seconds)
            result, _ = self._execute(nested)
            return result, "processes"
        if tool == "archive":
            action = str(args.get("action", "list"))
            path = self._resolve(str(args["path"]))
            if action == "list":
                if zipfile.is_zipfile(path):
                    names = zipfile.ZipFile(path).namelist()
                elif tarfile.is_tarfile(path):
                    with tarfile.open(path) as archive:
                        names = archive.getnames()
                else:
                    raise ValueError("unsupported archive")
                return ToolResult(ok=True, data={"members": names[:2000]}), None
            if action == "unpack":
                dest = self._resolve(str(args.get("dest", ".")))
                dest.mkdir(parents=True, exist_ok=True)
                if zipfile.is_zipfile(path):
                    with zipfile.ZipFile(path) as archive:
                        for member in archive.infolist():
                            self._safe_archive_member(dest, member.filename)
                        archive.extractall(dest)
                elif tarfile.is_tarfile(path):
                    with tarfile.open(path) as archive:
                        for member in archive.getmembers():
                            self._safe_archive_member(dest, member.name)
                            if member.issym() or member.islnk():
                                raise PermissionError("structured archive extraction rejects links")
                        archive.extractall(dest, filter="data")
                else:
                    raise ValueError("unsupported archive")
                return ToolResult(ok=True, data={"dest": str(dest.relative_to(self.root))}), "filesystem"
            if action == "pack":
                source = self._resolve(str(args.get("source", ".")))
                base = str(path)
                fmt = str(args.get("format", "zip"))
                if fmt not in {"zip", "gztar", "tar"}:
                    raise ValueError("archive format must be zip, gztar, or tar")
                made = shutil.make_archive(base.removesuffix(Path(base).suffix), fmt, root_dir=source)
                return ToolResult(ok=True, data={"path": made}), "filesystem"
            raise ValueError(f"unsupported archive action {action!r}")
        if tool == "env":
            return ToolResult(ok=True, data={"environment": scrub_environment()}), None
        if tool == "scratch.write":
            key = self._scratch_key(str(args["key"]))
            self.scratch_dir.mkdir(parents=True, exist_ok=True)
            value = str(args.get("value", ""))
            key.write_text(value, encoding="utf-8")
            return ToolResult(ok=True, bytes_written=len(value.encode("utf-8"))), "filesystem"
        if tool == "scratch.read":
            key = self._scratch_key(str(args["key"]))
            value = key.read_text(encoding="utf-8")
            return ToolResult(ok=True, stdout=value, bytes_read=len(value.encode("utf-8"))), None
        if tool == "receipt":
            return ToolResult(ok=True, data={"accepted": True, "note": str(args.get("note", ""))[:2000]}), None
        raise ValueError(f"unsupported Beast Arms tool {tool!r}")

    @staticmethod
    def _safe_archive_member(dest: Path, name: str) -> Path:
        posix = PurePosixPath(name)
        windows = PureWindowsPath(name)
        if posix.is_absolute() or windows.is_absolute() or windows.drive or ".." in posix.parts or ".." in windows.parts:
            raise PermissionError("archive member escapes destination")
        target = (dest / Path(name.replace("\\", "/"))).resolve()
        try:
            target.relative_to(dest.resolve())
        except ValueError as exc:
            raise PermissionError("archive member escapes destination") from exc
        return target

    def _scratch_key(self, key: str) -> Path:
        if not key or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for ch in key):
            raise ValueError("scratch key contains unsupported characters")
        return self.scratch_dir / key
