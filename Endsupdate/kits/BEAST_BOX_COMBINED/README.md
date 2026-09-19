# Combined Beast Box kit

Start with [EnD](EnD). Extract the complete release, then run `INSTALL.bat`
(Windows) or `sh UnixINSTALL.sh` (Linux/macOS). Launch with `LAUNCH.bat` or
`sh UnixLAUNCH.sh`. Python 3.10–3.12 is required; graphical use requires Tk.

The shared bootstrap verifies the wheel SHA-256 before installing offline in
`~/.beastbox/venv`. Data stays separately in `~/.beastbox/data` across reinstall
and model changes. No administrator access, credentials or model download is
required. `--smoke` on the launcher exercises a durable reference-fixture turn
without a display; it does not validate native graphical behavior.

The release also includes source, architecture/security/readiness documents,
license, and the unchanged historical model-swap receipt. No weights or secrets.
A source checkout must build the release or install from the repository root.
Historical v0.3.2 and v0.4.0 assets stay separate.
