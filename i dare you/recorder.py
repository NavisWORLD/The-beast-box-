"""Beast Box JEV × PHOS experiment recorder.

Offline operation measures substrate/checkpoint controls ONLY. Neither a network
provider nor PHOS weight training is emulated. JEV private data is never copied
into the public ledger or into the distribution package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import sys
import time
from datetime import datetime, timezone
from urllib import request
from urllib.error import HTTPError, URLError

GENESIS = "0" * 64
PHASES = ("A0", "CHECKPOINT_1", "B0", "B1", "B2", "A1", "CONTROL", "FINAL")
JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha(value: bytes):
    return hashlib.sha256(value).hexdigest()


def file_hash(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as dst:
        dst.write(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True).encode() + b"\n")
        dst.flush()
        os.fsync(dst.fileno())
    tmp.replace(path)


class Ledger:
    """Append-only hash-linked events; verify every preceding event before appending."""
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        past = verify_ledger(path)
        self.seq = len(past)
        self.previous = past[-1]["event_hash"] if past else GENESIS

    def emit(self, phase, kind, payload, provenance="beastbox.i_dare_you.recorder.v1"):
        if phase not in PHASES:
            raise ValueError("invalid phase")
        event = {"timestamp": timestamp(), "seq": self.seq + 1, "phase": phase,
                 "event_type": kind, "provenance": provenance, "previous_hash": self.previous,
                 "payload": payload}
        event["event_hash"] = sha(canonical(event))
        with self.path.open("ab") as dst:
            dst.write(canonical(event) + b"\n")
            dst.flush()
            os.fsync(dst.fileno())
        self.previous = event["event_hash"]
        self.seq += 1
        return event


def verify_ledger(path: Path):
    if not path.exists():
        return []
    previous, result = GENESIS, []
    for line_num, line in enumerate(path.read_bytes().splitlines(), 1):
        event = json.loads(line)
        received = event.pop("event_hash")
        expected = sha(canonical(event))
        if received != expected or event["previous_hash"] != previous or event["seq"] != line_num:
            raise ValueError(f"ledger corrupted at line {line_num}")
        event["event_hash"] = received
        result.append(event)
        previous = received
    return result


def post_json(url, payload, key=None, timeout=20):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = request.Request(url, data=canonical(payload), headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"provider call unavailable: {type(exc).__name__}") from None


def jev_decide(prompt, memory, model="jev-latest"):
    key = os.getenv("TYPESAFE_API_KEY")
    if not key:
        raise RuntimeError("TYPESAFE_API_KEY absent")
    # Choice is a typed decision, NOT a generated chat response.
    body = {"model": model, "state": {"current_input": prompt, "external_memory": memory},
            "questions": {"route": {"type": "choice",
                                   "instructions": "Classify the input for routing, not freeform dialogue.",
                                   "criteria": {"question": "The input requests information",
                                                "statement": "The input states information",
                                                "other": "Neither of the above"}}}}
    return post_json(JEV_ENDPOINT, body, key=key)


def phos_generate(prompt, url):
    if not url.startswith("http://127.0.0.1:") and not url.startswith("http://localhost:"):
        raise ValueError("PHOS adapter must bind to local loopback")
    return post_json(url.rstrip("/") + "/api/generate",
                     {"model": "phos", "prompt": prompt, "stream": False,
                      "options": {"num_predict": 96}})


def initial_state():
    return {"schema": "independent_substrate_fixture_v1", "dyn12": [0.0] * 12,
            "memory": [], "state_counter": 0, "active_provider": None,
            "authority": "none", "routing": "fixed_choice_fixture_v1"}


def memory_context(state):
    return "\n".join(record["content"] for record in state["memory"])


def snapshot(state):
    return sha(canonical(state))


def check_control(original, current, kind):
    copy = json.loads(json.dumps(current))
    if kind == "empty_memory":
        copy["memory"] = []
    elif kind == "shuffled_memory":
        copy["memory"] = list(reversed(copy["memory"]))
    elif kind == "no_training":
        return {"status": "BLOCKED", "reason": "authentic PHOS checkpoint unavailable"}
    elif kind == "independent_training":
        return {"status": "BLOCKED", "reason": "authentic PHOS training and held-out evaluation unavailable"}
    else:
        raise ValueError("unknown control")
    return {"status": "EXECUTED", "name": kind,
            "memory_count": len(copy["memory"]), "state_counter": copy["state_counter"],
            "memory_context_matches_full": memory_context(copy) == memory_context(current),
            "state_snapshot_sha256": snapshot(copy)}


def sanitize_error(exc):
    s = str(exc)
    s = re.sub(r"(?i)(bearer|api[_-]?key|token)\s*[=:]\s*\S+", r"\1=<REDACTED>", s)
    return s[:350]


def run(out: Path, *, enable_jev=False, phos_checkpoint=None, phos_url=None, training_command=None):
    if (out / "events.jsonl").exists():
        raise FileExistsError("Run directory already exists; immutable evidence cannot be overwritten")
    private, public = out / "private_jev", out / "public_research"
    private.mkdir(parents=True)
    public.mkdir(parents=True)
    ledger = Ledger(out / "events.jsonl")
    private_ledger = Ledger(private / "jev_events.jsonl")
    run_id = secrets.token_hex(12)
    ledger.emit("A0", "run_started", {"run_id": run_id, "mode": "actual_execution_no_simulation",
                                      "source": "independent_substrate_fixture"})
    state = initial_state()
    # This controlled fixture tests storage and retrieval, not provider learning.
    for i, content in enumerate(("CANARY_ALPHA: independent context before provider swap",
                                 "CANARY_BETA: preserve user-managed state across providers"), 1):
        state["memory"].append({"id": i, "content": content, "origin": "independent_test_fixture"})
    state["state_counter"] = 1
    state["dyn12"][0] = 0.125
    write_json(out / "substrate_state.json", state)
    ledger.emit("A0", "independent_state_written", {"state_sha256": file_hash(out / "substrate_state.json"),
               "memory_count": 2, "state_counter": 1, "dyn12": state["dyn12"],
               "provider": None})
    suite = ("Classify this request: what is preserved during a swap?",)
    if enable_jev and os.getenv("TYPESAFE_API_KEY"):
        for prompt in suite:
            start = time.monotonic()
            try:
                response = jev_decide(prompt, memory_context(state))
                private_ledger.emit("A0", "typed_decision", {"input": prompt, "response": response,
                                    "elapsed_ms": round((time.monotonic() - start) * 1000, 3)})
                ledger.emit("A0", "private_jev_call_completed", {"provider": "jev-latest",
                            "private_ledger_hash": file_hash(private / "jev_events.jsonl")})
                state["active_provider"] = "jev-latest"
            except Exception as exc:
                ledger.emit("A0", "phase_blocked", {"reason": sanitize_error(exc), "provider": "jev-latest"})
    else:
        ledger.emit("A0", "phase_blocked", {"reason": "JEV access not enabled or TYPESAFE_API_KEY missing"})
    baseline = snapshot(state)
    write_json(out / "substrate_state.json", state)
    frozen = out / "checkpoint_1.json"
    shutil.copyfile(out / "substrate_state.json", frozen)
    frozen_sha = file_hash(frozen)
    restored = json.loads(frozen.read_text())
    if snapshot(restored) != baseline:
        raise RuntimeError("checkpoint restore verification failed")
    ledger.emit("CHECKPOINT_1", "checkpoint_verified", {"sha256": frozen_sha,
                "restored_state_sha256": baseline, "restoration_equal": True})
    if phos_checkpoint and phos_checkpoint.is_file() and phos_url:
        checkpoint_sha = file_hash(phos_checkpoint)
        ledger.emit("B0", "checkpoint_verified", {"provider": "phos", "checkpoint_sha256": checkpoint_sha,
                    "source_path_basename": phos_checkpoint.name, "authenticity": "user_supplied_not_proven_by_hash"})
        try:
            prompt = "Please recall: " + memory_context(state)
            response = phos_generate(prompt, phos_url)
            ledger.emit("B0", "model_response", {"provider": "phos", "input": prompt,
                       "output": response.get("response"), "checkpoint_sha256": checkpoint_sha})
            state["active_provider"] = "phos"
        except Exception as exc:
            ledger.emit("B0", "phase_blocked", {"reason": sanitize_error(exc)})
    else:
        ledger.emit("B0", "phase_blocked", {"reason": "authentic PHOS checkpoint + local serving endpoint unavailable"})
    if training_command:
        # Never claim training from a command's exit status. A separately verified
        # model/validation receipt is required before B1 can be counted as completed.
        ledger.emit("B1", "phase_blocked", {"reason": "training integration requires verified trainer and held-out metric contract; command not executed"})
    else:
        ledger.emit("B1", "phase_blocked", {"reason": "authentic PHOS training not available"})
    ledger.emit("B2", "phase_blocked", {"reason": "no verified trained PHOS checkpoint"})
    # The post-swap fixture update is outside provider outputs and must not be
    # confused with successful PHOS dialogue, training, or Jev access.
    state["memory"].append({"id": 3, "content": "CANARY_GAMMA: recorded after attempted PHOS swap",
                            "origin": "independent_test_fixture"})
    state["state_counter"] += 1
    state["dyn12"][1] = 0.25
    write_json(out / "substrate_state.json", state)
    ledger.emit("A1", "independent_state_written", {"memory_count": 3, "state_counter": 2,
               "state_sha256": file_hash(out / "substrate_state.json"), "dyn12": state["dyn12"]})
    if enable_jev and os.getenv("TYPESAFE_API_KEY"):
        try:
            response = jev_decide("Classify whether the canary gamma was added post swap.", memory_context(state))
            private_ledger.emit("A1", "typed_decision", {"response": response,
                    "input": "Classify whether the canary gamma was added post swap."})
            ledger.emit("A1", "private_jev_call_completed", {"provider": "jev-latest",
                        "private_ledger_hash": file_hash(private / "jev_events.jsonl")})
        except Exception as exc:
            ledger.emit("A1", "phase_blocked", {"reason": sanitize_error(exc)})
    else:
        ledger.emit("A1", "phase_blocked", {"reason": "JEV reentry unavailable; no cross-provider context verification"})
    results = {}
    for kind in ("empty_memory", "shuffled_memory", "no_training", "independent_training"):
        result = check_control(restored, state, kind)
        results[kind] = result
        ledger.emit("CONTROL", "control_result", result)
    # Assert only the facts the local test actually measured.
    reloaded = json.loads((out / "substrate_state.json").read_text())
    continuity = {"storage_roundtrip": reloaded == state, "frozen_checkpoint_equal": snapshot(restored) == baseline,
                  "memory_count": len(reloaded["memory"]), "state_counter": reloaded["state_counter"],
                  "cross_provider_continuity": "NOT_MEASURED"}
    if not all((continuity["storage_roundtrip"], continuity["frozen_checkpoint_equal"])):
        raise RuntimeError("local continuity verification failed")
    ledger.emit("FINAL", "local_continuity_result", continuity)
    events = verify_ledger(out / "events.jsonl")
    checkpoint = {"checkpoint_1_sha256": frozen_sha, "checkpoint_1_state_sha256": baseline,
                  "final_state_sha256": file_hash(out / "substrate_state.json"), "verified": True}
    write_json(out / "continuity_checkpoints.json", checkpoint)
    for name, matches in (("training_metrics.jsonl", ("training_step",)),
                          ("model_swap_events.jsonl", ("provider_swapped", "phase_blocked"))):
        (out / name).write_bytes(b"".join(canonical(e) + b"\n" for e in events if e["event_type"] in matches))
    lines = ["# Conversation transcript", "", "No model-generated conversation was measured in this run.",
             "JEV makes typed decisions, not generated dialogue. Private JEV responses, when authorized, are retained separately.", ""]
    for e in events:
        if e["event_type"] == "model_response":
            lines.extend((f"## {e['timestamp']} — {e['payload']['provider']}",
                          f"Input: {e['payload']['input']}", f"Output: {e['payload']['output']}", ""))
    (out / "conversation_transcript.md").write_text("\n".join(lines) + "\n")
    final = events[-1]
    write_json(out / "reproduction_manifest.json", {"run_id": run_id, "timestamp_utc": final["timestamp"],
               "python": sys.version.split()[0], "platform": sys.platform,
               "event_count": len(events), "last_event_hash": final["event_hash"],
               "checkpoint": checkpoint, "controls": results, "continuity": continuity,
               "mode": "offline fixture with attempted optional providers; not an executed JEV-PHOS-JEV swap"})
    (out / "experiment_summary.md").write_text(
        "# JEV × PHOS measured execution — partial\n\n"
        f"Run \`{run_id}\` at {final['timestamp']}. Ledger events: {len(events)}.\n\n"
        "**Executed:** independent substrate fixture; immutable checkpoint + restore; "
        "empty/shuffled memory controls; hash-chain validation.\n\n"
        "**Not established:** JEV/PHOS conversations, authentic PHOS training or weight improvement, "
        "cross-provider continuity, matched provider benchmarks. Check \`events.jsonl\` for each blocker.\n\n"
        "This is neither a screen recording nor a replay of a full model-swap experiment. "
        "Do not treat synthetic canary fixtures as observed model dialogue.\n")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--enable-jev", action="store_true")
    p.add_argument("--phos-checkpoint", type=Path)
    p.add_argument("--phos-url")
    p.add_argument("--training-command")
    v = sub.add_parser("verify")
    v.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.command == "run":
        print(run(args.out, enable_jev=args.enable_jev,
                  phos_checkpoint=args.phos_checkpoint, phos_url=args.phos_url,
                  training_command=args.training_command))
    else:
        events = verify_ledger(args.path / "events.jsonl")
        manifest = json.loads((args.path / "reproduction_manifest.json").read_text())
        if not events or events[-1]["event_hash"] != manifest["last_event_hash"]:
            raise SystemExit("manifest and ledger disagree")
        if file_hash(args.path / "checkpoint_1.json") != manifest["checkpoint"]["checkpoint_1_sha256"]:
            raise SystemExit("checkpoint digest mismatch")
        print(f"VERIFIED events={len(events)} checkpoint={manifest['checkpoint']['checkpoint_1_sha256']}")


if __name__ == "__main__":
    main()
