# Zeref for macOS

Zeref now has two macOS paths: a source launcher for developers and a packaged Finder app for normal users.

## Recommended: Zeref.app / DMG

The macOS workflow builds separate installers for:

- Apple Silicon (`arm64`)
- Intel (`x86_64`)

Each disk image contains:

```text
Zeref.app
Applications -> /Applications
```

Open the DMG, drag **Zeref.app** into **Applications**, then open Zeref from Finder or Spotlight.

The packaged app contains a frozen `zeref-cli` executable built with PyInstaller, so DMG users do not need to install Python separately. Ollama is still the local model runtime. If Ollama is missing, Zeref shows a macOS dialog and opens the Ollama download page rather than failing silently.

When the app starts, it opens Terminal and launches the same COSMOS/Zeref runtime used by the command-line kit. Persistent memory remains under the normal per-user Zeref home:

```text
~/.cosmos-zeref/
```

That means switching between Zeref.app, the command-line launcher, or different Ollama models continues to use the same user memory unless `ZEREF_HOME` is intentionally changed.

## Model switching

Inside the Zeref session:

```text
/models
/model
/use llama3.2:3b
/use qwen2.5:7b
/use zeref
```

A missing Ollama model is pulled automatically. Switching the language model does not discard the COSMOS Reconciliation Memory database.

## Source checkout: double-click launcher

Developers who cloned the repository can double-click:

```text
START_ZEREF.command
```

This source launcher detects the Mac architecture, checks Python and Ollama, and then delegates to `START_ZEREF.sh`.

Unlike the packaged app, the source launcher requires Python 3.10 or newer because it creates a local `.venv` from the checkout.

## Building locally

On macOS:

```bash
python3 -m pip install -e '.[dev]'
python3 -m pip install pyinstaller
chmod +x scripts/build_macos_dist.sh macos/Zeref START_ZEREF.command
./scripts/build_macos_dist.sh
```

Artifacts are written to `dist/`:

```text
Zeref.app
Zeref-macOS-AppleSilicon-arm64.dmg       # on Apple Silicon
Zeref-macOS-Intel-x86_64.dmg             # on Intel
Zeref-macOS-*.app.zip
Zeref-macOS-*.sha256
```

The build verifies the app bundle with `codesign` and the disk image with `hdiutil verify`.

## Signing and Gatekeeper

Public CI builds use an ad-hoc code signature so the bundle structure is signed and verifiable without storing an Apple private signing identity in the repository.

For a normal public macOS distribution with the smoothest Gatekeeper experience, configure a real Apple Developer ID signing identity and notarize the release outside the public source tree. `scripts/build_macos_dist.sh` accepts `MACOS_SIGN_IDENTITY` for a configured signing environment. Apple credentials and certificates must remain in secret storage and must never be committed.

## CI and releases

`.github/workflows/macos-zeref.yml` builds and validates both Mac architectures. Pull requests produce downloadable workflow artifacts. Tags matching `v*` also publish the generated DMG, zipped app, and SHA-256 files to the matching GitHub Release.

No Hugging Face token, Apple signing credential, or other private credential is embedded in the Mac app or packaging workflow.
