import hashlib
from pathlib import Path

import pytest

from beastbox.creature.gguf import export_gguf
from beastbox.creature.weights import build_weight_manifest, inspect_weight, sha256_file


def test_weight_inspection_and_manifest_are_content_addressed(tmp_path: Path):
    path = tmp_path / "spark.pt"
    path.write_bytes(b"cosmos-weight")
    wanted = hashlib.sha256(b"cosmos-weight").hexdigest()
    assert sha256_file(path) == wanted
    info = inspect_weight(path)
    assert info["format"] == "native"
    assert info["size"] == len(b"cosmos-weight")
    manifest = build_weight_manifest(path, architecture="qc67-spark-cst", license_name="research")
    assert manifest["sha256"] == wanted
    assert manifest["format"] == "native"
    assert manifest["architecture"] == "qc67-spark-cst"
    assert manifest["license"] == "research"


def test_gguf_extension_is_identified_as_gguf(tmp_path: Path):
    path = tmp_path / "gemma.gguf"
    path.write_bytes(b"GGUF" + b"\x00" * 16)
    assert inspect_weight(path)["format"] == "gguf"


def test_export_gguf_refuses_extension_only_fake_conversion(tmp_path: Path):
    source = tmp_path / "spark.pt"
    source.write_bytes(b"native")
    with pytest.raises(ValueError, match="converter"):
        export_gguf(source, tmp_path / "spark.gguf")
