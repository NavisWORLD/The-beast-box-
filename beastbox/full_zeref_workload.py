from __future__ import annotations

import hashlib
import json
from typing import Any

FROZEN_WORKLOAD = (
    {"id": "instruction", "prompt": "Reply exactly with: ZEREF READY", "expected_substring": "zeref ready"},
    {"id": "memory_store", "prompt": "Remember this code word for later: ORBIT-47. Reply ACK.", "expected_substring": "ack"},
    {"id": "memory_recall", "prompt": "What code word did I ask you to remember?", "expected_substring": "orbit"},
    {"id": "arithmetic", "prompt": "Solve 17 + 25. Reply with the number only.", "expected_substring": "42"},
    {"id": "code_reasoning", "prompt": "A Python function should add 2 to x but returns x * 2. In one short line, identify the bug.", "expected_substring": ""},
    {"id": "correction", "prompt": "Correction: the code word is now NEBULA-9, not ORBIT-47. Acknowledge the correction.", "expected_substring": "nebula"},
    {"id": "corrected_recall", "prompt": "What is the current corrected code word?", "expected_substring": "nebula"},
    {"id": "limits", "prompt": "State one limitation of this experiment in one sentence.", "expected_substring": ""},
)

CLASSICAL_NATIVE_SEED = 20260820


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def workload_sha256() -> str:
    return hashlib.sha256(_canonical(FROZEN_WORKLOAD)).hexdigest()
