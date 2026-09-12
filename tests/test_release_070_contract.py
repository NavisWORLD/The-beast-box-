from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_070_is_version_consistent_and_source_bound() -> None:
    pyproject = text("pyproject.toml")
    package = text("beastbox/__init__.py")
    portable = text(".github/workflows/portable-products.yml")
    release = text(".github/workflows/release.yml")

    assert 'version = "0.7.0"' in pyproject
    assert '__version__ = "0.7.0"' in package
    assert "0.6.0" not in portable
    assert "RELEASE_NOTES_0.7.0.md" in release
    assert "origin/main" in release and "GITHUB_SHA" in release


def test_release_070_requires_canonical_ci_config_and_web_gates() -> None:
    release = text(".github/workflows/release.yml")
    for workflow in ("ci.yml", "config-contract.yml", "web-runtime.yml"):
        assert f"uses: ./.github/workflows/{workflow}" in release
    for job in ("canonical-ci", "configuration-contract", "web-runtime"):
        assert job in release


def test_release_070_public_kit_contains_standalone_web_client() -> None:
    builder = text("scripts/build_release_kit.py")
    for asset in (
        "html/index.html",
        "html/standalone.html",
        "html/styles.css",
        "html/app.js",
        "html/policy.js",
        "html/profiles.js",
        "html/manifest.webmanifest",
        "html/sw.js",
        "html/icon.svg",
        "html/README.md",
    ):
        assert asset in builder


def test_public_stranger_smoke_follows_published_release_and_public_checksums() -> None:
    smoke = text(".github/workflows/public-release-wheel-smoke.yml")
    assert "release:" in smoke and "published" in smoke
    assert "SHA256SUMS.txt" in smoke
    assert "source_checkout_used" in smoke
    assert "standalone.html" in smoke
    assert "beastbox-cosmic" in smoke
    assert "0.6.0" not in smoke
