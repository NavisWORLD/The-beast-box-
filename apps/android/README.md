# Beast Box Android 0.5.0 candidate

Native Kotlin UI embedding this repository's Python `beastbox.durable.DurableRuntime`
through Chaquopy. Application ID: `dev.beastbox.mobile`. Android 7.0/API 24 minimum;
arm64-v8a and x86_64. Memory lives in `Context.filesDir/beast-runtime`, is verified
on reopen, and survives provider changes and process restarts. Android backup is
disabled. Uninstalling or clearing data deletes that memory.

Reference A and B are **deterministic fixtures**, not language models. Ollama accepts
only the core's protected loopback URLs: install and run a compatible Ollama engine
and weights on the Android device separately. A desktop's localhost is not the
phone's localhost. No remote proxy, credentials, weights, owner history or authority
is bundled or transferred. The default runtime has no enabled tool authority.
Failed inference never falls back to a fixture. The provider configuration is stored
in private Android preferences only after validation; memories cannot configure it.

## Build and acceptance

Install Java 17, Python 3.12, Android SDK platform 35/build-tools 35.0.0 and Gradle
8.11.1. Run from this directory:

```sh
gradle --no-daemon assembleDebug assembleDebugAndroidTest lintDebug
adb install app/build/outputs/apk/debug/app-debug.apk
adb install app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
bash scripts/emulator_acceptance.sh acceptance
ACCEPTANCE_OUTCOME=success python scripts/build_receipt.py
```

Use an API 35 x86_64 emulator for the automated acceptance. Each instrumentation
phase runs in a separate process: initialize/write with A, reopen/recall with B,
then reopen/recall with A. Assertions check retained system ID, checkpoint, memory
digest, state digest, ledger head and turn, plus rejected nonloopback/credential URLs.
The middle phase also closes and recreates the Python runtime within one process.
Fixture recall is not real-model inference acceptance. Physical devices and real
Ollama inference require separate testing.

The `Android on-device runtime candidate` GitHub workflow supports dispatch,
`workflow_call`, and the integration branch. Its success artifact
`beast-android-0.5.0` contains `beast-android-0.5.0-sideload.apk`, the build receipt
with APK/source hashes, and emulator receipts/logs. Failure evidence is retained
separately. Only a successful actual Android build and emulator gate produces the
candidate artifact. The APK uses Android debug signing for sideloading; it is not
Play production signing. Debug keys may change across clean CI builds, so an
existing installation may not accept an update (do not uninstall retained data
without arranging a backup).

Host bridge verification from repository root:

```sh
python -m unittest discover -s apps/android/tests -v
```

Pinned compatibility sources:

- [Chaquopy 17.0 setup](https://chaquo.com/chaquopy/doc/current/android.html): Python 3.12, API 24+, AGP 7.3–9.2, 64-bit ABIs.
- [AGP 8.9 compatibility](https://developer.android.com/build/releases/agp-8-9-0-release-notes): Gradle 8.11.1, JDK 17, API 35.
- [Kotlin Gradle compatibility](https://kotlinlang.org/docs/gradle-configure-project.html): Kotlin 2.2.10 supports AGP through 8.10 and Gradle through 8.14.
