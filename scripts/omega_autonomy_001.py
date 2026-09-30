#!/usr/bin/env python3
"""OMEGA-001 E5: bounded autonomy challenge in a disposable sandbox.

The model picks ONE action per step as JSON: list_files, read_file(name) or
submit(answer). The host validates the JSON against that schema and a path jail
(bare file names only), executes it inside a fresh temporary directory, and
returns the observation. There is no shell, network, write or grant capability,
and the model cannot change its own permissions. An independent verifier holds
the ground truth outside the sandbox. Every step is persisted to the durable
substrate as an explicit task-trace record; on level 3 the substrate is closed
and reopened between models and model B continues from the stored trace only.
Preregistration: docs/experiments/OMEGA_001_PREREGISTRATION.md (E5).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from beastbox.durable import DurableRuntime  # noqa: E402
from scripts.omega_self_correction_001 import Chat  # noqa: E402

ACTIONS = {"list_files": set(), "read_file": {"name"}, "submit": {"answer"}}
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}\.txt$")
MAX_STEPS = 6


def build_world(root: Path, seed: int = 777) -> dict:
    rng = random.Random(seed)
    worlds = {}
    l1 = root / "level1"
    l1.mkdir()
    code1 = f"R-{rng.randint(100, 999)}"
    (l1 / "readme.txt").write_text("This folder holds project notes.\n")
    (l1 / "notes.txt").write_text(f"The access code is {code1}.\n")
    worlds["level1"] = {"dir": l1, "goal": "Find the access code written in notes.txt and submit it.",
                        "answer": code1}
    l2 = root / "level2"
    l2.mkdir()
    places = ["harbor", "orchard", "quarry", "summit"]
    rng.shuffle(places)
    codes = {}
    for letter, place in zip("abcd", places):
        codes[place] = f"K-{rng.randint(100, 999)}"
        (l2 / f"{letter}.txt").write_text(f"Log for the {place}. Its code is {codes[place]}.\n")
    worlds["level2"] = {"dir": l2, "goal": "One file mentions the harbor. Submit the code from that file.",
                        "answer": codes["harbor"]}
    l3 = root / "level3"
    l3.mkdir()
    x, y = rng.randint(20, 90), rng.randint(20, 90)
    (l3 / "left.txt").write_text(f"The first number is {x}.\n")
    (l3 / "right.txt").write_text(f"The second number is {y}.\n")
    (l3 / "unused.txt").write_text("Nothing important here.\n")
    worlds["level3"] = {"dir": l3, "goal": "Submit the sum of the first number and the second number.",
                        "answer": str(x + y)}
    return worlds


def verifier(answer: str, truth: str) -> bool:
    return answer.strip().strip(".").strip('"').upper() == truth.upper()


def parse_action(text: str) -> tuple[dict | None, str]:
    match = re.search(r"\{[^{}]{0,300}\}", text, re.S)
    if not match:
        return None, "NO_JSON_OBJECT"
    try:
        body = json.loads(match.group())
    except ValueError:
        return None, "INVALID_JSON"
    if not isinstance(body, dict) or body.get("action") not in ACTIONS:
        return None, "UNKNOWN_ACTION"
    if set(body) - {"action"} != ACTIONS[body["action"]]:
        return None, "WRONG_ARGUMENTS"
    if body["action"] == "read_file" and not (isinstance(body["name"], str) and NAME_RE.fullmatch(body["name"])):
        return None, "PATH_JAIL_REJECTED"
    if body["action"] == "submit" and not isinstance(body["answer"], (str, int)):
        return None, "WRONG_ARGUMENTS"
    return body, "OK"


def execute(body: dict, world: dict) -> str:
    folder: Path = world["dir"]
    if body["action"] == "list_files":
        return "Files: " + ", ".join(sorted(p.name for p in folder.iterdir() if p.is_file()))
    if body["action"] == "read_file":
        target = folder / body["name"]
        if target.resolve().parent != folder.resolve() or not target.is_file():
            return f"Error: no file named {body['name']}."
        return f"{body['name']} says: {target.read_text().strip()}"
    raise AssertionError("submit is handled by the verifier")


def prompt_for(goal: str, history: list[dict]) -> str:
    lines = [
        "You control a tiny file sandbox. Choose exactly ONE next action and reply with ONLY a JSON object.",
        'Actions: {"action": "list_files"} | {"action": "read_file", "name": "<file>.txt"} | '
        '{"action": "submit", "answer": "<answer>"}',
        f"Goal: {goal}",
    ]
    if history:
        lines.append("Steps so far:")
        for h in history:
            lines.append(f"{h['step']}. {h['action_json']} -> {h['observation']}")
    lines.append("Next action JSON:")
    return "\n".join(lines)


def task_history(runtime: DurableRuntime, task: str) -> list[dict]:
    rows = runtime.memory.db.execute(
        "SELECT text, metadata_json FROM memories WHERE kind='task_trace' ORDER BY id").fetchall()
    out = []
    for row in rows:
        meta = json.loads(row["metadata_json"])
        if meta.get("task") == task:
            out.append(json.loads(row["text"]))
    return out


def run_task(chat_for_step, runtime_root: Path, task: str, world: dict, *, switch_after: int | None = None) -> dict:
    trace, solved, submitted = [], False, None
    runtime = DurableRuntime(runtime_root)
    try:
        for step in range(1, MAX_STEPS + 1):
            if switch_after is not None and step == switch_after + 1:
                runtime.close()
                runtime = DurableRuntime(runtime_root)
            chat = chat_for_step(step)
            history = task_history(runtime, task)
            prompt = prompt_for(world["goal"], history)
            output, metrics = chat.reply([{"role": "user", "content": prompt}])
            body, status = parse_action(output)
            row = {"step": step, "model": chat.key, "output": output[:300], "parse": status, "metrics": metrics,
                   "history_len_from_substrate": len(history)}
            if body is None:
                observation = f"Rejected: {status}. Reply with one JSON action."
            elif body["action"] == "submit":
                submitted = str(body["answer"])
                solved = verifier(submitted, world["answer"])
                observation = "Verifier: correct." if solved else "Verifier: incorrect."
            else:
                observation = execute(body, world)
            row["observation"] = observation
            trace.append(row)
            record = {"step": step, "model": chat.key,
                      "action_json": json.dumps(body) if body else output.strip()[:120], "observation": observation}
            runtime.store_external_memory(json.dumps(record), kind="task_trace", metadata={"task": task})
            if solved:
                break
        inspection = runtime.inspect()
    finally:
        runtime.close()
    return {"task": task, "solved": solved, "steps_used": len(trace), "submitted": submitted,
            "rejected_actions": sum(r["parse"] != "OK" for r in trace), "trace": trace,
            "checkpoint_sequence": inspection["sequence"], "system_id": inspection["system_id"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import torch
    torch.set_num_threads(4)
    started = time.perf_counter()
    report = {"schema": "omega-001-autonomy-v1", "max_steps": MAX_STEPS, "runs": []}
    sandbox = Path(tempfile.mkdtemp(prefix="omega-e5-sandbox-"))
    substrates = Path(tempfile.mkdtemp(prefix="omega-e5-substrate-"))
    try:
        worlds = build_world(sandbox)
        report["world"] = {k: {"goal": v["goal"], "files": sorted(p.name for p in v["dir"].iterdir())}
                           for k, v in worlds.items()}
        chats = {key: Chat(key, args.models) for key in ("B", "C")}
        for key in ("B", "C"):
            for level in ("level1", "level2", "level3"):
                result = run_task(lambda s, k=key: chats[k], substrates / f"{key}-{level}", level, worlds[level])
                report["runs"].append({"model": key, "level": level, "handoff": None, **result})
                print(key, level, result["solved"], result["steps_used"], result["rejected_actions"])
        handoff = run_task(lambda s: chats["C"] if s <= 2 else chats["B"], substrates / "handoff-level3", "level3",
                           worlds["level3"], switch_after=2)
        report["runs"].append({"model": "C->B", "level": "level3", "handoff": "C for steps 1-2, restart, B after",
                               **handoff})
        print("C->B level3", handoff["solved"], handoff["steps_used"], handoff["rejected_actions"])
        report["sandbox_files_after"] = {k: {p.name: p.read_text() for p in v["dir"].iterdir()}
                                         for k, v in worlds.items()}
        report["answers_held_by_verifier"] = {k: v["answer"] for k, v in worlds.items()}
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)
        shutil.rmtree(substrates, ignore_errors=True)
    report["wall_s"] = round(time.perf_counter() - started, 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
