"""Spark Beasts: recorded-run integrity, deterministic genomes, QBEAST1 round trip."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPARK = ROOT / "spark-beasts"
sys.path.insert(0, str(SPARK))

from beastgen.genome import build_genome  # noqa: E402
from beastgen.runs import load_runs, load_table  # noqa: E402
from beastgen.signal import simulate_stable, simulate_windows, stabilize  # noqa: E402
from qbeast_file import build_qbeast, load_qbeast, serialize_qbeast  # noqa: E402

PUBLIC_RUNS = ROOT / "apps" / "beastbox-cloud" / "public" / "spark" / "runs.json"
GOLDEN = SPARK / "golden" / "case.json"


def test_recorded_table_is_compact_and_hashed():
    table = load_table()
    assert table["schema"] == "spark-beasts-quantum-runs-compact-v1"
    assert table["totals"]["entries"] == 5580
    assert table["totals"]["unique_jobs"] == 171
    assert PUBLIC_RUNS.read_bytes() == (SPARK / "data" / "quantum_runs.compact.json").read_bytes()
    runs = load_runs()
    assert len(runs) == 5580
    assert len({(run["job_id"], run["pub_index"], run["key"]) for run in runs}) == 5580
    assert {run["backend"] for run in runs} <= {"ibm_fez", "ibm_kingston", "ibm_marrakesh", "ibm_torino"}
    assert sum(run["num_bits"] == 1 for run in runs) == 5184


def test_same_inputs_same_beast_and_inputs_change_it():
    run = next(item for item in load_runs() if item["key"] == "ibm_marrakesh:d93d8pgoamcc73dc3afg")
    other = next(item for item in load_runs() if item["num_bits"] == 12)
    traits = {"focus": 40, "calm": 35, "spark": 20}
    first = build_genome(traits, run, "cory")
    second = build_genome(traits, run, "cory")
    assert first == second
    assert first["seed"] != build_genome(traits, other, "cory")["seed"]
    assert first["seed"] != build_genome(traits, run, "keeper")["seed"]
    assert len(first["engine"]["dyn12"]) == 12
    assert len(first["names"]) == 3


def test_bucket_absorbs_one_point_of_jitter():
    sessions = [stabilize(simulate_windows("balanced", 8, salt=f"s{i}")) for i in range(6)]
    assert sessions.count(sessions[0]) == 6
    stable = simulate_stable("balanced")
    run = next(item for item in load_runs() if item["num_bits"] == 5)
    assert build_genome(stable, run)["seed"] == build_genome(
        {"focus": stable["focus"], "calm": stable["calm"] + 1, "spark": stable["spark"]}, run
    )["seed"]


def test_qbeast_round_trip_matches_golden():
    cases = json.loads(GOLDEN.read_text())
    runs = {run["key"]: run for run in load_runs()}
    for case in cases:
        genome = build_genome(case["traits"], runs[case["run"]], case["user"])
        assert json.loads(json.dumps(genome)) == case["genome"]
        text = serialize_qbeast(build_qbeast(genome))
        assert text == case["qbeast"]
        loaded = load_qbeast(text)
        assert loaded["card"]["name"] == genome["names"][2]
        assert loaded["card"]["run"] == genome["inputs"]["quantum_run"]
        rebuilt = build_genome(loaded["card"]["traits"], runs[loaded["card"]["run"]], loaded["card"]["user_id"])
        assert rebuilt["seed"] == genome["seed"]
        assert json.loads(json.dumps(rebuilt)) == case["genome"]
        raw = json.loads(text)
        assert raw["format"] == "QBEAST1" and raw["version"] == 1
        assert raw["public_state"]["mode"] == "unavailable"
        assert raw["public_state"]["values"] == [0] * 12
        assert raw["progress"] == {"trust": 0, "bond": 0, "evolution_stage": 0}
