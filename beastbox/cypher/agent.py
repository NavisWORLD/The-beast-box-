from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .models import LocalChatModel
from .workspace import Workspace

SYSTEM_PROMPT = """You are Cosmic Cypher, a local coding agent operating inside one user-selected workspace.
You may inspect and edit source code only through the tool protocol below. Do not invent tool results.
Do not request host escape, credentials, persistence, privilege escalation, or network lateral movement.
The owner can choose any local model, but host authority stays explicit.

Return exactly one JSON object per turn. Allowed forms:
{"action":"list","path":"."}
{"action":"read","path":"relative/file.py"}
{"action":"search","query":"symbol or text"}
{"action":"mkdir","path":"relative/dir"}
{"action":"write","path":"relative/file.py","content":"complete new UTF-8 file content"}
{"action":"run","argv":["pytest","-q"]}
{"action":"finish","message":"concise result and what changed"}

Rules:
- use relative workspace paths only;
- inspect before editing when possible;
- preserve existing behavior unless the task requires change;
- write complete file contents, not patches;
- use run only for tests/build checks;
- finish only after the requested work is implemented or after naming a concrete blocker.
"""


@dataclass
class AgentResult:
    session_id: str
    final: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    changed_paths: list[str] = field(default_factory=list)
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"session_id": self.session_id, "final": self.final, "steps": self.steps, "changed_paths": sorted(set(self.changed_paths)), "dry_run": self.dry_run}


def _extract_json(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("model did not return a JSON action")
        value = json.loads(candidate[start:end + 1])
    if not isinstance(value, dict) or "action" not in value:
        raise ValueError("model action must be a JSON object with an action field")
    return value


class CoderAgent:
    def __init__(self, model: LocalChatModel, workspace: Workspace, *, apply: bool = False, allow_run: bool = False, max_steps: int = 16, system_prompt: str = SYSTEM_PROMPT) -> None:
        self.model, self.workspace, self.apply, self.allow_run = model, workspace, apply, allow_run
        self.max_steps = max(1, max_steps)
        self.system_prompt = system_prompt
        self.overlay: dict[str, str] = {}

    def _read(self, path: str) -> str:
        key = path.replace("\\", "/")
        return self.overlay[key] if key in self.overlay else self.workspace.read(path)

    def run(self, task: str) -> AgentResult:
        session_id = uuid.uuid4().hex
        result = AgentResult(session_id=session_id, final="", dry_run=not self.apply)
        messages: list[dict[str, str]] = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": f"TASK:\n{task}\n\nWORKSPACE TREE:\n" + "\n".join(self.workspace.tree()) + f"\n\nMODE: {'APPLY' if self.apply else 'DRY RUN'}; test runner: {'enabled' if self.allow_run else 'disabled'}"}]
        for step_index in range(1, self.max_steps + 1):
            raw = self.model.chat(messages)
            try:
                action = _extract_json(raw)
            except Exception as exc:
                observation = {"ok": False, "error": str(exc), "hint": "return exactly one allowed JSON action"}
                messages.extend([{"role": "assistant", "content": raw}, {"role": "user", "content": "TOOL RESULT:\n" + json.dumps(observation)}])
                result.steps.append({"step": step_index, "action": "protocol_error", "result": observation})
                continue
            name = str(action.get("action", "")).lower()
            try:
                observation, ok = self._execute(name, action, result), True
            except Exception as exc:
                observation, ok = {"error": f"{type(exc).__name__}: {exc}"}, False
            record = {"step": step_index, "action": name, "request": action, "ok": ok, "result": observation}
            result.steps.append(record)
            audit_request = dict(action)
            if name == "write" and "content" in audit_request:
                raw_content = str(audit_request.pop("content"))
                audit_request["content_bytes"] = len(raw_content.encode("utf-8"))
                audit_request["content_sha256"] = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
            audit_result = observation
            if isinstance(observation, dict) and "diff" in observation:
                audit_result = dict(observation)
                diff_text = str(audit_result.pop("diff"))
                audit_result["diff_bytes"] = len(diff_text.encode("utf-8"))
                audit_result["diff_sha256"] = hashlib.sha256(diff_text.encode("utf-8")).hexdigest()
            self.workspace.append_event({"session_id": session_id, "ts": time.time(), "step": step_index, "action": name, "request": audit_request, "ok": ok, "result": audit_result})
            if name == "finish" and ok:
                result.final = str(action.get("message") or "finished")
                return result
            messages.extend([{"role": "assistant", "content": json.dumps(action, ensure_ascii=False)}, {"role": "user", "content": "TOOL RESULT:\n" + json.dumps(observation, ensure_ascii=False, default=str)}])
        result.final = f"max_steps={self.max_steps} reached before the model emitted finish"
        return result

    def _execute(self, name: str, action: dict[str, Any], result: AgentResult) -> Any:
        if name == "list":
            return self.workspace.tree(str(action.get("path") or "."))
        if name == "read":
            path = str(action["path"]); return {"path": path, "content": self._read(path)}
        if name == "search":
            return self.workspace.search(str(action.get("query") or ""))
        if name == "mkdir":
            path = str(action["path"]); return {"path": self.workspace.mkdir(path) if self.apply else path, "applied": self.apply}
        if name == "write":
            path, content = str(action["path"]), str(action.get("content") or "")
            diff = self.workspace.diff(path, content); result.changed_paths.append(path)
            if self.apply:
                return {**self.workspace.write(path, content), "applied": True}
            self.overlay[path.replace("\\", "/")] = content
            return {"path": path, "diff": diff, "applied": False}
        if name == "run":
            argv = action.get("argv")
            if not isinstance(argv, list) or not all(isinstance(v, str) for v in argv):
                raise ValueError("run.argv must be a JSON array of strings")
            if not self.allow_run:
                return {"skipped": True, "reason": "test runner disabled; pass --allow-run"}
            if self.overlay and not self.apply:
                return {"skipped": True, "reason": "dry-run edits are in memory; use --apply before running tests"}
            return self.workspace.run(argv)
        if name == "finish":
            return {"finished": True}
        raise ValueError(f"unsupported action {name!r}")
