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


class ChatJobs:
    def __init__(self, handler: Callable[[dict[str, Any]], tuple[int, dict[str, Any]]]):
        self._handler = handler
        self._lock = threading.Lock()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._requests: dict[str, str] = {}
        self._active: str | None = None

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
            data["error"] = "Chat did not return a confirmed result. Check conversation before retrying."
        return data

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
        try:
            status, response = self._handler(payload)
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
