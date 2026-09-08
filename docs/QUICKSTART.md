# Five-minute quickstart

Your AI history can live outside the model. Start with the reference fixture to
check installation, then connect a real model. No cloud account is required.

1. Download the combined ZIP from [Releases](https://github.com/NavisWORLD/The-beast-box-/releases).
   Verify `SHA256SUMS.txt`, then extract the ZIP into a new folder.
2. Install Python 3.10–3.12 if using the combined kit. Run `INSTALL.bat` on Windows
   or `sh UnixINSTALL.sh` on Linux/macOS. The installer verifies its bundled wheel.
   Desktop executable ZIPs bundle Python; their platform names describe the tested build target.
3. Run `LAUNCH.bat` or `sh UnixLAUNCH.sh`. Choose Reference for a labelled fixture,
   or Ollama with an explicitly installed model. Enter a message, close and reopen.
   The default desktop data directory is `~/.beastbox/data`.

For CLI use, activate `~/.beastbox/venv` (Windows: `%USERPROFILE%\.beastbox\venv`),
or use a source environment:

```bash
git clone https://github.com/NavisWORLD/The-beast-box-.git
cd The-beast-box-
python -m venv .venv
# Unix: source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -e .
beastbox doctor --data-dir ./my-beast
beastbox runtime chat "Remember the test code is SUNFLOWER" --data-dir ./my-beast
beastbox runtime chat "What is the test code?" --data-dir ./my-beast
beastbox runtime inspect --data-dir ./my-beast
```

Each CLI invocation is a separate process. The reference provider echoes selected
context; it is **not a language model**. `inspect` verifies durable state and reports
its system ID and checkpoint hash. `doctor` checks actual write access, storage,
recovery and installed wheel file hashes. Editable installs cannot attest a wheel
RECORD and say `UNAVAILABLE`; optional libraries are not required gates.

Connect a separately installed Ollama model:

```bash
beastbox doctor --provider ollama --model YOUR_MODEL --data-dir ./my-beast
beastbox runtime chat "What is the test code?" --provider ollama --model YOUR_MODEL --data-dir ./my-beast
```

Keep `--data-dir` unchanged when changing the model. Consult
[Provider setup](PROVIDER_SETUP.md), [Portable state](PORTABLE_STATE.md), and
[EnD](../kits/BEAST_BOX_COMBINED/EnD) for API, backups and permission boundaries.

## Remove the app without erasing the story

Close every Beast process. Delete the extracted executable folder or uninstall the
package/virtual environment. This does not intentionally delete `~/.beastbox/data`.
To erase memory, first verify a backup if you want recovery, then explicitly delete
that data directory. Mobile uninstall/clear-data can erase the app's private store;
mobile export UI and encrypted backup are not implemented. Do not assume an OS
backup or app-store reinstall preserves mobile history.

If a model server is missing, start/configure it; there is no inference fallback.
If integrity fails, preserve the corrupt copy and restore a verified snapshot into
a new directory. Never repair hashes to make corrupt data look valid.
