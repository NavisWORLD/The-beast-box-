"""Preserve production's existing native Dockerfile during Git-backed releases.

Research scripts or a basic cloud bridge image must not silently replace the
RAWRPHOS/PHOS/SAMGO-enabled existing owner service.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
DEPLOY=ROOT/"apps/beastbox-cloud/bridge/deploy"

def test_railway_native_main_uses_same_source_image_as_existing_production():
    cfg=json.loads((DEPLOY/"railway.json").read_text(encoding="utf-8"))
    assert cfg["build"]["builder"]=="DOCKERFILE"
    assert cfg["build"]["dockerfilePath"]=="apps/beastbox-cloud/bridge/deploy/Dockerfile.rawrphos"
    native=ROOT/cfg["build"]["dockerfilePath"]
    assert native.is_file()
    src=native.read_text(encoding="utf-8")
    assert "COPY models/rawrphos/" in src
    assert "COPY models/qc67/" in src
    assert "start_rawrphos.sh" in src
    assert "install_pinned_14k.py" in src
    assert "install_pinned_18k.py" in src

def test_research_publication_main_change_is_watched_and_healthcheck_is_preserved():
    cfg=json.loads((DEPLOY/"railway.json").read_text(encoding="utf-8"))
    assert "README.md" in cfg["build"]["watchPatterns"]
    assert "apps/beastbox-cloud/bridge/**" in cfg["build"]["watchPatterns"]
    assert cfg["deploy"]["healthcheckPath"]=="/healthz"
    assert cfg["deploy"]["healthcheckTimeout"]>=180
