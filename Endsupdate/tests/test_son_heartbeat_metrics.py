import math


def test_distribution_metrics_identity_and_symmetry():
    from beastbox.son_heartbeat_metrics import tvd, jsd_bits, pairwise_matrix
    p = {'00000': .5, '11111': .5}
    q = {'00000': .5, '11111': .5}
    r = {'00000': 0, '11111': 1}
    assert tvd(p, q) == 0 and jsd_bits(p, q) == 0
    assert math.isclose(tvd(p, r), 0.5)
    assert math.isclose(jsd_bits(p, r), jsd_bits(r, p))
    m = pairwise_matrix({'A': p, 'B': r})
    assert m['tvd']['A']['B'] == m['tvd']['B']['A']


def test_normalize_counts_requires_shots():
    from beastbox.son_heartbeat_metrics import normalize_counts
    assert normalize_counts({'00000': 2048, '11111': 2048})['00000'] == 0.5


def test_ideal_gate_program_simulator_is_normalized():
    from beastbox.son_heartbeat_metrics import simulate_gate_program
    p = simulate_gate_program({'operations': []})
    assert abs(sum(p.values()) - 1.0) < 1e-12
    assert p['00000'] == 1.0
