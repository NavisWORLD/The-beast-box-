import json
import sys
from pathlib import Path

import pytest

from beastbox.creature.native_gguf import run_native_conversion


def test_runner_requires_real_converter(tmp_path: Path):
    source = tmp_path / "phos.pt"
    source.write_bytes(b"checkpoint")
    with pytest.raises(ValueError, match="converter"):
        run_native_conversion("phos", source=source, output_dir=tmp_path)


def test_runner_hashes_source_and_validates_gguf_output(tmp_path: Path):
    source = tmp_path / "cosmos_born.pt"
    source.write_bytes(b"checkpoint-source")
    converter = tmp_path / "fake_converter.py"
    converter.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "Path(sys.argv[2]).write_bytes(b'GGUF' + (3).to_bytes(4, 'little') + b'test')\n",
        encoding="utf-8",
    )

    receipt = run_native_conversion(
        "cosmos-born",
        source=source,
        output_dir=tmp_path / "out",
        converter=[sys.executable, str(converter), "{source}", "{output}"],
    )
    assert receipt["schema"] == "cosmos.native-gguf-receipt.v1"
    assert receipt["status"] == "CONVERTED"
    assert len(receipt["source"]["sha256"]) == 64
    assert len(receipt["output"]["sha256"]) == 64
    assert receipt["output"]["format"] == "gguf"
    assert Path(receipt["receipt_path"]).is_file()
    persisted = json.loads(Path(receipt["receipt_path"]).read_text(encoding="utf-8"))
    assert persisted["output"]["sha256"] == receipt["output"]["sha256"]
