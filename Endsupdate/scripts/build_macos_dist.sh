#!/bin/zsh
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
OUT_DIR="${OUT_DIR:-$ROOT/dist}"
WORK_DIR="${WORK_DIR:-$ROOT/.build/macos-zeref}"
APP="$OUT_DIR/Zeref.app"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "build_macos_dist.sh must run on macOS" >&2
  exit 2
fi

ARCH="$(uname -m)"
case "$ARCH" in
  arm64) ARCH_TAG="AppleSilicon-arm64" ;;
  x86_64) ARCH_TAG="Intel-x86_64" ;;
  *) echo "Unsupported macOS architecture: $ARCH" >&2; exit 2 ;;
esac

echo "[Zeref] Building macOS distribution for $ARCH ($ARCH_TAG)"
rm -rf "$WORK_DIR" "$APP"
mkdir -p "$WORK_DIR" "$OUT_DIR"

if ! "$PYTHON_BIN" -c 'import PyInstaller' >/dev/null 2>&1; then
  echo "PyInstaller is required. Install with: python3 -m pip install pyinstaller" >&2
  exit 2
fi

"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name zeref-cli \
  --collect-submodules beastbox \
  --distpath "$WORK_DIR/pyinstaller-dist" \
  --workpath "$WORK_DIR/pyinstaller-work" \
  --specpath "$WORK_DIR" \
  "$ROOT/scripts/zeref_app_entry.py"

mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$ROOT/macos/Info.plist" "$APP/Contents/Info.plist"
cp "$ROOT/macos/Zeref" "$APP/Contents/MacOS/Zeref"
cp "$WORK_DIR/pyinstaller-dist/zeref-cli" "$APP/Contents/Resources/zeref-cli"
chmod +x "$APP/Contents/MacOS/Zeref" "$APP/Contents/Resources/zeref-cli"

SIGN_IDENTITY="${MACOS_SIGN_IDENTITY:--}"
if [[ "$SIGN_IDENTITY" == "-" ]]; then
  echo "[Zeref] Applying ad-hoc codesign signature"
  /usr/bin/codesign --force --deep --sign - "$APP"
else
  echo "[Zeref] Signing with configured Developer ID identity"
  /usr/bin/codesign --force --deep --options runtime --timestamp --sign "$SIGN_IDENTITY" "$APP"
fi
/usr/bin/codesign --verify --deep --strict --verbose=2 "$APP"

STAGING="$WORK_DIR/dmg-root"
rm -rf "$STAGING"
mkdir -p "$STAGING"
/usr/bin/ditto "$APP" "$STAGING/Zeref.app"
ln -s /Applications "$STAGING/Applications"

DMG="$OUT_DIR/Zeref-macOS-$ARCH_TAG.dmg"
ZIP="$OUT_DIR/Zeref-macOS-$ARCH_TAG.app.zip"
rm -f "$DMG" "$ZIP"
/usr/bin/hdiutil create \
  -volname "Zeref" \
  -srcfolder "$STAGING" \
  -ov \
  -format UDZO \
  "$DMG"
/usr/bin/hdiutil verify "$DMG"
/usr/bin/ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"

CHECKSUMS="$OUT_DIR/Zeref-macOS-$ARCH_TAG.sha256"
DMG_NAME="$(basename "$DMG")"
ZIP_NAME="$(basename "$ZIP")"
CHECKSUM_NAME="$(basename "$CHECKSUMS")"
(
  cd "$OUT_DIR"
  /usr/bin/shasum -a 256 "$DMG_NAME" "$ZIP_NAME" > "$CHECKSUM_NAME"
)

printf '\n[Zeref] macOS artifacts ready:\n  %s\n  %s\n  %s\n' "$DMG" "$ZIP" "$CHECKSUMS"
