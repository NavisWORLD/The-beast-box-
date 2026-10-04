"""Bridge to Beast Box 12D -> 54D math.

Uses, unmodified:
  beastbox.quantum_lifesource.packets_to_dyn12
  beastbox.quantum_lifesource.mirror_step
  beastbox.state_family.StateFamily
  beastbox.dyn12.gaussian_affinity
"""
from __future__ import annotations

import math

from beastbox.dyn12 import gaussian_affinity
from beastbox.quantum_lifesource import mirror_step, packets_to_dyn12
from beastbox.state_family import StateFamily

PAIRS = ((0, 1), (2, 3), (4, 0))


def pairs_for(nb: int) -> tuple:
    """Bit pairs for the three 4-outcome packets, for any register width."""
    if nb >= 6:
        return ((0, 1), (2, 3), (4, 5))
    if nb == 5:
        return PAIRS
    return tuple((a % nb, b % nb) for a, b in PAIRS)


def bit(bitstring: str, i: int) -> int:
    """Qiskit convention: classical bit 0 is the rightmost character."""
    return int(bitstring[-1 - i])


def quantum_features(counts: dict[str, int]) -> dict:
    shots = sum(counts.values())
    nb = len(next(iter(counts)))
    packets = []
    for a, b in pairs_for(nb):
        c = {"00": 0, "01": 0, "10": 0, "11": 0}
        for k, n in counts.items():
            c[f"{bit(k, b)}{bit(k, a)}"] += n
        packets.append({"counts": c, "shots": shots})
    q12 = packets_to_dyn12(packets)
    marg_nb = [sum(n for k, n in counts.items() if bit(k, i)) / shots for i in range(nb)]
    marg = [marg_nb[i % nb] for i in range(max(5, nb))]
    probs = [n / shots for n in counts.values()]
    entropy = -sum(p * math.log2(p) for p in probs if p > 0) / nb
    top = max(sorted(counts), key=lambda k: counts[k])
    counts_top = sorted(counts, key=lambda k: (-counts[k], k))[:4]
    return {
        "q12": q12,
        "marginals": marg,
        "marginals_measured": marg_nb,
        "num_bits": nb,
        "entropy_norm": entropy,
        "top_state": top,
        "counts_top": counts_top,
        "top_frac": counts[top] / shots,
        "packets": packets,
    }


def signal_vector(traits: dict[str, int]) -> list[float]:
    f, c, s = traits["focus"] / 100, traits["calm"] / 100, traits["spark"] / 100
    r = max(0.0, 1.0 - f - c - s)
    v = [
        f, c, s, r, f - c, s - c, f - s, 4 * f * c, 4 * c * s, 4 * s * f,
        math.sin(2 * math.pi * f + c), math.cos(2 * math.pi * s + c),
    ]
    return [max(-1.0, min(1.0, x)) for x in v]


def fuse(traits: dict[str, int], qf: dict, steps: int = 9) -> dict:
    s12 = signal_vector(traits)
    qdrive = [max(-1.0, min(1.0, (p - 0.25) * 6.0)) for p in qf["q12"]]
    mir = mirror_step(s12, qdrive)
    fam = StateFamily()
    for i in range(steps):
        fam.update(mir["coupled_drive"] if i % 3 else s12)
    st = fam.as_dict()
    return {
        "signal12": s12,
        "quantum_drive12": qdrive,
        "coupled12": mir["coupled_drive"],
        "dyn12": st["dyn12"],
        "dyn54": st["dyn54"],
    }
