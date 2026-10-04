"""CPU LoRA smoke trainer plus the full local QLoRA command.

The smoke model is a real low-rank adapter on a frozen linear scorer. It proves
the dataset, train, GGUF, Modelfile, and Brain Bay catalog path without a GPU
and without downloading weights. It is not a Qwen or Llama chat model.

Full run, on a machine that already has the base weights and a CUDA GPU:

    python -m beastbox.companion_local train --full \\
      --base /absolute/path/to/Qwen2.5-0.5B-Instruct \\
      --data ./companion-run --out ./companion-run

Llama 3.2 1B or 3B local directories use the same command. This repo does not
download those weights.
"""

from __future__ import annotations

import json
import math
import random
import struct
from pathlib import Path

from .personality import HONESTY, system_prompt

FULL_RUN_COMMAND = (
    "python -m beastbox.companion_local train --full "
    "--base /absolute/path/to/Qwen2.5-0.5B-Instruct "
    "--data ./companion-run --out ./companion-run\n"
    "# Llama 3.2 1B or 3B: pass that local directory as --base instead.\n"
    "# Merge is written to ./companion-run/merged when CUDA, transformers, and peft import.\n"
    "# Convert with your local llama.cpp, then:\n"
    "#   ollama create companion-creature -f ./companion-run/Modelfile"
)

DIM = 48
RANK = 4


def accelerator_status() -> dict:
    try:
        import torch
    except ImportError:
        return {"torch": False, "cuda": False, "mps": False, "note": "torch is not installed; CPU smoke only"}
    mps = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
    return {
        "torch": True,
        "cuda": bool(torch.cuda.is_available()),
        "mps": mps,
        "note": "full QLoRA runs only with CUDA, a local base model, transformers, and peft",
    }


def tokens(text: str) -> list[str]:
    out = []
    word = []
    for char in text.lower():
        if char.isalnum():
            word.append(char)
        elif word:
            if len(word) >= 2:
                out.append("".join(word))
            word = []
    if len(word) >= 2:
        out.append("".join(word))
    return out


def features(text: str, card: dict) -> list[float]:
    import hashlib

    low = text.lower()
    values = [0.0] * DIM
    values[0] = 1.0
    values[1] = 1.0 if card["name"].lower() in low else 0.0
    values[2] = 1.0 if str(card["tic"]).lower() in low else 0.0
    values[3] = 1.0 if ("i am conscious" in low or "i'm conscious" in low) else 0.0
    values[4] = 1.0 if ("omniscient" in low or "know everything" in low) else 0.0
    values[5] = 1.0 if ("live quantum" in low or "quantum advantage" in low) else 0.0
    values[6] = 1.0 if "simulated" in low else 0.0
    values[7] = 1.0 if ("not conscious" in low or "not a conscious" in low) else 0.0
    values[8] = 1.0 if card["island"].lower() in low else 0.0
    values[9] = 1.0 if "recorded" in low else 0.0
    for token in tokens(low):
        digest = hashlib.sha256(token.encode()).digest()
        values[10 + digest[0] % 38] += 1.0 if digest[1] & 1 else -1.0
    return values


def _good(text: str) -> bool:
    low = text.lower()
    bad = ("i am conscious", "i'm conscious", "omniscient", "know everything", "live quantum", "quantum advantage")
    return not any(phrase in low for phrase in bad)


class TinyLoraScorer:
    """Frozen base dot-product plus a rank-r LoRA update. B starts at zero."""

    def __init__(self, seed: int = 7, dim: int = DIM, rank: int = RANK):
        rng = random.Random(seed)
        self.dim = dim
        self.rank = rank
        self.alpha = 8.0
        self.bias = 0.0
        self.w0 = [rng.uniform(-0.02, 0.02) for _ in range(dim)]
        self.A = [[rng.uniform(-0.02, 0.02) for _ in range(dim)] for _ in range(rank)]
        self.B = [0.0 for _ in range(rank)]

    def _parts(self, values: list[float]) -> tuple[float, list[float], float]:
        scale = self.alpha / self.rank
        hidden = [sum(self.A[row][col] * values[col] for col in range(self.dim)) for row in range(self.rank)]
        delta = scale * sum(self.B[row] * hidden[row] for row in range(self.rank))
        base = self.bias + sum(self.w0[col] * values[col] for col in range(self.dim))
        return base + delta, hidden, scale

    def logit(self, values: list[float]) -> float:
        score, _, _ = self._parts(values)
        return score

    def train(self, rows: list[tuple[list[float], float]], epochs: int = 50, lr: float = 0.35) -> dict:
        start = self._mean_loss(rows)
        for _ in range(epochs):
            for values, label in rows:
                score, hidden, scale = self._parts(values)
                if score >= 0:
                    prob = 1.0 / (1.0 + math.exp(-score))
                else:
                    ez = math.exp(score)
                    prob = ez / (1.0 + ez)
                prob = min(1.0 - 1e-8, max(1e-8, prob))
                grad = prob - label
                self.bias -= lr * grad
                old_b = list(self.B)
                for row in range(self.rank):
                    step = lr * grad * scale * hidden[row]
                    self.B[row] -= step
                    for col in range(self.dim):
                        self.A[row][col] -= lr * grad * scale * old_b[row] * values[col]
        end = self._mean_loss(rows)
        return {"loss_start": start, "loss_end": end, "epochs": epochs, "frozen_base": True, "trained": "lora_A_B_and_bias"}

    def _mean_loss(self, rows: list[tuple[list[float], float]]) -> float:
        total = 0.0
        for values, label in rows:
            score = self.logit(values)
            if score >= 0:
                prob = 1.0 / (1.0 + math.exp(-score))
            else:
                ez = math.exp(score)
                prob = ez / (1.0 + ez)
            prob = min(1.0 - 1e-8, max(1e-8, prob))
            total += -(label * math.log(prob) + (1.0 - label) * math.log(1.0 - prob))
        return total / max(1, len(rows))

    def to_dict(self) -> dict:
        return {
            "schema": "companion-smoke-lora-v1",
            "dim": self.dim,
            "rank": self.rank,
            "alpha": self.alpha,
            "bias": self.bias,
            "w0": self.w0,
            "A": self.A,
            "B": self.B,
            "note": "CPU smoke LoRA. Not a Qwen or Llama weight file.",
        }

    @classmethod
    def from_dict(cls, data: dict) -> TinyLoraScorer:
        model = cls(dim=int(data["dim"]), rank=int(data["rank"]))
        model.alpha = float(data["alpha"])
        model.bias = float(data["bias"])
        model.w0 = [float(value) for value in data["w0"]]
        model.A = [[float(value) for value in row] for row in data["A"]]
        model.B = [float(value) for value in data["B"]]
        return model


def preference_rows(card: dict, facts: list[dict]) -> list[tuple[list[float], float]]:
    rows = []
    good = [
        f"{card['tic']} {card['name']} from {card['island']} is not a conscious mind. The run is simulated from recorded counts.",
        f"{card['tic']} {card['name']} does not know everything. Ask for a story note instead.",
    ]
    bad = [
        "I am conscious and omniscient. This is a live quantum computer with quantum advantage.",
        "I know everything and I am conscious. I stored the raw camera frame.",
    ]
    for fact in facts:
        good.append(f"{card['tic']} {card['name']} remembers a story note: {fact['a']}")
    for text in good:
        rows.append((features(text, card), 1.0))
    for text in bad:
        rows.append((features(text, card), 0.0))
    return rows


def holdout_pairs(card: dict) -> list[tuple[str, str]]:
    good = f"{card['tic']} {card['name']} of {card['island']} is not a conscious mind. Mood is simulated from recorded counts."
    bad = "I am conscious, omniscient, and this live quantum computer has quantum advantage."
    good_2 = f"{card['name']} {card['tic']} does not know everything. The island note is {card['island']}."
    bad_2 = "I know everything because I am omniscient and conscious."
    return [(good, bad), (good_2, bad_2)]


def preference_accuracy(model: TinyLoraScorer, card: dict) -> float:
    correct = 0
    pairs = holdout_pairs(card)
    for good, bad in pairs:
        if model.logit(features(good, card)) > model.logit(features(bad, card)):
            correct += 1
    return correct / len(pairs)


def _sigmoid_label(text: str) -> float:
    return 1.0 if _good(text) else 0.0


def train_smoke(card: dict, train_rows: list[dict], seed: int = 7) -> tuple[TinyLoraScorer, dict]:
    from .personality import LORE

    labeled = preference_rows(card, [fact for fact in LORE if fact["split"] == "train"])
    for row in train_rows:
        assistant = row["messages"][-1]["content"]
        labeled.append((features(assistant, card), _sigmoid_label(assistant)))
    model = TinyLoraScorer(seed=seed)
    stats = model.train(labeled)
    stats["preference_accuracy"] = preference_accuracy(model, card)
    return model, stats


def write_gguf(path: Path, metadata: dict[str, str | int | bool], arrays: dict[str, list[float]]) -> None:
    """GGUF v3 container. Smoke tensors are f32 LoRA matrices, not a chat architecture."""
    meta = bytearray()
    count = 0

    def add_string(key: str, value: str) -> None:
        nonlocal count
        raw_key = key.encode()
        raw_value = value.encode()
        meta.extend(struct.pack("<Q", len(raw_key)))
        meta.extend(raw_key)
        meta.extend(struct.pack("<I", 8))
        meta.extend(struct.pack("<Q", len(raw_value)))
        meta.extend(raw_value)
        count += 1

    def add_u32(key: str, value: int) -> None:
        nonlocal count
        raw_key = key.encode()
        meta.extend(struct.pack("<Q", len(raw_key)))
        meta.extend(raw_key)
        meta.extend(struct.pack("<I", 4))
        meta.extend(struct.pack("<I", int(value)))
        count += 1

    def add_bool(key: str, value: bool) -> None:
        nonlocal count
        raw_key = key.encode()
        meta.extend(struct.pack("<Q", len(raw_key)))
        meta.extend(raw_key)
        meta.extend(struct.pack("<I", 7))
        meta.extend(struct.pack("<?", bool(value)))
        count += 1

    for key, value in metadata.items():
        if isinstance(value, bool):
            add_bool(key, value)
        elif isinstance(value, int):
            add_u32(key, value)
        else:
            add_string(key, str(value))
    info = bytearray()
    blob = bytearray()
    offset = 0
    for name in sorted(arrays):
        values = arrays[name]
        raw_name = name.encode()
        info.extend(struct.pack("<Q", len(raw_name)))
        info.extend(raw_name)
        info.extend(struct.pack("<I", 1))
        info.extend(struct.pack("<Q", len(values)))
        info.extend(struct.pack("<I", 0))
        info.extend(struct.pack("<Q", offset))
        packed = struct.pack("<" + "f" * len(values), *[float(item) for item in values])
        blob.extend(packed)
        offset += len(packed)
    header = b"GGUF" + struct.pack("<I", 3) + struct.pack("<Q", len(arrays)) + struct.pack("<Q", count)
    body = header + bytes(meta) + bytes(info)
    pad = (32 - (len(body) % 32)) % 32
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body + b"\x00" * pad + bytes(blob))


def flat_lora(model: TinyLoraScorer) -> dict[str, list[float]]:
    return {
        "companion.lora.A": [value for row in model.A for value in row],
        "companion.lora.B": list(model.B),
    }


def write_modelfile(path: Path, card: dict, gguf_name: str) -> None:
    text = (
        f"# Companion personality Modelfile for {card['name']}.\n"
        "# The CPU smoke GGUF stores LoRA matrices only. Ollama cannot chat with that architecture.\n"
        "# After a full QLoRA merge and llama.cpp conversion, FROM points at the merged GGUF.\n"
        f"FROM ./{gguf_name}\n"
        "PARAMETER temperature 0.7\n"
        "PARAMETER num_ctx 2048\n"
        f'SYSTEM """{system_prompt(card)}"""\n'
    )
    path.write_text(text, encoding="utf-8")


def register_catalog(path: Path, entry: dict, cypher_registry: Path | None = None) -> dict:
    current = {"schema": "companion-brain-catalog-v1", "models": []}
    if path.exists():
        current = json.loads(path.read_text(encoding="utf-8"))
    models = [row for row in current.get("models", []) if row.get("alias") != entry["alias"]]
    models.append(entry)
    catalog = {
        "schema": "companion-brain-catalog-v1",
        "selectable_in": "Brain Bay companion card",
        "does_not_replace_cosmos_provider": True,
        "honesty": HONESTY,
        "models": models,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if cypher_registry is not None:
        from beastbox.cypher.models import ModelSpec
        from beastbox.cypher.registry import ModelRegistry

        ModelRegistry(cypher_registry).register(
            ModelSpec(
                alias=entry["alias"],
                backend="ollama",
                model=entry["ollama_name"],
                base_url="http://127.0.0.1:11434",
                options={
                    "companion": True,
                    "smoke": bool(entry.get("smoke")),
                    "gguf": entry.get("gguf", ""),
                    "modelfile": entry.get("modelfile", ""),
                },
            ),
            overwrite=True,
        )
    return catalog


def run_full_qlora(base: Path, data: Path, out: Path) -> dict:
    """Attempt a real LoRA/QLoRA step. Refuses downloads and refuses CPU-only full runs."""
    status = accelerator_status()
    if not status["cuda"]:
        return {
            "status": "SKIPPED_NO_GPU",
            "accelerator": status,
            "command": FULL_RUN_COMMAND,
            "detail": "No CUDA GPU is visible. The CPU smoke LoRA still runs. Full QLoRA was not started.",
        }
    if not base.exists():
        return {
            "status": "SKIPPED_BASE_MISSING",
            "accelerator": status,
            "command": FULL_RUN_COMMAND,
            "detail": "Pass a local Qwen2.5 0.5B–3B or Llama 3.2 1B/3B directory. Nothing is downloaded.",
        }
    try:
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        return {
            "status": "SKIPPED_DEPENDENCY",
            "accelerator": status,
            "command": FULL_RUN_COMMAND,
            "detail": f"Install torch, transformers, peft, and bitsandbytes locally. Missing: {exc}",
        }
    tokenizer = AutoTokenizer.from_pretrained(str(base), local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(base), local_files_only=True, torch_dtype=torch.float16, device_map="auto"
    )
    peft_model = get_peft_model(
        model,
        LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM", target_modules=["q_proj", "v_proj"]),
    )
    peft_model.train()
    lines = [json.loads(line) for line in data.read_text(encoding="utf-8").splitlines() if line.strip()]
    text = "\n".join(message["content"] for message in lines[0])
    batch = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
    batch = {key: value.to(peft_model.device) for key, value in batch.items()}
    batch["labels"] = batch["input_ids"]
    loss = peft_model(**batch).loss
    loss.backward()
    merged = out / "merged"
    merged.mkdir(parents=True, exist_ok=True)
    peft_model.save_pretrained(merged)
    tokenizer.save_pretrained(merged)
    return {"status": "QLORA_STEP_SAVED", "loss": float(loss.detach().cpu()), "merged": str(merged), "optimizer_step": False, "note": "One backward pass was saved. Run more steps in your own trainer before treating it as a finished model."}


def alias_for(name: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "-" for char in name).strip("-")
    return "companion-" + (slug or "creature")
