"""Bounded owner-only asynchronous chat jobs for slow CPU inference.

A completed turn goes through CosmicApp's existing durable path exactly once.
Pending jobs live only in host RAM; losing a process returns unknown rather than
falsely claiming success or silently replaying a possibly committed turn.
"""
from __future__ import annotations

import re
import secrets
import threading
import time
from typing import Any, Callable

_REQUEST_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
_JOB_ID = re.compile(r"[A-Za-z0-9_-]{32}\Z")
TTL_SECONDS = 900

# A fixed diagnostic vocabulary: upstream bodies and credentials are never
# returned to the browser. Retain exact failure identity without auto-retry.
PROVIDER_ERRORS = {
    "MODEL_AUTH_REJECTED": "Ollama or the selected provider rejected its saved API key. Use Settings → Test access (no paid inference).",
    "MODEL_ACCESS_DENIED": "The model provider denied access. Check this account's model entitlement in Settings; no automatic retry.",
    "MODEL_NOT_FOUND": "The provider did not recognize the selected model ID. Run the read-only model-list check in Settings.",
    "MODEL_RATE_LIMITED": "The provider reported a rate limit. Check provider limits before manually retrying; the request was not replayed.",
    "MODEL_TIMEOUT": "The model provider did not respond within the server timeout. Check conversation before retrying.",
    "MODEL_UNAVAILABLE": "The selected provider returned an upstream error. Check provider status and conversation before retrying.",
    "MODEL_OUTPUT_EMPTY": "The model returned no user-facing text. Its output may have been exhausted by reasoning; no automatic retry.",
    "MODEL_BAD_RESPONSE": "The provider response was missing usable text or exceeded its size limit. No automatic retry.",
}


class ChatJobs:
    def __init__(self, handler: Callable[[dict[str, Any]], tuple[int, dict[str, Any]]]):
        self._handler = handler
        self._lock = threading.Lock()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._requests: dict[str, str] = {}
        self._active: str | None = None
        self._guest_active = False

    def _prune(self) -> None:
        now = time.monotonic()
        for job_id, record in tuple(self._jobs.items()):
            if record["state"] != "running" and now - record["finished_at"] >= TTL_SECONDS:
                self._jobs.pop(job_id, None)
                self._requests.pop(record["request_id"], None)

    @staticmethod
    def _response(record: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {"job_id": record["id"], "state": record["state"]}
        if record["state"] == "complete":
            data["result"] = record["result"]
        elif record["state"] == "failed":
            code = record.get("failure_code")
            data["failure_code"] = code or "UNCONFIRMED"
            data["error"] = (
                PROVIDER_ERRORS[code] if code in PROVIDER_ERRORS else
                "Remote provider authorization was not available. Select or reactivate a model in Brain Bay."
                if code == "AUTHORITY_REVOKED" else
                "The selected model rejected or failed the request. Check conversation before retrying, or switch models in Brain Bay."
                if code == "PROVIDER_REJECTED" else
                "Chat did not return a confirmed result. Check conversation before retrying."
            )
        return data

    def acquire_guest(self) -> bool:
        """No guest may overlap an owner job or a different guest request."""
        with self._lock:
            if self._active is not None or self._guest_active:
                return False
            self._guest_active = True
            return True

    def release_guest(self) -> None:
        with self._lock:
            self._guest_active = False

    def run_when_idle(self, action: Callable[[], tuple[int, dict[str, Any]]]) -> tuple[int, dict[str, Any]]:
        """Serialize an owner model/credential change with job admission."""
        with self._lock:
            if self._active is not None:
                return 409, {"error": "Chat is still running; wait before changing models."}
            if self._guest_active:
                return 409, {"error": "Local guest inference is busy; wait before changing models."}
            return action()

    def start(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if set(body) != {"request_id", "text", "context_ids"}:
            return 400, {"error": "chat-start requires request_id, text and context_ids"}
        request_id, text, ids = body["request_id"], body["text"], body["context_ids"]
        if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
            return 400, {"error": "invalid chat request ID"}
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 8192:
            return 400, {"error": "invalid chat text"}
        if (not isinstance(ids, list) or len(ids) > 20 or
                any(type(i) is not int or i < 0 for i in ids) or len(set(ids)) != len(ids)):
            return 400, {"error": "invalid chat context IDs"}
        with self._lock:
            self._prune()
            previous = self._requests.get(request_id)
            if previous:
                record = self._jobs[previous]
                return 200 if record["state"] != "running" else 202, self._response(record)
            if self._active is not None:
                return 409, {"error": "A chat is already processing. Wait for its result before starting another."}
            if self._guest_active:
                return 409, {"error": "Local guest inference is busy. Wait before starting another chat."}
            if len(self._jobs) >= 32:
                return 429, {"error": "Recent chat job limit reached; wait before sending more."}
            job_id = secrets.token_urlsafe(24)
            record = {"id": job_id, "request_id": request_id, "state": "running",
                      "result": None, "finished_at": None}
            self._jobs[job_id] = record
            self._requests[request_id] = job_id
            self._active = job_id
            worker = threading.Thread(
                target=self._run, args=(job_id, {"text": text, "context_ids": list(ids)}),
                name="cosmos-owner-chat", daemon=True,
            )
            worker.start()
            return 202, self._response(record)

    def _run(self, job_id: str, payload: dict[str, Any]) -> None:
        result: dict[str, Any] | None = None
        success = False
        failure_code = "UNCONFIRMED"
        try:
            status, response = self._handler(payload)
            if status == 403:
                failure_code = "AUTHORITY_REVOKED"
            elif (isinstance(response, dict)
                    and response.get("provider_failure") in PROVIDER_ERRORS):
                failure_code = response["provider_failure"]
            elif status in (400, 401, 404, 429, 500, 502, 503, 504):
                failure_code = "PROVIDER_REJECTED"
            if status == 200 and isinstance(response, dict) and isinstance(
                response.get("result"), dict
            ) and isinstance(response["result"].get("response"), str):
                result = response
                success = True
        except Exception:
            # Do not log prompts, context, model output, host secrets or exceptions.
            pass
        finally:
            with self._lock:
                record = self._jobs.get(job_id)
                if record is not None:
                    record["state"] = "complete" if success else "failed"
                    record["result"] = result
                    record["failure_code"] = failure_code if not success else None
                    record["finished_at"] = time.monotonic()
                if self._active == job_id:
                    self._active = None

    def get(self, job_id: str) -> tuple[int, dict[str, Any]]:
        if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id):
            return 400, {"error": "invalid chat job ID"}
        with self._lock:
            self._prune()
            record = self._jobs.get(job_id)
            if record is None:
                return 410, {"error": "Job unavailable after expiry or restart. Check conversation before retrying."}
            return 200, self._response(record)
