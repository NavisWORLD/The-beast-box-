"""QBEAST1 writer compatible with Living Universe arcade/lost-cosmos/qbeast.mjs.

The portable file is the public game snapshot (format QBEAST1, version 1).
Stats and the public id are rebuilt from the 64-character spark seed by the
same generator as packages/quantum-beast and mailbox.mjs. Host progress stays
at zero and the dyn12 projection is marked unavailable, so the file needs no
signature.

A single public memory event carries the spark card (traits, bucket, recorded
run key, stage-2 name). The in-game SPARK tab can read that card and rebuild
the same beast from the shipped runs table. Recorded counts are a seed source,
not a measured privileged projection.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

FAMILIES = ["nebula", "aurora", "void", "plasma", "memory", "signal", "starlight"]
FAMILY_LOOK = {
    "nebula": "nebula",
    "aurora": "aurora",
    "void": "nebula",
    "plasma": "starlight",
    "memory": "starlight",
    "signal": "aurora",
    "starlight": "starlight",
}
HUES = {"nebula": 0, "aurora": 0, "void": 83, "plasma": -92, "memory": 29, "signal": 45, "starlight": 0}
STAT_NAMES = [
    "hp", "energy", "signal", "memory", "resonance", "agility", "chaos", "stability", "curiosity", "evolution",
]
TRAIT_NAMES = ["curiosity", "energy", "playfulness", "caution", "independence"]
STEMS = ["Neb", "Lum", "Ori", "Vexa", "Astr", "Phera", "Glima", "Zori", "Mira", "Cosmi"]
ENDS = ["by", "io", "ix", "a", "on", "ora", "u", "ra", "yx", "iri"]
PRIVATE = re.compile(
    r"(?:api[_ -]?key|password|credential|authorization|biometric|owner[_ -]?memory|"
    r"private[_ -]?(?:key|state)|-----BEGIN|\bBearer\s|\bsk-[a-z0-9_-]{8,})",
    re.I,
)
CARD_RE = re.compile(
    r"^Spark Beasts v1\. Recorded quantum seed, game companion\. "
    r"traits=(\d+),(\d+),(\d+) bucket=(\d+) run=([A-Za-z0-9:_#-]+) name=([A-Za-z0-9]+)"
    r"(?: keeper=([A-Za-z0-9 ._-]{1,24}))?$"
)


def canonical(value) -> str:
    """Same canonical JSON as Living Universe qbeast.mjs and quantum-beast."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int):
        return json.dumps(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Invalid number")
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ",".join(canonical(item) for item in value) + "]"
    if isinstance(value, dict):
        parts = [json.dumps(key, ensure_ascii=False) + ":" + canonical(value[key]) for key in sorted(value)]
        return "{" + ",".join(parts) + "}"
    raise TypeError(type(value))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def hash_object(value) -> str:
    return hashlib.sha256(b"QBEAST1\0" + canonical(value).encode()).hexdigest()


def _u32(n: int) -> int:
    return n & 0xFFFFFFFF


def _i32(n: int) -> int:
    n &= 0xFFFFFFFF
    return n - 0x100000000 if n & 0x80000000 else n


def fnv1a(text: str) -> int:
    h = 2166136261
    for byte in text.encode():
        h ^= byte
        h = _u32(h * 16777619)
    return h


def _generator(seed: str, domain: str):
    state = fnv1a(f"1|{domain}|{seed}") or 0x6D2B79F5

    def nxt() -> float:
        nonlocal state
        state = _u32(_i32(state) ^ _i32(_i32(state) << 13))
        state = _u32(_i32(state) ^ (state >> 17))
        state = _u32(_i32(state) ^ _i32(_i32(state) << 5))
        return state / 4294967296

    return nxt


def stable_creature_id(seed: str) -> str:
    return "bb-" + f"{fnv1a(f'identity|1|{seed}'):08x}"


def generate_creature(seed: str, chosen_family: str | None = None) -> dict:
    if not isinstance(seed, str) or not 1 <= len(seed) <= 64:
        raise ValueError("Seed must have 1 to 64 characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in seed):
        raise ValueError("Control characters cannot be used as seeds")
    if chosen_family is not None and chosen_family not in FAMILIES:
        raise ValueError("Unknown family")
    art = _generator(seed, "appearance")
    stats_random = _generator(seed, "stats")
    traits_random = _generator(seed, "temperament")
    family = chosen_family or FAMILIES[int(art() * len(FAMILIES))]
    hue_shift = max(-180, min(180, HUES[family] + int(art() * 21) - 10))
    stats = {key: 50 for key in STAT_NAMES}
    for _ in range(270):
        source = int(stats_random() * len(STAT_NAMES))
        target = int(stats_random() * len(STAT_NAMES))
        if source != target and stats[STAT_NAMES[source]] > 20 and stats[STAT_NAMES[target]] < 80:
            stats[STAT_NAMES[source]] -= 1
            stats[STAT_NAMES[target]] += 1
    temperament = {key: int(20 + traits_random() * 61) for key in TRAIT_NAMES}
    naming = _generator(seed, "name")
    name = STEMS[int(naming() * len(STEMS))] + ENDS[int(naming() * len(ENDS))]
    profile = {
        "schema": "beast-cage-creature-v1",
        "version": 1,
        "id": stable_creature_id(seed),
        "seed": seed,
        "name": name,
        "family": family,
        "baseLook": FAMILY_LOOK[family],
        "appearance": {
            "hueShift": hue_shift,
            "glow": round(40 + art() * 60),
            "finPattern": int(art() * 4),
            "haloPattern": int(art() * 3),
            "constellation": int(art() * 65536),
        },
        "temperament": temperament,
        "game": {"stats": stats, "level": 1, "experience": 0},
        "provenance": "classical-seeded-game-generation",
    }
    if abs(profile["appearance"]["hueShift"]) > 127:
        raise ValueError("hue out of the portable range")
    return profile


def spark_summary(genome: dict) -> str:
    traits = genome["inputs"]["traits"]
    keeper = genome["inputs"].get("user_id") or ""
    text = (
        "Spark Beasts v1. Recorded quantum seed, game companion. "
        f"traits={traits['focus']},{traits['calm']},{traits['spark']} "
        f"bucket=10 run={genome['inputs']['quantum_run']} name={genome['names'][2]}"
    )
    if keeper:
        if not re.fullmatch(r"[A-Za-z0-9 ._-]{1,24}", keeper) or PRIVATE.search(keeper):
            raise ValueError("keeper name must be a short public label")
        text += f" keeper={keeper}"
    if len(text) > 256 or PRIVATE.search(text):
        raise ValueError("spark card is not public text")
    return text


def parse_spark_card(summary: str) -> dict:
    match = CARD_RE.fullmatch(summary)
    if not match:
        raise ValueError("spark card was not recognized")
    focus, calm, spark, bucket, run, name, keeper = match.groups()
    card = {
        "traits": {"focus": int(focus), "calm": int(calm), "spark": int(spark)},
        "bucket": int(bucket),
        "run": run,
        "name": name,
        "user_id": keeper,
    }
    if card["bucket"] != 10:
        raise ValueError("unsupported bucket")
    return card


def build_qbeast(genome: dict) -> dict:
    seed = genome["seed"]
    # validCreature regenerates with the stored family, which skips the family roll.
    family = FAMILIES[fnv1a("spark-family|" + seed) % len(FAMILIES)]
    profile = generate_creature(seed, family)
    public_state = {
        "schema": "dyn12-public-v1",
        "mode": "unavailable",
        "values": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "source_sha256": None,
    }
    progress = {"trust": 0, "bond": 0, "evolution_stage": 0}
    summary = spark_summary(genome)
    head = hash_object({"domain": "genesis", "profile": profile, "public_state": public_state, "progress": progress})
    event = {
        "generation": 1,
        "parent": head,
        "proposal_id": sha256_text("spark-proposal:" + seed),
        "kind": "memory",
        "payload": {"summary": summary, "source_ref": "public:spark-beasts"},
    }
    event["hash"] = hash_object({"domain": "event", **{k: v for k, v in event.items() if k != "hash"}})
    snapshot = {
        "format": "QBEAST1",
        "version": 1,
        "profile": profile,
        "public_state": public_state,
        "progress": progress,
        "events": [event],
        "generation": 1,
        "lineage_head": event["hash"],
        "digest": "0" * 64,
    }
    body = {k: v for k, v in snapshot.items() if k != "digest"}
    snapshot["digest"] = hash_object(body)
    return snapshot


def serialize_qbeast(snapshot: dict) -> str:
    return canonical(snapshot) + "\n"


def load_qbeast(text: str) -> dict:
    if len(text.encode()) > 524288:
        raise ValueError("Beast file is too large")
    snapshot = json.loads(text)
    if snapshot.get("format") != "QBEAST1" or snapshot.get("version") != 1:
        raise ValueError("Unsupported QBEAST format")
    digest = snapshot["digest"]
    body = {k: v for k, v in snapshot.items() if k != "digest"}
    if hash_object(body) != digest:
        raise ValueError("QBEAST digest mismatch")
    if snapshot["generation"] != len(snapshot["events"]):
        raise ValueError("Lineage was rejected")
    if snapshot["public_state"]["mode"] != "unavailable":
        raise ValueError("Measured projection is not accepted from Spark Beasts")
    if snapshot["progress"] != {"trust": 0, "bond": 0, "evolution_stage": 0}:
        raise ValueError("Host progress is not accepted without a pinned signing key")
    card = parse_spark_card(snapshot["events"][0]["payload"]["summary"])
    if snapshot["profile"]["seed"] != snapshot["profile"]["seed"]:
        raise ValueError("seed mismatch")
    expected = generate_creature(snapshot["profile"]["seed"], snapshot["profile"]["family"])
    if snapshot["profile"] != expected:
        raise ValueError("Game profile does not match the seed")
    return {"snapshot": snapshot, "card": card}
