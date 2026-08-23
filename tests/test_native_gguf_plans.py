from pathlib import Path

from beastbox.creature.native_gguf import build_conversion_plan


def test_missing_source_is_explicit(tmp_path: Path):
    plan = build_conversion_plan("phos", source=tmp_path / "phos.pt", output_dir=tmp_path)
    assert plan["status"] == "SOURCE_MISSING"
    assert plan["source"]["exists"] is False
    assert plan["output"].endswith("cosmos-phos-f32.gguf")
    assert plan["architecture"] == "cosmos"


def test_present_source_is_hashed_before_conversion(tmp_path: Path):
    source = tmp_path / "cosmos_born.pt"
    source.write_bytes(b"real-source-bytes")
    plan = build_conversion_plan("cosmos-born", source=source, output_dir=tmp_path / "out")
    assert plan["status"] == "SOURCE_READY"
    assert plan["source"]["exists"] is True
    assert len(plan["source"]["sha256"]) == 64
    assert plan["source"]["size"] == len(b"real-source-bytes")
    assert plan["runtime"]["stock_llamacpp"] is False
