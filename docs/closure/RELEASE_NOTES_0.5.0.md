Beast Box 0.5.0 is release-hardened experimental software with a durable local runtime and portable application previews. It is not a universally production-ready operating system or app-store release.

Downloads:
- `beast-box-combined-0.5.0.zip`: EnD, checked INSTALL.bat/INSTALL.sh, Python wheel/source, configuration instructions and sealed historical evidence. Requires Python 3.10–3.12; installation preserves separate user data.
- `beast-desktop-*.zip`: Windows and Linux desktop executables, C++/Rust process clients, license notices and actual restart/install receipts. Linux build targets Ubuntu 24.04. Desktop real inference requires a separately installed loopback Ollama model; reference providers are fixtures.
- Android sideload APK: actual embedded durable runtime, emulator-tested process restarts and A/B/A fixture swaps. Debug signed, no bundled inference engine/model, no Play release.
- iOS simulator ZIP and unsigned device archive: actual embedded runtime with fixture providers, simulator-tested process restarts and A/B/A. Physical iPhone installation requires Apple signing/provisioning; this is not a TestFlight/App Store download.

Optional IBM and Azure methods use user-owned credentials with explicit live-job authorization. Azure integration targets an IonQ simulator. No live hardware job, quantum causality, or quantum advantage is established. WAV summaries and numeric light inputs are bounded input adapters, not certification of camera/audio/light hardware.

Model-independent memory, state, provenance, integrity checks, backups and authority isolation remain outside model weights. Retention is recoverable according to storage/backups, not a promise of infinite memory. Models never inherit tool authority through context.

The original real-model experiment-002 evidence is unchanged. Its successful historical revision remains SmolLM2-135M@4e53f736cbb20a9a0f56b4c4bf378d9f306ff915; failed revisions and blocked experiment-001 provenance remain preserved.

See RELEASE_PROVENANCE.json, RELEASE_VERIFICATION.json, PORTABLE_VERIFICATION.json and the accompanying CI evidence for exact source and tests. Verify SHA256SUMS.txt before installation. Historical v0.3.2/v0.4.0 assets are not replaced.
