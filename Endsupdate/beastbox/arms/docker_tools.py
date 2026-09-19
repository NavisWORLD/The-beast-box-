from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path
from typing import Any

from .network import NetworkPolicy
from .recorder import EvidenceRecorder
from .schema import ToolRequest, ToolResult
from .tools import BeastArms, scrub_environment


class DockerBeastArms(BeastArms):
    """Beast Arms whose command/process authority is a named Docker subject.

    Structured filesystem helpers continue to operate on ``root`` because that
    host directory is the exact bind mount exposed as ``/work``. Shell, git,
    environment inspection, and managed process commands are routed through
    ``docker exec`` so model-directed arbitrary code never executes directly on
    the supervisor host.
    """

    def __init__(
        self,
        root: str | Path,
        recorder: EvidenceRecorder,
        network_policy: NetworkPolicy,
        *,
        container_name: str,
        docker_bin: str = "docker",
        container_workdir: str = "/work",
        shell_timeout: float = 180.0,
        max_output_bytes: int = 200_000,
    ) -> None:
        super().__init__(
            root,
            recorder,
            network_policy,
            shell_timeout=shell_timeout,
            max_output_bytes=max_output_bytes,
        )
        if not container_name or any(ch.isspace() for ch in container_name):
            raise ValueError("container_name must be a non-empty Docker name without whitespace")
        self.container_name = container_name
        self.docker_bin = docker_bin
        self.container_workdir = container_workdir

    def _docker_exec_argv(self, argv: list[str]) -> list[str]:
        return [
            self.docker_bin,
            "exec",
            "--workdir",
            self.container_workdir,
            self.container_name,
            *argv,
        ]

    def _run_in_container(self, argv: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            self._docker_exec_argv(argv),
            cwd=self.root,
            env=scrub_environment(),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )

    def _execute(self, request: ToolRequest) -> tuple[ToolResult, str | None]:
        tool = request.tool.strip().lower()
        args: dict[str, Any] = dict(request.arguments)

        if tool == "shell":
            argv = args.get("argv")
            if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
                raise ValueError("shell.argv must be a non-empty array of strings")
            timeout = min(float(request.timeout_seconds), self.shell_timeout)
            proc = self._run_in_container(argv, timeout=timeout)
            return (
                ToolResult(
                    ok=proc.returncode == 0,
                    returncode=proc.returncode,
                    stdout=self._trim(proc.stdout),
                    stderr=self._trim(proc.stderr),
                    data={"execution_namespace": "docker", "container": self.container_name},
                ),
                "processes",
            )

        if tool == "git":
            argv = args.get("argv")
            if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
                raise ValueError("git.argv must be an array of strings")
            nested = ToolRequest(
                tool="shell",
                arguments={"argv": ["git", *argv]},
                timeout_seconds=request.timeout_seconds,
            )
            return self._execute(nested)

        if tool == "env":
            proc = self._run_in_container(["env"], timeout=min(float(request.timeout_seconds), 30.0))
            values: dict[str, str] = {}
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    if key and not any(marker in key.upper() for marker in ("TOKEN", "SECRET", "PASSWORD", "KEY", "GITHUB_", "AWS_", "AZURE_", "HF_", "IBM_", "SSH_")):
                        values[key] = value
            return (
                ToolResult(
                    ok=proc.returncode == 0,
                    returncode=proc.returncode,
                    stderr=self._trim(proc.stderr),
                    data={"environment": values, "execution_namespace": "docker"},
                ),
                "processes",
            )

        if tool == "process.spawn":
            argv = args.get("argv")
            if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
                raise ValueError("process.spawn argv must be a non-empty array of strings")
            proc = subprocess.Popen(
                self._docker_exec_argv(argv),
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
            return ToolResult(ok=True, data={"pid": proc.pid, "execution_namespace": "docker", "container": self.container_name}), "processes"

        if tool == "process.poll":
            pid = int(args["pid"])
            proc = self._processes.get(pid)
            if proc is None:
                raise KeyError(f"unknown managed pid {pid}")
            code = proc.poll()
            if code is None:
                return ToolResult(ok=True, data={"pid": pid, "running": True, "execution_namespace": "docker"}), "processes"
            stdout, stderr = proc.communicate()
            return (
                ToolResult(
                    ok=code == 0,
                    returncode=code,
                    stdout=self._trim(stdout),
                    stderr=self._trim(stderr),
                    data={"pid": pid, "running": False, "execution_namespace": "docker"},
                ),
                "processes",
            )

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
            return ToolResult(ok=True, data={"pid": pid, "terminated_client": True, "container_cleanup_is_authoritative": True}), "processes"

        return super()._execute(request)
