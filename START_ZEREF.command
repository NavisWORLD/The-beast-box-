#!/bin/zsh
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT"
ARCH="$(uname -m)"
echo "[Zeref] macOS launcher detected: $ARCH"

if ! command -v python3 >/dev/null 2>&1; then
  /usr/bin/osascript -e 'display dialog "Python 3 is required for the source launcher. The packaged Zeref.app/DMG includes its own Python runtime." buttons {"Open Python Download", "Cancel"} default button "Open Python Download" with title "Zeref"' >/dev/null 2>&1 || true
  /usr/bin/open "https://www.python.org/downloads/macos/"
  exit 2
fi

if ! command -v ollama >/dev/null 2>&1; then
  /usr/bin/osascript -e 'display dialog "Zeref uses Ollama for local models. Install Ollama, then double-click START_ZEREF.command again." buttons {"Open Ollama Download", "Cancel"} default button "Open Ollama Download" with title "Zeref"' >/dev/null 2>&1 || true
  /usr/bin/open "https://ollama.com/download/mac"
  exit 2
fi

exec /bin/sh "$ROOT/START_ZEREF.sh" "$@"
