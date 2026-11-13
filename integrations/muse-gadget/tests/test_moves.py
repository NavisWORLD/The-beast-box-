import json

from conftest import FIXTURES

from beastbox_musegadget import moves


def test_moveset_is_deterministic_and_element_based():
    genome = json.loads((FIXTURES / "genomes.json").read_text())[0]
    one = moves.build_moveset(genome)
    two = moves.build_moveset(json.loads(json.dumps(genome)))
    assert one == two
    assert one["element"] == "frost"
    assert [m["name"] for m in one["moves"]] == ["Rime Lance", "Frost Fang", "Shard Blizzard", "Glacier Stomp"]
    assert moves.pick_attack(one, 3, "chat") == moves.pick_attack(two, 3, "chat")


def test_fallback_moves_and_find():
    fallback = moves.build_moveset(None)
    assert fallback["key"] == "spark-fallback" and fallback["moves"][0]["name"] == "Spark Beam"
    assert moves.find_move(fallback, "SLASH")["name"] == "Star Claw"
    assert moves.find_move(fallback, "nope") is None


def test_js_round_matches_math_round():
    assert moves.js_round(2.5) == 3 and moves.js_round(-2.5) == -2 and moves.js_round(0.49) == 0
