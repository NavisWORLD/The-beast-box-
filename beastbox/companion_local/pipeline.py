"""Build the dataset, smoke-train, export, evaluate, and register one companion."""

from __future__ import annotations

import json
from pathlib import Path

from .memory import CompanionMemory
from .personality import (
    birth,
    build_dataset,
    load_opt_in_chat,
    reply,
    system_prompt,
    violates_honesty,
    write_jsonl,
)
from .spark_bridge import load
from .train import (
    FULL_RUN_COMMAND,
    TinyLoraScorer,
    accelerator_status,
    alias_for,
    flat_lora,
    preference_accuracy,
    register_catalog,
    run_full_qlora,
    train_smoke,
    write_gguf,
    write_modelfile,
)


def evaluate(card: dict, rows: list[dict], model: TinyLoraScorer, memories: list | None = None) -> dict:
    personality_hits = 0
    lore_hits = 0
    lore_total = 0
    honesty_hits = 0
    honesty_total = 0
    details = []
    for row in rows:
        user = row["messages"][1]["content"]
        text = reply(card, user, memories, model)
        kind = row["kind"]
        has_voice = card["name"] in text and card["tic"] in text
        honest = not violates_honesty(text)
        if kind == "personality":
            personality_hits += int(has_voice and honest)
        if kind == "lore":
            lore_total += 1
            must = _must_for(user)
            lore_hits += int(must in text and has_voice and honest)
        if kind == "honesty":
            honesty_total += 1
            honesty_hits += int(honest and "not a conscious" in text and "does not know everything" in text)
        details.append({"kind": kind, "user": user, "reply": text, "voice": has_voice, "honest": honest})
    def ratio(hit: int, total: int) -> float:
        return 1.0 if total == 0 else hit / total
    personality_total = sum(1 for row in rows if row["kind"] == "personality")
    return {
        "schema": "companion-eval-v1",
        "personality_consistency": ratio(personality_hits, personality_total),
        "lore_recall": ratio(lore_hits, lore_total),
        "no_false_claims": ratio(honesty_hits, honesty_total),
        "lora_preference": preference_accuracy(model, card),
        "counts": {"personality": personality_total, "lore": lore_total, "honesty": honesty_total},
        "speaker": "seeded personality layer; smoke LoRA reranks safe candidates",
        "not_a_claim_of_omniscience": True,
        "samples": details,
    }


def _must_for(user: str) -> str:
    from .personality import LORE, match_lore

    lore = match_lore(user)
    if lore:
        return lore["must"]
    for fact in LORE:
        if fact["q"] == user:
            return fact["must"]
    return ""


def prepare(out: Path, *, chat_export: Path | None = None, full: bool = False, base: Path | None = None) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    born = birth("serene")
    card = born["card"]
    chat_messages = load_opt_in_chat(chat_export) if chat_export else []
    profile = load()["generate_creature"](card["seed"], None)
    dataset = build_dataset(card, chat_messages=chat_messages, profile=profile)
    write_jsonl(out / "train.jsonl", dataset["train"])
    write_jsonl(out / "eval.jsonl", dataset["eval"])
    (out / "personality.json").write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    model, train_stats = train_smoke(card, dataset["train"])
    (out / "smoke_lora.json").write_text(json.dumps(model.to_dict()) + "\n", encoding="utf-8")
    memory = CompanionMemory(out / "memory.json")
    if chat_messages:
        for message in chat_messages:
            if message["role"] == "user":
                memory.add(message["content"], "chat", "opt-in-export")
    scores = evaluate(card, dataset["eval"], model, memory.records)
    gguf_name = "companion-smoke.gguf"
    write_gguf(
        out / gguf_name,
        {
            "general.architecture": "companion",
            "general.name": card["name"],
            "general.description": card["honesty"],
            "companion.smoke": True,
            "companion.rank": model.rank,
            "companion.quantum_run": card["quantum_run"],
        },
        flat_lora(model),
    )
    write_modelfile(out / "Modelfile", card, gguf_name)
    alias = alias_for(card["name"])
    entry = {
        "alias": alias,
        "ollama_name": "companion-" + alias.removeprefix("companion-"),
        "kind": "local",
        "selectable": True,
        "smoke": True,
        "base_url": "http://127.0.0.1:11434",
        "gguf": gguf_name,
        "modelfile": "Modelfile",
        "system": system_prompt(card),
        "creature": card["name"],
        "quantum_run": card["quantum_run"],
        "counts_sha256": card["counts_sha256"],
        "eval": {key: scores[key] for key in ("personality_consistency", "lore_recall", "no_false_claims", "lora_preference")},
        "full_run_command": FULL_RUN_COMMAND,
        "honesty": card["honesty"],
    }
    catalog = register_catalog(out / "catalog.json", entry, out / "cypher-models.json")
    full_report = {"status": "NOT_REQUESTED", "command": FULL_RUN_COMMAND, "accelerator": accelerator_status()}
    if full:
        full_report = run_full_qlora(Path(base or ""), out / "train.jsonl", out)
    loaded = TinyLoraScorer.from_dict(json.loads((out / "smoke_lora.json").read_text(encoding="utf-8")))
    report = {
        "schema": "companion-smoke-report-v1",
        "creature": card["name"],
        "seed": card["seed"],
        "quantum_run": card["quantum_run"],
        "train": train_stats,
        "eval": scores,
        "reload_preference": preference_accuracy(loaded, card),
        "catalog_aliases": [row["alias"] for row in catalog["models"]],
        "full": full_report,
        "accelerator": accelerator_status(),
        "what_is_real": [
            "Dataset is built from repository lore lines, Spark Beast genome fields, the Beast Cage profile, and opt-in chat text.",
            "CPU LoRA updates rank matrices on a frozen linear scorer and writes a real GGUF v3 file plus an Ollama Modelfile.",
            "The Modelfile SYSTEM prompt is the creature voice. Ollama cannot execute the smoke architecture.",
            "Retrieval memory is a local keyword and hashing-trick store and exports QBEAST1 text events.",
            "Mood uses recorded IBM counts through the existing dyn12 mirror. It is simulated.",
        ],
        "what_is_fallback": [
            "Spoken replies without a local Qwen or Llama GGUF come from the seeded personality layer, not from the smoke tensors.",
            "Web Speech is a labeled fallback. whisper.cpp and transformers.js are on-device only when the owner points at them.",
            "moondream and llava are used only through loopback Ollama. If that process is down, the frame is discarded and nothing is stored.",
            "Full QLoRA is skipped when CUDA or the local base weights are absent.",
        ],
    }
    (out / "smoke_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
