#!/usr/bin/env python3
"""OMEGA-001 E4: self-correction from genuine, non-revealing verifier feedback.

For each of 30 synthetic two-step arithmetic problems (seed 4242), the model gives
an independent first answer. Then:
- verifier_feedback: a host checker compares the parsed integer with ground truth
  and, ONLY if wrong, says "Your answer is incorrect. Try again." (never the answer);
- sham_feedback: the same sentence after EVERY first answer, right or wrong.
Greedy decoding, pinned local checkpoints, no answer disclosure.
Preregistration: docs/experiments/OMEGA_001_PREREGISTRATION.md (E4).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.omega_model_independence_001 import PINS, sha_file  # noqa: E402

FEEDBACK = "Your answer is incorrect. Try again. End with the final answer as a single integer."
INSTRUCTION = "Solve the problem. Think briefly, then give the final answer as a single integer on the last line."
MAX_NEW = 160


def problems(seed: int = 4242, n: int = 30) -> list[dict]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        kind = i % 3
        a, b, c = rng.randint(3, 12), rng.randint(4, 15), rng.randint(2, 30)
        if kind == 0:
            text, answer = (f"A shop has {a} boxes with {b} pencils in each box. It sells {c} pencils. "
                            "How many pencils are left?"), a * b - c
        elif kind == 1:
            text, answer = (f"Mia reads {b} pages every day for {a} days, then reads {c} more pages. "
                            "How many pages did she read in total?"), a * b + c
        else:
            total = a * b + c
            text, answer = (f"There are {total} chairs. {c} chairs are removed and the rest are arranged "
                            f"in {a} equal rows. How many chairs are in each row?"), b
        out.append({"id": i, "text": text, "answer": answer})
    return out


def parse_int(text: str) -> int | None:
    found = re.findall(r"-?\d+", text.replace(",", ""))
    return int(found[-1]) if found else None


class Chat:
    def __init__(self, key: str, models: Path):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        repo, sub, sha = PINS[key]
        path = models / sub
        if sha_file(path / "model.safetensors") != sha:
            raise RuntimeError("pinned weights mismatch")
        self.torch = torch
        self.key, self.repo = key, repo
        self.tok = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(str(path), local_files_only=True,
                                                          torch_dtype=torch.float32).eval()

    def reply(self, messages: list[dict]) -> tuple[str, dict]:
        ids = self.tok.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt")
        started = time.perf_counter()
        with self.torch.inference_mode():
            out = self.model.generate(ids, max_new_tokens=MAX_NEW, do_sample=False,
                                      pad_token_id=self.tok.eos_token_id)
        text = self.tok.decode(out[0][ids.shape[-1]:], skip_special_tokens=True)
        return text, {"input_tokens": int(ids.shape[-1]), "output_tokens": int(out.shape[-1] - ids.shape[-1]),
                      "ms": round((time.perf_counter() - started) * 1000, 1)}


def run_model(chat: Chat, items: list[dict]) -> dict:
    rows = []
    for item in items:
        first_msgs = [{"role": "user", "content": f"{INSTRUCTION}\n\n{item['text']}"}]
        first, m1 = chat.reply(first_msgs)
        first_ok = parse_int(first) == item["answer"]
        second_msgs = first_msgs + [{"role": "assistant", "content": first},
                                    {"role": "user", "content": FEEDBACK}]
        # One generation serves both arms when the first answer is wrong: the message is identical.
        second, m2 = chat.reply(second_msgs)
        second_ok = parse_int(second) == item["answer"]
        rows.append({
            "id": item["id"], "answer": item["answer"],
            "first_parsed": parse_int(first), "first_correct": first_ok,
            "second_parsed": parse_int(second), "second_correct": second_ok,
            "verifier_final_correct": first_ok or second_ok,
            "sham_final_correct": second_ok,
            "first_output": first[-400:], "second_output": second[-400:], "metrics": [m1, m2],
        })
    n = len(rows)
    first_acc = sum(r["first_correct"] for r in rows)
    verifier = sum(r["verifier_final_correct"] for r in rows)
    sham = sum(r["sham_final_correct"] for r in rows)
    wrong_to_right = sum((not r["first_correct"]) and r["second_correct"] for r in rows)
    right_to_wrong_sham = sum(r["first_correct"] and not r["second_correct"] for r in rows)
    supported = verifier - first_acc >= 3 and sham < verifier
    return {"model": chat.repo, "n": n, "first_correct": first_acc, "verifier_final_correct": verifier,
            "sham_final_correct": sham, "wrong_to_right": wrong_to_right,
            "sham_right_to_wrong": right_to_wrong_sham,
            "verdict": "SUPPORTED" if supported else "NULL", "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import torch
    torch.set_num_threads(4)
    items = problems()
    report = {"schema": "omega-001-self-correction-v1", "feedback": FEEDBACK, "instruction": INSTRUCTION,
              "problems": items, "results": {}}
    for key in ("B", "C"):
        chat = Chat(key, args.models)
        started = time.perf_counter()
        report["results"][key] = run_model(chat, items)
        report["results"][key]["wall_s"] = round(time.perf_counter() - started, 1)
        del chat
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        r = report["results"][key]
        print(key, {k: r[k] for k in ("first_correct", "verifier_final_correct", "sham_final_correct",
                                      "wrong_to_right", "sham_right_to_wrong", "verdict")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
