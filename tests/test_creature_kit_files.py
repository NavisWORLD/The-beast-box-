import json
from pathlib import Path


REQUIRED = [
    "README.md",
    "QUICKSTART.md",
    "ecosystem-manifest.json",
    "libraries/README.md",
    "weights/README.md",
    "weights/native/README.md",
    "weights/gguf/README.md",
    "weights/adapters/README.md",
    "weights/tools/inspect_weights.py",
    "weights/tools/build_manifest.py",
    "weights/tools/export_gguf.py",
    "bridges/README.md",
    "config/creature.example.json",
    "config/secrets.example.env",
    "examples/hello_creature.py",
    "examples/classical_state.py",
    "examples/ibm_receipt.py",
    "examples/azure_receipt.py",
    "evidence/README.md",
]

TEMPLATES = ["blank-creature", "local-creature", "ibm-creature", "azure-creature", "hybrid-creature"]


def test_creator_distribution_contains_complete_contract():
    root = Path("COSMOS_CREATURE_KIT")
    missing = [rel for rel in REQUIRED if not (root / rel).exists()]
    assert not missing, missing
    for name in TEMPLATES:
        path = root / "templates" / name / "creature.json"
        assert path.exists(), path
        data = json.loads(path.read_text())
        assert data["species"] == "cosmos.quantum-creature"
