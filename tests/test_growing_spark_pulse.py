from beastbox import spark_pulse as sp

def test_port_matches_js_vector_and_moves_each_beat():
    p = sp.spark_pulse(1793900000000)
    assert p["beat"] == 41179 and p["label"] == "RECORDED" and p["question_pair"] == "x1y0"
    assert p["pulse_sha256"] == "2c1c647e2156c56e3045c8fd8a93727a64b67f09f12cf8b34323048def5ad792" and p["glow"] == 0.559
    assert sp.spark_pulse(1793900060000)["beat"] == 41185

def test_absent_is_none_not_half():
    assert sp.spark_pulse("bad") is None

def test_no_random_in_port():
    src = open(sp.__file__).read()
    assert "random" not in src.replace("no random", "")
