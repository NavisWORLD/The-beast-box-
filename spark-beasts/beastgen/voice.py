"""Seeded creature voice parameters (synthesised in-browser by live/voice.js with WebAudio).

Everything comes from the beast's seed stream, its body/element/temperament and the recorded
quantum counts of its seed run:
  base pitch      body size (small -> high) x seeded detune
  style           chirp / purr / growl / trill / coo / beep, weighted by body, element, temperament
  formants        F1 from qubit-0 marginal, F2 from qubit-1 marginal (vowel colour / timbre)
  vowels          the run's top outcomes (as integers) pick the vowel sequence
  rhythm          bits of the top outcome: 1 = long syllable, 0 = short (padded from the seed hash
                  for runs with <5 bits, flagged in rhythm_source)
  vibrato, speed, contour, breathiness, waveform: seeded within style-specific ranges
No audio is generated here; the same parameters drive the browser synth, the demo-video audio
(rendered with OfflineAudioContext from the same JS) and the WAV samples.
"""
from __future__ import annotations

import hashlib

STYLES = ["chirp", "purr", "growl", "trill", "coo", "beep"]
SIZE = {"pup": 0.50, "fox": 0.52, "sprout": 0.45, "moth": 0.34, "axolotl": 0.46, "golem": 0.82, "dragonling": 0.64,
        "bird": 0.30, "fish": 0.40, "serpent": 0.58, "biped": 0.50}
STYLE_W = {  # body -> style weights
    "pup": dict(purr=3, chirp=2, coo=1, growl=1), "fox": dict(chirp=3, purr=2, trill=1), "sprout": dict(coo=3, chirp=2, trill=1),
    "moth": dict(coo=3, trill=2, chirp=2), "axolotl": dict(trill=3, coo=2, chirp=1), "golem": dict(growl=3, beep=2, purr=1),
    "dragonling": dict(growl=3, chirp=2, purr=1), "bird": dict(chirp=4, trill=3), "fish": dict(trill=3, coo=2, chirp=1),
    "serpent": dict(trill=2, purr=2, growl=1, coo=1), "biped": dict(chirp=2, coo=2, purr=1, beep=1)}
ELEMENT_W = {"machine": dict(beep=6), "ember": dict(growl=2, chirp=1), "umbral": dict(coo=2, purr=1), "crystal": dict(trill=2, chirp=1),
             "frost": dict(coo=2, trill=1), "radiant": dict(chirp=2, trill=1), "verdant": dict(chirp=1, coo=1), "grove": dict(purr=1, coo=1)}
TEMPER_W = {"Serene": dict(coo=1.5, purr=1), "Gentle": dict(purr=1.5, coo=1), "Fierce": dict(growl=2), "Bold": dict(growl=1, chirp=1),
            "Playful": dict(chirp=1.5, trill=1), "Curious": dict(chirp=1.5, trill=0.5), "Dreamy": dict(coo=2), "Steadfast": dict(purr=1, beep=0.5)}
# style -> (waveform weights, syllables/s range, vibrato Hz, vibrato cents, AM Hz, breath)
STYLE_P = {
    "chirp": (dict(sine=2, triangle=3), (6.0, 9.0), (6, 9), (20, 60), 0, (0.02, 0.10)),
    "purr":  (dict(triangle=2, sawtooth=1), (3.0, 4.6), (4, 6), (10, 30), (22, 30), (0.10, 0.25)),
    "growl": (dict(sawtooth=3, square=1), (2.8, 4.2), (4, 6), (20, 50), (30, 46), (0.12, 0.30)),
    "trill": (dict(sine=2, triangle=2), (4.5, 7.0), (14, 22), (90, 180), 0, (0.02, 0.10)),
    "coo":   (dict(sine=4, triangle=1), (2.6, 4.0), (4, 6), (15, 40), 0, (0.06, 0.18)),
    "beep":  (dict(square=3, triangle=1), (5.0, 8.0), (0, 0.01), (0, 1), 0, (0.0, 0.02)),
}
CONSONANTS = {"chirp": ["p", "t", "ch", "k", "pi"], "purr": ["mr", "r", "m", "pr"], "growl": ["gr", "r", "g", "hr"],
              "trill": ["tr", "l", "r", "tl"], "coo": ["w", "m", "h", "n"], "beep": ["b", "d", "bz", "t"]}
VOWELS = [("a", 800, 1200), ("e", 500, 1900), ("i", 320, 2500), ("o", 500, 900), ("u", 340, 800),
          ("ee", 300, 2700), ("aw", 650, 1000), ("ü", 300, 1700)]


class _S:
    def __init__(self, seed: str, label: str):
        self.seed, self.label, self.n = seed, label, 0

    def u(self) -> float:
        h = hashlib.sha256(f"{self.seed}:{self.label}:{self.n}".encode()).digest()
        self.n += 1
        return int.from_bytes(h[:8], "big") / 2**64

    def rng(self, lo, hi):
        return lo + (hi - lo) * self.u()

    def pick(self, w: dict):
        items, tot = list(w.items()), sum(w.values())
        x, acc = self.u() * tot, 0.0
        for k, v in items:
            acc += v
            if x < acc:
                return k
        return items[-1][0]


def derive_voice(seed: str, body: str, element: str, temperament: str, genes: dict, qf: dict, beh: dict) -> dict:
    V = _S(seed, "voice")
    w = {s: 0.2 for s in STYLES}
    for src in (STYLE_W.get(body, {}), ELEMENT_W.get(element, {}), TEMPER_W.get(temperament, {})):
        for k, v in src.items():
            w[k] += v
    style = V.pick(w)
    waves, sps, vib, cents, am, breath = STYLE_P[style]
    size = SIZE.get(body, 0.5) + 0.18 * (genes["chub"] - 0.5)
    base = 980 * 2 ** (-1.7 * size) * 2 ** (0.6 * (V.u() - 0.5))
    if style == "growl":
        base *= 0.72
    m = qf["marginals_measured"]
    m0, m1 = m[0], m[1 % len(m)]
    f1 = 300 + 550 * m0 + 80 * (V.u() - 0.5)
    f2 = 950 + 1500 * m1 + 200 * (V.u() - 0.5)
    tops = sorted(qf.get("counts_top", []) or [qf["top_state"]])
    vowel_seq = [int(b, 2) % len(VOWELS) for b in (qf.get("counts_top") or [qf["top_state"]])][:4]
    if len(set(vowel_seq)) < 2:
        vowel_seq = vowel_seq + [int(seed[20 + 2 * i:22 + 2 * i], 16) % len(VOWELS) for i in range(3)]
        vowel_src = "top outcomes + seed-hash (run has few distinct outcomes)"
    else:
        vowel_src = "top outcomes of the run"
    rhythm = [int(b) for b in reversed(qf["top_state"])][:8]
    rsrc = "top_state bits"
    if len(rhythm) < 5:
        sb = bin(int(seed[24:32], 16))[2:].zfill(32)
        rhythm = rhythm + [int(c) for c in sb[:5 - len(rhythm)]]
        rsrc = "top_state bit + seed-hash padding (1-bit run)"
    cons = CONSONANTS[style][:]
    k0 = int(V.u() * len(cons))
    cons = cons[k0:] + cons[:k0]
    del tops
    return {
        "style": style,
        "base_pitch_hz": round(base, 1),
        "formants_hz": [round(f1), round(f2)],
        "formant_q": round(V.rng(4.0, 9.0), 2),
        "wave": V.pick(waves),
        "brightness": round(V.rng(0.2, 0.9), 3),
        "breath": round(V.rng(*breath), 3),
        "speed_sps": round(V.rng(*sps), 2),
        "vibrato_hz": round(V.rng(*vib), 2),
        "vibrato_cents": round(V.rng(*cents), 1),
        "am_hz": round(V.rng(*am), 1) if am else 0,
        "contour": V.pick({"rise": 1, "fall": 1, "arch": 1.3, "bounce": 1}),
        "jump_semitones": round(V.rng(2.0, 7.0), 2),
        "rhythm": rhythm, "rhythm_source": rsrc,
        "vowels": [VOWELS[i][0] for i in vowel_seq], "vowel_formants": [[VOWELS[i][1], VOWELS[i][2]] for i in vowel_seq],
        "vowel_source": vowel_src,
        "consonants": cons,
        "phrase_syllables": [2 + int(V.u() * 2), 3 + int(V.u() * 3)],
        "gain": round(V.rng(0.55, 0.85), 3),
        "prng_seed": int(seed[32:40], 16),
        "chattiness": beh["chattiness"],
    }
