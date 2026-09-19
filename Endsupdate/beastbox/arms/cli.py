from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from ..cypher.models import ModelSpec, create_model
from .docker_tools import DockerBeastArms
from .network import NetworkPolicy
from .replay import read_replay, verify_bundle
from .subject import NetworkedCageSubject
from .supervisor import BenchmarkSupervisor, VERDICT_INVALID
from .tools import scrub_environment


_COMPACT_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "t": {
            "type": "string",
            "enum": ["l", "r", "w", "x", "q", "s", "p", "o", "k", "h", "d", "g", "a", "e", "n", "m", "c", "f"],
        },
        "a": {"type": "object"},
    },
    "required": ["t", "a"],
    "additionalProperties": False,
}


def compact_action_model_options() -> dict:
    """Constrain compact short-context subjects to the Beast Arms wire envelope.

    This is a decoding constraint at the local inference server, not an action
    injection: Zeref still chooses the tool alias and all arguments. The cage,
    network policy, canaries, and supervisor remain unchanged.
    """
    return {
        "request": {
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "beast_action",
                    "strict": True,
                    "schema": _COMPACT_ACTION_SCHEMA,
                },
            }
        }
    }


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="beast-arms", description="Reusable Beast Arms Networked Cage benchmark tools")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a model-in-the-loop benchmark against a disposable Docker subject")
    run.add_argument("--base-url", required=True, help="loopback local model server URL, e.g. http://127.0.0.1:18080/v1")
    run.add_argument("--model", required=True, help="model identifier sent to the local inference server")
    run.add_argument("--backend", default="openai-compatible")
    run.add_argument("--out", required=True, help="external evidence bundle directory")
    run.add_argument("--duration", type=int, default=1800)
    run.add_argument("--run-id", default=None)
    run.add_argument("--model-revision", default="")
    run.add_argument("--model-sha256", default="")
    run.add_argument("--model-file", default="")
    run.add_argument("--temperature", type=float, default=0.2)
    run.add_argument("--max-tokens", type=int, default=1024)
    run.add_argument("--context", type=int, default=8192)
    run.add_argument("--max-turns", type=int, default=10000)
    run.add_argument("--cage-ready-timeout", type=int, default=900)
    run.add_argument("--compact-subject", action="store_true", help="use the compact short-context Beast Arms wire protocol")
    run.add_argument(
        "--strict-duration",
        action="store_true",
        help="record model finish claims but keep the subject active until the supervisor deadline",
    )

    verify = sub.add_parser("verify", help="verify hashes and canary/verdict consistency without executing tools")
    verify.add_argument("path")

    replay = sub.add_parser("replay", help="print frozen event observations; never executes recorded actions")
    replay.add_argument("path")
    replay.add_argument("--limit", type=int, default=0)
    return parser


def _wait_ready(path: Path, launcher: subprocess.Popen[str], timeout: int) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        code = launcher.poll()
        if code is not None:
            raise RuntimeError(f"cage launcher exited before readiness with code {code}")
        time.sleep(0.25)
    raise TimeoutError(f"cage did not become ready within {timeout} seconds")


def _signal_launcher_group(launcher: subprocess.Popen[str], sig: int) -> None:
    try:
        os.killpg(launcher.pid, sig)
    except (AttributeError, ProcessLookupError, PermissionError):
        if sig == signal.SIGTERM:
            launcher.terminate()
        else:
            launcher.kill()


def _terminate_launcher(launcher: subprocess.Popen[str] | None) -> None:
    if launcher is None or launcher.poll() is not None:
        return
    _signal_launcher_group(launcher, signal.SIGTERM)
    try:
        launcher.wait(timeout=30)
    except subprocess.TimeoutExpired:
        _signal_launcher_group(launcher, signal.SIGKILL)
        launcher.wait(timeout=10)


def _restore_workspace_access(work: Path) -> None:
    """Reclaim the subject workspace only after the cage launcher has stopped."""
    owner = f"{os.getuid()}:{os.getgid()}"
    subprocess.run(["sudo", "chown", "-R", owner, str(work)], check=True)
    subprocess.run(["sudo", "chmod", "700", str(work)], check=True)


def run_benchmark(args: argparse.Namespace) -> int:
    if args.duration <= 0:
        raise ValueError("duration must be positive")
    run_id = args.run_id or f"networked-cage-{_utc_stamp()}"
    evidence = Path(args.out).expanduser().resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    runtime = evidence.parent / f".{evidence.name}-runtime-{run_id}"
    if runtime.exists():
        shutil.rmtree(runtime)
    work = runtime / "workspace"
    boundary = runtime / "boundary"
    ready = runtime / "cage-ready.json"
    runtime.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    boundary.mkdir(parents=True, exist_ok=True)

    repo_root = Path(__file__).resolve().parents[2]
    launcher_script = repo_root / "scripts" / "networked_cage.sh"
    launcher_stdout = (evidence / "cage-launcher.stdout.log").open("w", encoding="utf-8")
    launcher_stderr = (evidence / "cage-launcher.stderr.log").open("w", encoding="utf-8")
    launcher: subprocess.Popen[str] | None = None
    subject_claim = ""
    infrastructure_ok = True
    infrastructure_error = ""
    action_constraint = bool(args.compact_subject and args.backend.strip().lower().replace("_", "-") in {"openai-compatible", "llama.cpp-server", "llama-server", "lm-studio"})

    model_identity = {
        "backend": args.backend,
        "model": args.model,
        "base_url": args.base_url,
        "revision": args.model_revision,
        "file": args.model_file,
        "file_sha256": args.model_sha256,
        "context": args.context,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "compact_subject": bool(args.compact_subject),
        "compact_action_json_schema": action_constraint,
        "strict_duration": bool(args.strict_duration),
    }
    supervisor = BenchmarkSupervisor(
        evidence_root=evidence,
        subject_root=work,
        boundary_root=boundary,
        run_id=run_id,
        duration_seconds=args.duration,
        model_identity=model_identity,
    )

    try:
        supervisor.prepare_canaries()

        launcher = subprocess.Popen(
            [
                "bash",
                str(launcher_script),
                "--duration",
                str(args.duration + 600),
                "--out",
                str(runtime),
                "--run-id",
                run_id,
                "--work-dir",
                str(work),
                "--boundary-dir",
                str(boundary),
                "--evidence-dir",
                str(evidence),
                "--ready-file",
                str(ready),
            ],
            cwd=repo_root,
            env=scrub_environment(),
            stdout=launcher_stdout,
            stderr=launcher_stderr,
            text=True,
            start_new_session=True,
        )
        cage = _wait_ready(ready, launcher, args.cage_ready_timeout)
        supervisor.model_identity.update(
            {"cage": {"container": cage.get("container"), "network": cage.get("network")}}
        )

        supervisor.start()
        model = create_model(
            ModelSpec(
                alias="networked-cage-subject",
                backend=args.backend,
                model=args.model,
                base_url=args.base_url,
                context=args.context,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                options=compact_action_model_options() if action_constraint else {},
            )
        )
        assert supervisor.recorder is not None
        arms = DockerBeastArms(
            work,
            supervisor.recorder,
            NetworkPolicy(),
            container_name=str(cage["container"]),
        )
        subject = NetworkedCageSubject(
            model,
            arms,
            max_turns=args.max_turns,
            deadline_monotonic=supervisor.deadline_monotonic,
            compact=args.compact_subject,
            strict_duration=args.strict_duration,
        )
        result = subject.run()
        subject_claim = result.final_message
        (evidence / "subject-result.json").write_text(
            json.dumps(
                {
                    "finished": result.finished,
                    "timed_out": result.timed_out,
                    "tool_calls": result.tool_calls,
                    "turns": result.turns,
                    "protocol_errors": result.protocol_errors,
                    "final_message": result.final_message,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        infrastructure_ok = False
        infrastructure_error = f"{type(exc).__name__}: {exc}"
        (evidence / "infrastructure-error.txt").write_text(infrastructure_error + "\n", encoding="utf-8")
    finally:
        _terminate_launcher(launcher)
        try:
            _restore_workspace_access(work)
        except Exception as exc:
            infrastructure_ok = False
            infrastructure_error = (
                (infrastructure_error + "; " if infrastructure_error else "")
                + f"workspace ownership restore failed: {type(exc).__name__}: {exc}"
            )
        launcher_stdout.close()
        launcher_stderr.close()

    try:
        if work.exists():
            shutil.make_archive(str(evidence / "workspace_snapshot"), "gztar", root_dir=work)
    except Exception as exc:
        infrastructure_ok = False
        infrastructure_error = (
            (infrastructure_error + "; " if infrastructure_error else "")
            + f"workspace snapshot failed: {type(exc).__name__}: {exc}"
        )

    try:
        if supervisor.canaries is None:
            supervisor.prepare_canaries()
        if supervisor.recorder is None:
            supervisor.start()
            infrastructure_ok = False
            infrastructure_error = infrastructure_error or "cage/model preflight failed before subject start"
    except Exception as exc:
        infrastructure_ok = False
        infrastructure_error = (
            (infrastructure_error + "; " if infrastructure_error else "")
            + f"evidence finalization preflight failed: {type(exc).__name__}: {exc}"
        )
        raise RuntimeError(infrastructure_error) from exc

    verdict = supervisor.finalize(
        subject_claim=subject_claim,
        infrastructure_ok=infrastructure_ok,
        infrastructure_error=infrastructure_error,
    )
    check = verify_bundle(evidence)
    summary = {
        "run_id": run_id,
        "verdict": verdict.label,
        "evidence_integrity": check.ok,
        "verification_errors": list(check.errors),
        "evidence": str(evidence),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    try:
        shutil.rmtree(runtime)
    except OSError:
        pass
    if not check.ok or verdict.label == VERDICT_INVALID:
        return 3
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return run_benchmark(args)
    if args.command == "verify":
        result = verify_bundle(args.path)
        print(json.dumps({"ok": result.ok, "checked_files": result.checked_files, "errors": list(result.errors)}, indent=2, sort_keys=True))
        return 0 if result.ok else 2
    if args.command == "replay":
        count = 0
        for event in read_replay(args.path):
            print(json.dumps(event, sort_keys=True, ensure_ascii=False))
            count += 1
            if args.limit and count >= args.limit:
                break
        return 0
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())