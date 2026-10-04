"""Seed -> genome.

seed = SHA-256(canonical JSON of {schema, traits, quantum run identity + its full
measurement counts, optional user_id}).  All discrete choices come from labelled
SHA-256 sub-streams of that seed (no Python hash(), no global RNG), so the same
inputs give the same beast on any machine / Python version.
Continuous body genes blend the Beast Box engine state (dyn54) with the seed stream.
"""
from __future__ import annotations

import hashlib
import json
import math

from . import GENOME_SCHEMA, SEED_SCHEMA
from .engine import fuse, gaussian_affinity, quantum_features
from .signal import DEFAULT_BUCKET, validate
from .voice import derive_voice


def canon(v) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


class Stream:
    """Deterministic labelled random stream: SHA-256(seed:label:counter)."""

    def __init__(self, seed_hex: str, label: str):
        self.seed, self.label, self.n = seed_hex, label, 0

    def u(self) -> float:
        h = hashlib.sha256(f"{self.seed}:{self.label}:{self.n}".encode()).digest()
        self.n += 1
        return int.from_bytes(h[:8], "big") / 2**64

    def pick(self, items, weights=None):
        items = list(items)
        w = list(weights) if weights else [1.0] * len(items)
        x, acc = self.u() * sum(w), 0.0
        for it, wi in zip(items, w):
            acc += wi
            if x < acc:
                return it
        return items[-1]

    def rng(self, lo: float, hi: float) -> float:
        return lo + (hi - lo) * self.u()


# island -> archetype in (focus, calm, spark) space + art direction
ISLANDS = {
    "Eridoria Prime":     dict(arch=(0.33, 0.33, 0.30), element="verdant",
                               bodies={"sprout": 3, "pup": 2, "fox": 2, "biped": 2, "bird": 1, "golem": 1},
                               ears=["leaf", "pointy", "round"], tails=["leaf", "fluffy"], wings=["none", "none", "leaf"],
                               patterns=["spots", "moss", "belly", "stripes"]),
    "Hollow Verdance":    dict(arch=(0.15, 0.60, 0.05), element="grove",
                               bodies={"sprout": 2, "golem": 2, "pup": 1, "fox": 1, "biped": 2, "serpent": 1},
                               ears=["antlers", "leaf", "round"], tails=["leaf", "fluffy"], wings=["none", "none", "leaf"],
                               patterns=["moss", "spots", "stripes"]),
    "The Crown":          dict(arch=(0.50, 0.45, 0.05), element="radiant",
                               bodies={"pup": 2, "bird": 3, "fox": 2, "dragonling": 1, "moth": 1, "biped": 1},
                               ears=["pointy", "crown", "horns"], tails=["fluffy", "plume"], wings=["feather", "feather", "none"],
                               patterns=["belly", "stars", "stripes"]),
    "The Pale Expanse":   dict(arch=(0.05, 0.90, 0.02), element="frost",
                               bodies={"pup": 2, "axolotl": 1, "fish": 2, "bird": 1, "fox": 2, "serpent": 1},
                               ears=["round", "pointy", "crystal"], tails=["fluffy", "crystal"], wings=["none", "none", "crystal"],
                               patterns=["facets", "spots", "belly"]),
    "Rust Meridian":      dict(arch=(0.85, 0.10, 0.05), element="machine",
                               bodies={"golem": 3, "biped": 2, "pup": 1, "dragonling": 1, "fish": 1},
                               ears=["antenna", "bolts", "pointy"], tails=["cable", "gear"], wings=["none", "none", "vanes"],
                               patterns=["circuits", "plates", "stripes"]),
    "Cinder Drift":       dict(arch=(0.40, 0.03, 0.50), element="ember",
                               bodies={"dragonling": 3, "pup": 2, "fox": 2, "serpent": 1, "biped": 1},
                               ears=["flame", "pointy", "horns"], tails=["flame"], wings=["none", "bat", "flame"],
                               patterns=["cracks", "stripes"]),
    "Umbral Deep":        dict(arch=(0.05, 0.15, 0.05), element="umbral",
                               bodies={"moth": 3, "dragonling": 2, "serpent": 1, "fish": 1, "sprout": 1},
                               ears=["feelers", "round", "horns"], tails=["fluffy", "none"], wings=["moth", "bat"],
                               patterns=["stars", "spots"]),
    "The Shattered Reef": dict(arch=(0.10, 0.40, 0.45), element="crystal",
                               bodies={"axolotl": 3, "fish": 3, "serpent": 2, "moth": 1},
                               ears=["gills", "crystal"], tails=["fin", "crystal"], wings=["none", "crystal"],
                               patterns=["facets", "spots", "stars"]),
}
BODIES = ["pup", "fox", "sprout", "moth", "axolotl", "golem", "dragonling", "bird", "fish", "serpent", "biped"]
# which poses each body plan supports (seeded pick); art is drawn facing right then mirrored by `facing`
POSES = {"pup": ["front"], "sprout": ["front"], "moth": ["front"], "golem": ["front"], "biped": ["front", "three_quarter"],
         "axolotl": ["front"], "fox": ["three_quarter", "side"], "dragonling": ["three_quarter", "side"],
         "bird": ["three_quarter", "front"], "fish": ["side"], "serpent": ["side"]}

# HSV (deg, 0-1, 0-1): base, alt (secondary), belly, accent, glow
PALETTES = {
    "Eridoria Prime":     dict(base=(92, .55, .70), alt=(70, .55, .55), belly=(55, .30, .93), accent=(110, .60, .55), glow=(46, .85, 1.0)),
    "Hollow Verdance":    dict(base=(135, .50, .50), alt=(28, .50, .45), belly=(95, .35, .78), accent=(150, .55, .38), glow=(165, .70, .95)),
    "The Crown":          dict(base=(48, .18, .97), alt=(44, .70, .92), belly=(50, .08, 1.0), accent=(42, .75, .90), glow=(48, .80, 1.0)),
    "The Pale Expanse":   dict(base=(200, .22, .97), alt=(205, .40, .85), belly=(195, .06, 1.0), accent=(190, .45, .95), glow=(185, .75, 1.0)),
    "Rust Meridian":      dict(base=(24, .62, .78), alt=(215, .12, .62), belly=(30, .25, .88), accent=(210, .10, .48), glow=(184, .80, 1.0)),
    "Cinder Drift":       dict(base=(10, .38, .42), alt=(355, .70, .55), belly=(20, .55, .55), accent=(15, .85, .85), glow=(36, .95, 1.0)),
    "Umbral Deep":        dict(base=(272, .42, .72), alt=(285, .35, .55), belly=(270, .18, .92), accent=(265, .45, .82), glow=(48, .85, 1.0)),
    "The Shattered Reef": dict(base=(176, .48, .78), alt=(188, .55, .60), belly=(170, .20, .95), accent=(345, .40, .92), glow=(182, .85, 1.0)),
}

NAMES = {
    "Eridoria Prime":     ["Sprig", "Fern", "Clover", "Gild", "Thistle", "Bud", "Meadow", "Grove"],
    "Hollow Verdance":    ["Bark", "Root", "Glen", "Hollow", "Mire", "Yew", "Moss", "Bramble"],
    "The Crown":          ["Aur", "Sol", "Halo", "Regal", "Lumi", "Bright", "Gloria", "Crest"],
    "The Pale Expanse":   ["Frost", "Rime", "Glace", "Snow", "Hail", "Pale", "Shiver", "Floe"],
    "Rust Meridian":      ["Cog", "Rivet", "Ferro", "Bolt", "Gear", "Rust", "Volt", "Piston"],
    "Cinder Drift":       ["Ember", "Ash", "Cinder", "Scorch", "Pyre", "Char", "Magma", "Calder"],
    "Umbral Deep":        ["Moth", "Nyx", "Umbra", "Dusk", "Lun", "Shade", "Vesper", "Noct"],
    "The Shattered Reef": ["Glimmer", "Reef", "Prism", "Coral", "Shard", "Tide", "Lagoon", "Brine"],
}
SUFFIX = {
    1: {"default": ["ling", "pup", "kin", "let", "bun", "bit"], "moth": ["mite", "let", "fluff"], "axolotl": ["fin", "ling", "lotl"],
        "golem": ["bot", "nub", "ling"], "sprout": ["ling", "bud", "sprout"], "fox": ["kit", "ling", "pip"], "dragonling": ["wyrm", "let", "scale"],
        "bird": ["chick", "pip", "fledge"], "fish": ["fry", "fin", "bub"], "serpent": ["noodle", "ling", "coil"], "biped": ["kin", "tot", "bit"]},
    2: {"default": ["paw", "fang", "hound", "strider", "tail"], "moth": ["moth", "flutter", "wisp"], "axolotl": ["shard", "fin", "newt"],
        "golem": ["guard", "frame", "fist"], "sprout": ["paw", "bloom", "puff"], "fox": ["fox", "tail", "vix"], "dragonling": ["drake", "wing", "claw"],
        "bird": ["wing", "plume", "crest"], "fish": ["fin", "gill", "ray"], "serpent": ["coil", "naga", "slither"], "biped": ["walker", "scout", "kin"]},
    3: {"default": ["rex", "warden", "titan", "heart", "lord"], "moth": ["wing", "seraph", "veil"], "axolotl": ["leviath", "serpent", "drake"],
        "golem": ["colossus", "warden", "titan"], "sprout": ["warden", "heart", "elder"], "fox": ["kitsune", "warden", "regent"],
        "dragonling": ["dragon", "wyvern", "tyrant"], "bird": ["phoenix", "roc", "seraph"], "fish": ["leviath", "monarch", "tide"],
        "serpent": ["wyrm", "leviath", "naga"], "biped": ["knight", "sage", "warden"]},
}
TEMPERAMENTS = ["Serene", "Curious", "Fierce", "Dreamy", "Steadfast", "Playful", "Bold", "Gentle"]


def bucket_traits(traits: dict, bucket: int = DEFAULT_BUCKET) -> dict[str, int]:
    """Coarse rounding (default step 10) so EEG jitter of a few points doesn't re-roll the beast.
    Use signal.stabilize() first to take the median over several windows."""
    t = validate(traits)
    return {k: int(min(100, round(v / bucket) * bucket)) for k, v in t.items()} if bucket > 1 else t


def make_seed(traits: dict, run: dict, user_id: str | None = None, bucket: int = DEFAULT_BUCKET) -> tuple[str, dict]:
    t = validate(traits)
    material = {
        "schema": SEED_SCHEMA,
        "traits": {"schema": "cosmic-muse-traits-v1", **t},
        "stabilization": {"bucket": int(bucket)},
        "quantum": {"backend": run["backend"], "job_id": run["job_id"], "pub_index": run["pub_index"],
                    "shots": run["shots"], "counts": run["counts"]},
        "user_id": user_id,
    }
    return hashlib.sha256(canon(material)).hexdigest(), material


def _g(x: float) -> float:  # engine value (-1..1-ish) -> 0..1
    return 0.5 + 0.5 * math.tanh(2.5 * x)


GAITS = ["bob", "hop", "sway", "float", "wobble", "scuttle", "pulse"]
HABITS = ["look_around", "stretch", "turn_around", "double_hop", "doze_off", "shake", "sparkle_burst",
          "tail_flick", "peek", "spin_hop", "yawn", "sniff"]
QUIRKS = ["hiccups", "wanders", "shivers", "echo_bounce", "freezes_mid_beat", "counts_beats", "moonwalk", "startles"]
FLAVORS = {"calm": ["dozes", "melts", "purrs", "hums"], "focus": ["freezes", "tracks", "paces", "stares"],
           "spark": ["bounces", "zooms", "glitters", "spins"]}
CHANNELS = ("focus", "calm", "spark")


def behavior(seed: str, genes: dict, eng: dict, qf: dict, traits: dict, body: str, wings: str, tail: str) -> dict:
    """Movement + personality parameters, all derived from the seed / engine state / quantum run.

    No per-creature scripting: every beast goes through this same generic derivation; weights
    depend only on its own genes, its engine state and the recorded counts.
    """
    B = Stream(seed, "behavior")
    d54, c12 = eng["dyn54"], eng["coupled12"]
    gw = {"bob": 1.0, "hop": 0.4 + 1.6 * genes["legs"], "sway": 0.4 + 1.2 * genes["tail_size"] * (tail != "none"),
          "float": 0.15 + 2.2 * genes["wing_size"] * (wings != "none"), "wobble": 0.3 + 1.6 * genes["chub"],
          "scuttle": 0.3 + 1.2 * (1 - genes["legs"]), "pulse": 0.3 + 1.2 * genes["glow_amount"]}
    gait = B.pick(gw.keys(), gw.values())
    tempo = round(0.35 + 1.25 * (0.5 * _g(d54[31]) + 0.5 * B.u()) + 0.4 * traits["spark"] / 100, 3)  # beats / s
    accents = [int(b) for b in reversed(qf["top_state"])]  # the run's most frequent bitstring = rhythm accents
    accents_source = "top_state bits q0..q%d" % (len(accents) - 1)
    if len(accents) < 5:  # 1-bit runs: pad with seed-hash bits (flagged; the run itself has too few bits)
        sb = bin(int(seed[8:16], 16))[2:].zfill(32)
        accents = accents + [int(c) for c in sb[:5 - len(accents)]]
        accents_source += " + seed-hash padding"
    accents = accents[:8]
    if not any(accents):
        accents = [1] + accents[1:]
    habit_w = [0.4 + B.u() for _ in HABITS]
    habits = []
    pool = list(zip(HABITS, habit_w))
    for _ in range(3):
        h = B.pick([p[0] for p in pool], [p[1] for p in pool])
        pool = [p for p in pool if p[0] != h]
        habits.append({"name": h, "every_s": round(B.rng(4.0, 13.0), 2)})
    quirks = []
    qpool = list(QUIRKS)
    for _ in range(1 + (B.u() < 0.55)):
        q = qpool.pop(int(B.u() * len(qpool)))
        quirks.append({"name": q, "every_s": round(B.rng(3.0, 11.0), 2), "strength": round(B.rng(0.4, 1.0), 3)})
    raw = [0.3 + 0.7 * _g(d54[40 + 3 * i] + c12[4 * i]) + 0.9 * B.u() + 0.5 * qf["marginals"][i] for i in range(3)]
    tot = sum(raw)
    sens = {ch: round(3 * r / tot, 3) for ch, r in zip(CHANNELS, raw)}
    dominant = max(CHANNELS, key=lambda c: sens[c])
    return {
        "gait": gait, "tempo_hz": tempo, "amplitude_px": 1 + int(B.u() * 3), "swing": round(B.rng(0, 0.35), 3),
        "accents": accents, "accents_source": accents_source, "breath_hz": round(B.rng(0.12, 0.45), 3), "breath_px": 1 + int(B.u() < 0.35),
        "appendage_mul": round(B.rng(0.5, 3.0), 2), "appendage_px": 1 + int(B.u() < 0.4),
        "blink_mean_s": round(B.rng(1.6, 6.0), 2), "double_blink_p": round(B.rng(0, 0.5), 2),
        "habits": habits, "quirks": quirks,
        "sensitivity": sens, "reacts_most_to": dominant,
        "thresholds": {ch: int(B.rng(25, 60)) for ch in CHANNELS},
        "latency_s": round(B.rng(0.2, 1.2), 2),
        "flavors": {ch: B.pick(FLAVORS[ch]) for ch in CHANNELS},
        "chattiness": round(B.rng(0.25, 1.0), 2),
        "tic": None,
        "prng_seed": int(seed[:8], 16),
    }


def build_genome(traits: dict, run: dict, user_id: str | None = None, bucket: int = DEFAULT_BUCKET) -> dict:
    t = bucket_traits(traits, bucket)
    seed, _ = make_seed(t, run, user_id, bucket)
    qf = quantum_features(run["counts"])
    eng = fuse(t, qf)
    d54 = eng["dyn54"]
    S = lambda label: Stream(seed, label)  # noqa: E731

    # Island: engine affinity between the user's trait point and each archetype, sharpened,
    # then sampled with the seed stream (signal sets tendency; recorded quantum seed rolls).
    tp = (t["focus"] / 100, t["calm"] / 100, t["spark"] / 100)
    aff = {k: gaussian_affinity(tp, v["arch"], sigma=0.28) for k, v in ISLANDS.items()}
    island = S("island").pick(aff.keys(), [a ** 2 + 0.02 for a in aff.values()])
    I = ISLANDS[island]

    body = S("body").pick(I["bodies"].keys(), I["bodies"].values())
    ears = S("ears").pick(I["ears"])
    tail = S("tail").pick(I["tails"])
    wings = "moth" if body == "moth" else S("wings").pick(I["wings"])
    if body == "axolotl":
        ears = "gills" if ears not in ("gills", "crystal") else ears
        tail = tail if tail in ("fin", "crystal") else "fin"
    if body == "dragonling":
        wings = "bat" if wings in ("none", "moth", "leaf", "feather") else wings
        ears = ears if ears in ("horns", "crown", "crystal", "flame", "antenna", "bolts") else "horns"
        tail = "spade" if tail in ("fluffy", "plume", "leaf", "none") else tail
    if body == "bird":
        wings = "feather" if wings not in ("crystal", "flame", "vanes") else wings
        tail = "plume" if tail in ("fluffy", "leaf", "none", "cable", "gear") else tail
    if body == "fish":
        wings, tail = "none", ("crystal" if tail == "crystal" else "fishtail")
    if body == "serpent":
        wings = "none" if wings in ("feather", "leaf", "moth", "vanes") else wings
        tail = tail if tail in ("crystal", "flame", "fin", "leaf") else "tip"
    pose = S("pose").pick(POSES[body])
    pattern = S("pattern").pick(I["patterns"])
    top = qf["top_state"]
    top_int = int(top, 2)
    if len(top) >= 5:
        pattern_variant, pv_source = top_int & 31, "top_state (low 5 bits)"
    else:  # 1-bit runs carry too little: chest glyph / pattern variant from the seed hash instead (flagged)
        pattern_variant, pv_source = (top_int + 2 * int(seed[16:18], 16)) & 31, "top_state bit + seed-hash bits"

    # continuous genes: engine dyn54 component blended with a seed draw
    genes = {}
    names = ["chub", "head", "legs", "ear_size", "tail_size", "wing_size", "eye_size", "eye_gap",
             "hue", "sat", "val", "pattern_density", "pattern_scale", "glow_amount"]
    gs = S("genes")
    for i, n in enumerate(names):
        genes[n] = round(0.55 * _g(d54[(i * 5) % 54]) + 0.45 * gs.u(), 4)

    f, c, s = tp
    glow_hue = "gold" if (s >= f and island not in ("The Pale Expanse", "The Shattered Reef")) else "cyan"
    if island in ("Cinder Drift", "The Crown", "Eridoria Prime"):
        glow_hue = "native"
    eye_style = S("eye").pick(["round", "sparkle", "sleepy", "round"], [3, 1 + 3 * s, 3 * c, 1])
    mouth = S("mouth").pick(["smile", "w", "fang", "open"], [3, 2, 1 + 3 * f, 1 + 2 * s])

    ts = S("temper")
    scores = {"Serene": c * 1.2, "Curious": (s + f) * 0.6, "Fierce": (f + s) * 0.7 - c, "Dreamy": 1 - (f + c + s),
              "Steadfast": (f + c) * 0.6, "Playful": (s + c) * 0.6, "Bold": f, "Gentle": c * 0.7 + 0.1}
    temperament = max(TEMPERAMENTS, key=lambda k: scores[k] + 0.25 * ts.u())

    # base stats (HP, ATK, DEF, SPD, SPARK) per stage; weights from signal + engine + quantum marginals
    m = qf["marginals"]
    w = [1 + c + 0.6 * _g(d54[3]) + m[0], 1 + f + 0.6 * _g(d54[7]) + m[1], 1 + c * 0.8 + 0.6 * _g(d54[11]) + m[2],
         1 + (f + s) * 0.6 + 0.6 * _g(d54[17]) + m[3], 1 + s * 1.2 + 0.6 * _g(d54[23]) + m[4]]
    stats = {}
    for stage, total in ((1, 180), (2, 300), (3, 440)):
        v = [round(total * wi / sum(w)) for wi in w]
        stats[stage] = dict(zip(["hp", "atk", "def", "spd", "spark"], v))

    ns = S("names")
    pool = list(NAMES[island])
    stage_names = {}
    for stage in (1, 2, 3):
        pre = pool.pop(int(ns.u() * len(pool)))
        suf_pool = SUFFIX[stage].get(body, SUFFIX[stage]["default"])
        suf = suf_pool[int(ns.u() * len(suf_pool))]
        nm = pre + suf
        nm = nm.replace("ll" + "l", "ll")
        stage_names[stage] = nm[0].upper() + nm[1:]

    beh = behavior(seed, genes, eng, qf, t, body, wings, tail)
    voice = derive_voice(seed, body, I["element"], temperament, genes, qf, beh)
    nm1 = stage_names[1]
    beh["tic"] = (nm1[:2] + nm1[2:5].lower().strip("aeiou")[:1] or nm1[:3]).lower() + S("tic").pick(["!", "~", "?", "..."])
    return {
        "schema": GENOME_SCHEMA,
        "seed": seed,
        "inputs": {"traits": t, "quantum_run": run["key"], "user_id": user_id},
        "quantum": {"backend": run["backend"], "job_id": run["job_id"], "pub_index": run["pub_index"],
                    "counts_sha256": run["counts_sha256"], "top_state": top, "top_state_int": top_int, "num_bits": qf["num_bits"],
                    "entropy_norm": round(qf["entropy_norm"], 4), "marginals": [round(x, 4) for x in qf["marginals_measured"]]},
        "engine": {"dyn12": [round(x, 5) for x in eng["dyn12"]], "island_affinity": {k: round(v, 4) for k, v in aff.items()}},
        "island": island, "element": I["element"], "body": body, "ears": ears, "tail": tail, "wings": wings,
        "pattern": pattern, "pattern_variant": pattern_variant, "pattern_variant_source": pv_source, "pose": pose, "eye_style": eye_style, "mouth": mouth, "glow": glow_hue,
        "facing": S("facing").pick(["right", "left"]),
        "temperament": temperament, "behavior": beh, "voice": voice, "genes": genes, "stats": stats, "names": stage_names,
    }
