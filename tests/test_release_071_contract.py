from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_071_active_identity_is_consistent() -> None:
    assert 'version = "0.7.1"' in text("pyproject.toml")
    assert '__version__ = "0.7.1"' in text("beastbox/__init__.py")

    android = text("apps/android/app/build.gradle.kts")
    assert 'versionCode = 701' in android
    assert 'versionName = "0.7.1"' in android
    assert "0.7.1" in text("apps/android/scripts/build_receipt.py")

    ios = text("apps/ios/project.yml")
    assert "MARKETING_VERSION: '0.7.1'" in ios
    assert "CURRENT_PROJECT_VERSION: '8'" in ios


def test_release_071_workflows_and_portable_staging_use_patch_version() -> None:
    release = text(".github/workflows/release.yml")
    public_smoke = text(".github/workflows/public-release-wheel-smoke.yml")
    android = text(".github/workflows/android-app.yml")
    ios = text(".github/workflows/ios-app.yml")
    staging = text("scripts/stage_portable_release.py")

    assert 'test "$version" = "0.7.1"' in release
    assert "RELEASE_NOTES_0.7.1.md" in release
    assert "default: v0.7.1" in public_smoke
    assert "|| 'v0.7.1'" in public_smoke
    assert "beast-android-0.7.1" in android
    assert "beast-ios-simulator-0.7.1" in ios
    assert "beast-ios-unsigned-device-0.7.1" in ios
    assert "beast-ios-evidence-0.7.1" in ios
    assert 'version: str = "0.7.1"' in staging
    assert "default='0.7.1'" in staging


def test_release_071_notes_preserve_v070_audit_history() -> None:
    notes = text("docs/closure/RELEASE_NOTES_0.7.1.md")
    assert "Synapse Trace" in notes
    assert "v0.7.0" in notes
    assert "historical" in notes.lower()
    assert "public stranger" in notes.lower()
