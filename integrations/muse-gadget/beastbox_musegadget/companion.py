"""In-character replies for `talk`, from the best local engine available.

Order: the Glacecoil Ollama model (``companion-glacecoil``) if it is installed
on this machine, then the repository's ``beastbox.companion_local`` personality
layer if a checkout is configured, then a small built-in template. Every reply
passes an honesty filter: the beast never claims to be conscious, all-knowing
or linked to a live quantum computer.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from beastbox_musegadget import HONESTY

FORBIDDEN = (
    "i am conscious", "i'm conscious", "i am sentient", "i'm sentient", "i am alive",
    "i am omniscient", "i know everything", "quantum advantage", "live quantum computer",
    "live quantum link", "i am a real person",
)
CATCHPHRASES = ["oh crumbs", "tiny beep", "hehe", "psst", "star crumb", "wiggle"]


def violates_honesty(text: str) -> bool:
    low = text.lower()
    return any(phrase in low for phrase in FORBIDDEN)


def card_for(summary: dict, beast: Optional[dict] = None) -> dict:
    genome = (beast or {}).get("genome") or {}
    behavior = genome.get("behavior") or {}
    seed = str(genome.get("seed") or summary.get("name") or "beast")
    pick = sum(seed.encode("utf-8")) % len(CATCHPHRASES)
    return {
        "name": summary.get("name") or "Beast",
        "body": summary.get("species") or "beast",
        "island": summary.get("island") or "the Lost Cosmos",
        "temperament": summary.get("temperament") or "Curious",
        "tic": behavior.get("tic") or "*wiggles*",
        "catchphrase": CATCHPHRASES[pick],
        "habit": "I ask a tiny question",
        "mood": summary.get("mood") or "idle",
    }


def system_prompt(card: dict) -> str:
    return (
        f"You are {card['name']}, a {str(card['temperament']).lower()} {card['body']} from "
        f"{card['island']} in The Beast Box game. You are currently feeling {card['mood']}. "
        f"Your tic is {card['tic']!r} and you like to say {card['catchphrase']!r}. "
        "Answer in one to three short, playful sentences. You are a small local game companion, "
        "not a person and not a conscious mind, and you do not know everything. Recorded IBM "
        "quantum counts are only a fixed seed for your classical simulation, not a live quantum link."
    )


FEELINGS = {"idle": "curious", "happy": "happy", "sleep": "a bit sleepy", "evolve": "extra sparkly"}


def fallback_reply(card: dict, message: str) -> str:
    text = message.strip().rstrip("?!.")
    hook = f"You said \u201c{text[:80]}\u201d" if text else "You said hi"
    feeling = FEELINGS.get(str(card.get("mood")), "curious")
    return (f"{card['tic']} {card['name']} the {str(card['temperament']).lower()} {card['body']} "
            f"perks up. {card['catchphrase'].capitalize()}! {hook}, and I'm feeling {feeling}. "
            "Want to play a tiny game?")


def _ollama_has(host: str, model: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=timeout) as response:
            tags = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return False
    names = {str(m.get("name", "")) for m in tags.get("models", []) if isinstance(m, dict)}
    return model in names or f"{model}:latest" in names


def ollama_reply(host: str, model: str, card: dict, message: str, timeout: float = 40.0) -> Optional[str]:
    if not _ollama_has(host, model):
        return None
    body = json.dumps({
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt(card)},
            {"role": "user", "content": message[:800]},
        ],
        "options": {"num_predict": 120},
    }).encode("utf-8")
    request = urllib.request.Request(host.rstrip("/") + "/api/chat", data=body,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return None
    text = ((data.get("message") or {}).get("content") or "").strip()
    return text or None


def companion_local_reply(repo: str, beast: Optional[dict], card: dict, message: str) -> Optional[str]:
    """Use beastbox.companion_local.personality from a local checkout, if present."""
    if not repo or not Path(repo, "beastbox", "companion_local", "personality.py").is_file():
        return None
    if repo not in sys.path:
        sys.path.insert(0, repo)
    try:
        from beastbox.companion_local import personality  # type: ignore
    except Exception:
        return None
    genome = (beast or {}).get("genome") or {}
    try:
        local_card = personality.personality_from_genome(genome)
    except Exception:
        local_card = {**card, "honesty": HONESTY}
    try:
        return str(personality.reply(local_card, message))
    except Exception:
        return None


def reply(cfg, summary: dict, beast: Optional[dict], message: str) -> dict:
    card = card_for(summary, beast)
    engines = (
        ("ollama:" + cfg.companion_model, lambda: ollama_reply(cfg.ollama_host, cfg.companion_model, card, message)),
        ("beastbox.companion_local", lambda: companion_local_reply(cfg.beastbox_repo, beast, card, message)),
    )
    for name, engine in engines:
        text = engine()
        if text:
            if violates_honesty(text):
                text = (f"{card['tic']} {card['name']} is a small game companion, not a conscious mind, "
                        "and my sparkle comes from recorded IBM counts used as a fixed seed, not a live quantum link.")
            return {"reply": text, "engine": name}
    return {"reply": fallback_reply(card, message), "engine": "built-in template (no local model found)"}
