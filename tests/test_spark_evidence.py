import importlib.util, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("spark_evidence", ROOT / "scripts/spark_evidence.py")
se = importlib.util.module_from_spec(spec)
spec.loader.exec_module(se)


def artifact(tmp_path):
    a = tmp_path / "art"
    (a / "alice").mkdir(parents=True)
    (a / "alice" / "private_questions.json").write_text('{"secret":[1,0,1]}')
    (a / "quota_before.json").write_text('{"remaining_seconds":138}')
    (a / "_ibm_open_plan_preflight").mkdir()
    (a / "_ibm_open_plan_preflight" / "receipt.json").write_text('{"remaining_seconds":127}')
    full = {"backend": "ibm_test", "job_id": "jobx", "job_tag": "t", "label": "CHSH", "outcomes_sha256": "ab" * 32, "outcomes": [[0, 1]] * 5,
            "questions": {"alice": [0, 1], "bob": [1, 0]}, "commitments": {"alice_salt": "SALT", "alice_sha256": "a" * 64, "bob_salt": "SALT2", "bob_sha256": "b" * 64},
            "quantum": {"per_question_pair": {"x0y0": {"rounds": 5, "win_rate": 0.8}}, "rounds": 5, "standard_error": 0.1, "win_rate": 0.8, "wins": 4, "sigma_above_classical_bound": 1.0},
            "quantum_ideal": 0.85, "classical_bound": 0.75, "loopholes": ["x"], "recorded_utc": "2026-10-25T20:00:00+00:00", "source_class": "RECORDED_IBM_HARDWARE",
            "schema": "navisworld-chsh-game-v1", "date_utc": "20261025", "quantum_seconds": None, "classical_control": {}}
    (a / "chsh_game_result.json").write_text(json.dumps(full))
    prev = tmp_path / "prev.json"
    prev.write_text(json.dumps({"heart_seed_sha256": "c" * 64}))
    return a, prev


def test_public_evidence_never_contains_private_questions_salts_or_outcomes(tmp_path):
    a, prev = artifact(tmp_path)
    out = tmp_path / "out"
    r = se.build(a, out, "tag-x", 8, prev, latest=tmp_path / "latest" / "spark-seed.json")
    text = "".join(f.read_text() for f in out.rglob("*") if f.is_file())
    for banned in ("SALT", "private_questions", "secret", '"outcomes":', '"questions":'):
        assert banned not in text
    assert not list(out.rglob("*private*"))
    assert (tmp_path / "latest" / "spark-seed.json").read_text() == (out / "spark-seed.json").read_text()
    assert r["heart_seed"]["mix"]["heart_seed_v7_sha256"] == "c" * 64 and r["heart_seed"]["heartbeat"].startswith("none")
    assert json.loads((out / "quota-after.json").read_text())["remaining_seconds"] == 127


def test_heartbeat_is_in_the_seed_only_when_a_measured_packet_is_supplied_and_it_is_deterministic(tmp_path):
    a, prev = artifact(tmp_path)
    pk = tmp_path / "pk.json"
    pk.write_text(json.dumps({"packet_sha256": "d" * 64, "heartbeat_label": "MEASURED", "raw_video_published": False}))
    r1 = se.build(a, tmp_path / "o1", "t", 9, prev, bio_packet=pk)
    r2 = se.build(a, tmp_path / "o2", "t", 9, prev, bio_packet=pk)
    plain = se.build(a, tmp_path / "o3", "t", 9, prev)
    assert r1["heart_seed"]["heartbeat"] == "MEASURED" and r1["heart_seed"]["heart_seed_sha256"] == r2["heart_seed"]["heart_seed_sha256"]
    assert r1["heart_seed"]["heart_seed_sha256"] != plain["heart_seed"]["heart_seed_sha256"]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"packet_sha256": "d" * 64, "heartbeat_label": "SIMULATED", "raw_video_published": False}))
    try:
        se.build(a, tmp_path / "o4", "t", 9, prev, bio_packet=bad)
        assert False
    except SystemExit:
        pass


def test_a_result_that_is_not_recorded_ibm_hardware_is_refused(tmp_path):
    a, prev = artifact(tmp_path)
    d = json.loads((a / "chsh_game_result.json").read_text())
    d["source_class"] = "SIMULATED"
    (a / "chsh_game_result.json").write_text(json.dumps(d))
    try:
        se.build(a, tmp_path / "o", "t", 8, prev)
        assert False
    except SystemExit:
        pass


def test_committed_003_evidence_matches_the_latest_pointer_and_the_mix_hook_is_present():
    ev = ROOT / "evidence/zeref-final-spark-003"
    hs = json.loads((ev / "heart-seed-v8.json").read_text())
    v7 = json.loads((ROOT / "evidence/zeref-final-spark-001/heart-seed-v7.json").read_text())
    assert hs["mix"]["heart_seed_v7_sha256"] == v7["heart_seed_sha256"] and hs["creature_id"] == "bb-deada969"
    assert not list(ev.rglob("*private*"))
    src = (ROOT / "scripts/zeref_continuation_006.py").read_text()
    assert "heart_seed_v8_sha256" in src and "evidence/zeref-final-spark-003/heart-seed-v8.json" in src
