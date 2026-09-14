from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_android_release_identity_and_env_signing() -> None:
    gradle = (ROOT / "apps/android/app/build.gradle.kts").read_text(encoding="utf-8")
    assert 'applicationId = "dev.beastbox.mobile"' in gradle
    assert 'versionName = "0.7.1"' in gradle
    assert "BEASTBOX_ANDROID_KEYSTORE" in gradle
    assert "BEASTBOX_ANDROID_KEYSTORE_PASSWORD" in gradle
    assert "BEASTBOX_ANDROID_KEY_ALIAS" in gradle
    assert "BEASTBOX_ANDROID_KEY_PASSWORD" in gradle
    assert "storePassword =" in gradle
    for forbidden in ("hunter2", "androiddebugkey-password-literal", "/home/", "BEGIN RSA"):
        assert forbidden not in gradle
    receipt = (ROOT / "apps/android/scripts/build_receipt.py").read_text(encoding="utf-8")
    assert "0.7.1" in receipt


def test_ios_release_metadata_entitlements_and_export_options() -> None:
    project = (ROOT / "apps/ios/project.yml").read_text(encoding="utf-8")
    assert "MARKETING_VERSION: '0.7.1'" in project
    assert "CODE_SIGN_ENTITLEMENTS: BeastBox.entitlements" in project
    assert "NSLocalNetworkUsageDescription" in project
    entitlements = (ROOT / "apps/ios/BeastBox.entitlements").read_text(encoding="utf-8")
    assert "com.apple.security.network.client" in entitlements
    options = (ROOT / "apps/ios/ExportOptions.plist").read_text(encoding="utf-8")
    assert "REPLACE_WITH_APPLE_TEAM_ID" in options
    assert "dev.beastbox.mobile" in options
    assert "BEGIN CERTIFICATE" not in options