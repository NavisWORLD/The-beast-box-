# Beast Box iOS 0.5.0

SwiftUI calls embedded CPython 3.12 and the repository's `beastbox.durable.DurableRuntime`.
SQLite, checkpoints, provenance and retained memory live in the application's private
Application Support/BeastRuntime directory. Each request reopens the same store.
The A/B picker selects explicitly labelled reference providers. No language model
weights, private history or external service credentials are included.

## Build and acceptance

On an Apple Silicon Mac with Xcode, an installed iOS simulator and XcodeGen:

```sh
bash apps/ios/scripts/fetch-python.sh
cd apps/ios
xcodegen generate
xcodebuild -project BeastBox.xcodeproj -scheme BeastBox -configuration Release \
  -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath build/simulator CODE_SIGNING_ALLOWED=NO build
```

The `ios-app.yml` workflow installs and launches the simulator app in three separate
processes (A, B, A), verifies identical retained checkpoints between processes,
checks increasing turns and provider labels, and only then packages the simulator
app and unsigned device archive. Receipts are retained even when later gates fail.
The acceptance flag writes only the fixture receipt to the app's Documents folder;
it does not clear the runtime store. CI uses a newly installed app container.

`beast-ios-simulator-0.5.0` is an installable simulator app ZIP.
`beast-ios-unsigned-device-0.5.0` is an Xcode archive ZIP, **not an installable IPA**.
An Apple developer identity, provisioning profile, appropriate bundle identifier,
physical device acceptance and App Store Connect/TestFlight upload remain external
release requirements. Neither a source check nor simulator success certifies these.

## Pinned Python origin

Official release: https://github.com/beeware/Python-Apple-support/releases/tag/3.12-b9

Asset: `Python-3.12-iOS-support.b9.tar.gz`

SHA-256: `a3be9e278c742911db54dd3045bd7451928813508771c9acf14b4af75294edd2`

The hash was checked against both official GitHub release metadata and the
downloaded asset. Fetching fails on a mismatched hash. The build invokes the pinned
framework's own `build/utils.sh` to install the standard library and convert binary
extension modules (including SQLite) into iOS framework format. Its extension
frameworks receive ad hoc signatures when distribution signing is disabled.
The Python support package includes its own licensing files; these remain bundled
with its standard library. Public Beast source remains subject to the repository LICENSE.

Host boundary tests (not an iOS build claim):

```sh
PYTHONPATH=apps/ios/python:. python -m unittest discover -s apps/ios/python
```
