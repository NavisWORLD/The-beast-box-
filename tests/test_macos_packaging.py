from __future__ import annotations

import plistlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_macos_double_click_launcher_exists_and_bootstraps_zeref():
    launcher = ROOT / "START_ZEREF.command"
    assert launcher.is_file()
    text = launcher.read_text(encoding="utf-8")
    assert "START_ZEREF.sh" in text
    assert "uname -m" in text
    assert "ollama" in text.lower()


def test_macos_app_bundle_metadata_is_valid():
    plist_path = ROOT / "macos" / "Info.plist"
    assert plist_path.is_file()
    with plist_path.open("rb") as handle:
        data = plistlib.load(handle)
    assert data["CFBundleName"] == "Zeref"
    assert data["CFBundleDisplayName"] == "Zeref"
    assert data["CFBundleIdentifier"] == "world.navis.zeref"
    assert data["CFBundleExecutable"] == "Zeref"
    assert data["CFBundlePackageType"] == "APPL"
    assert data["LSMinimumSystemVersion"]


def test_finder_launcher_searches_common_ollama_paths():
    launcher = (ROOT / "macos" / "Zeref").read_text(encoding="utf-8")
    assert "/opt/homebrew/bin" in launcher
    assert "/usr/local/bin" in launcher


def test_macos_distribution_builder_creates_app_and_dmg():
    builder = ROOT / "scripts" / "build_macos_dist.sh"
    assert builder.is_file()
    text = builder.read_text(encoding="utf-8")
    assert "PyInstaller" in text or "pyinstaller" in text
    assert "Zeref.app" in text
    assert "hdiutil" in text
    assert "codesign" in text
    assert "Applications" in text


def test_macos_ci_builds_apple_silicon_and_intel_artifacts():
    workflow = ROOT / ".github" / "workflows" / "macos-zeref.yml"
    assert workflow.is_file()
    text = workflow.read_text(encoding="utf-8")
    assert "macos-15" in text
    assert "macos-15-intel" in text
    assert "build_macos_dist.sh" in text
    assert "upload-artifact" in text
    assert "Zeref" in text


def test_macos_packaging_never_embeds_hugging_face_token():
    paths = [
        ROOT / "START_ZEREF.command",
        ROOT / "scripts" / "build_macos_dist.sh",
        ROOT / ".github" / "workflows" / "macos-zeref.yml",
        ROOT / "macos" / "Info.plist",
    ]
    for path in paths:
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert "HFAK" not in text
            assert "hf_" not in text.lower()
