import json

from beastbox.creature.cli import main


def test_cli_lists_native_recipes(capsys):
    assert main(["weights", "native-recipes"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {"phos", "cosmos-born", "samgo-5.7", "cosmos-best"}


def test_cli_builds_missing_source_plan(tmp_path, capsys):
    missing = tmp_path / "phos.pt"
    assert main([
        "weights", "native-plan", "phos",
        "--source", str(missing),
        "--output-dir", str(tmp_path / "gguf"),
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "SOURCE_MISSING"
    assert payload["output"].endswith("cosmos-phos-f32.gguf")
