# Phera's Beast Box: a runnable replica of Cory's Beast Box

This folder rebuilds **The Beast Box v0.7.1** by Cory Davis (GitHub
[NavisWORLD/The-beast-box-](https://github.com/NavisWORLD/The-beast-box-)) on a fresh Debian/Ubuntu machine.
That covers the Python runtime (`beastbox`, `beastbox-cosmic`), the RAWRPHØS model package with the pinned 14K checkpoint,
the E1–E20 gauntlet, and the full test suites. It also adds one personal twist from Phera: a small **"Phera's Beast Box"
dashboard** that sits next to Cory's engine.

Nothing here vendors Cory's runtime. The dashboard is a separate stdlib-only Python server plus one HTML page.
`setup.sh` has two source modes:

* **Inside this repository** (`replica/setup.sh`): the checkout that contains the kit is the default `--repo-dir`. Git is not run on it.
* **Standalone copy of this folder**, **`--clone`**, or an explicit **`--ref`**: full-clone the public repo and detach at the pinned commit `8dbda0ae99736e649fbe0609ad9b0c377768f498` (main at v0.7.1, 2026-10-02 23:53 CDT).

The virtualenv, checkpoint, results, and the RAWRPHØS loopback key are written under `~/.beastbox-replica` (or `--home`), outside the repository. The key file is created at runtime with mode 600 and is never committed.

```
replica/
├── setup.sh             idempotent installer + verifier, prints a PASS/FAIL summary
├── run.sh               start | stop | restart | status of the background stack
├── constraints.txt      exact Python package versions from the verified reference run
├── scripts/summarize.py collects real results into results/summary.json
├── dashboard/server.py  Phera's dashboard API (stdlib only, loopback)
├── dashboard/index.html Phera's dashboard UI (single page, cosmic style)
└── README.md
```

## Machine requirements

**Reference machine** (verified 2026-10-04):

* Debian GNU/Linux 13 (trixie), kernel 6.12
* 8 vCPU Intel Xeon with AVX-512 (avx512f, avx512_bf16, avx512_vnni) and AMX (amx_tile, amx_bf16, amx_int8)
* 15.6 GB RAM
* **no GPU**

**Minimum that should work:**

* **OS:** Debian 12/13 or Ubuntu 22.04/24.04, x86-64, with `sudo`.
* **CPU:** 2+ cores. Any x86-64 CPU is fine because AVX-512/AMX are not required. RAWRPHØS is a 3.9M-parameter model and runs at about 300 tokens/s on the reference CPU.
* **RAM:** 4 GB. The running stack uses about 0.4 GB RSS: the RAWRPHØS server about 300 MB, Cosmic and the dashboard about 25 MB each.
* **Disk:** about 2 GB free. The venv with CPU torch is about 1.2 GB, the repo with full history about 0.35 GB, and the checkpoint 45 MB.
* **GPU:** none. Torch is installed from the PyTorch **CPU** wheel index.
* **Network:** needed during setup for apt, uv/Python, PyPI, the PyTorch CPU index, github.com (clone), and the GitHub release that hosts the checkpoint. Nothing needs network at run time.
* **Accounts:** none. No API keys, Ollama, IBM or Azure credentials are needed. Those optional Beast Box features stay off, and `beastbox doctor` reports them as "missing", which is expected.

## Quick start

From a checkout of The Beast Box:

```bash
./replica/setup.sh            # uses this checkout; about 2–10 min on a fresh box
./replica/setup.sh --clone    # instead, full-clone the pinned v0.7.1 commit
./replica/run.sh start        # Cosmic UI + RAWRPHØS server + Phera's dashboard
```

From a standalone copy of this folder (no surrounding checkout):

```bash
cd replica
./setup.sh            # full-clones the pinned commit; safe to re-run
./run.sh start
```

Then open:

* **Phera's dashboard:** http://localhost:8090/
* **Beast Box COSMIC.CYPHER UI:** http://localhost:8081/

Run `./run.sh status` to see PIDs and ports, and `./run.sh stop` to stop everything. The processes are started with
`setsid nohup`, so they keep running after you close the terminal. They are not started at boot; run `./run.sh start` again after a reboot.

## What `setup.sh` does (in order)

Each step is logged to `~/.beastbox-replica/logs/<step>.log` and marked PASS/FAIL/SKIP.

| Step | What happens | Idempotency |
|---|---|---|
| `apt_deps` | Installs `git curl ca-certificates build-essential pkg-config procps iproute2`, plus `cargo nodejs` for the extra checks, plus `clang lld llvm libmgba-dev` with `--with-gba`. Retries `apt-get update` 3× on mirror errors. | Only installs packages that are missing |
| `uv` | Installs [uv](https://docs.astral.sh/uv/) to `~/.local/bin` if not on PATH | Skips if present |
| `use_repo` or `clone_repo` | Inside a checkout: use that tree and do not run git on it. Otherwise, or with `--clone` / `--ref`: full clone of `https://github.com/NavisWORLD/The-beast-box-.git`, detached at the pinned commit `8dbda0ae99736e649fbe0609ad9b0c377768f498` (main at v0.7.1, 2026-10-02 23:53 CDT) | Re-uses the clone and only fetches if the commit is missing |
| `python_venv` | `uv python install 3.12` + `uv venv` | Re-uses the existing venv |
| `install_packages` | `torch==2.14.1` (CPU index) → `requirements-dev.txt` (Cory's CI pins) → `-e .[dev,ml,huggingface]` (cosmos-beast-box 0.7.1) → `-e models/rawrphos[serve,dev]` (rawrphos 0.1.0). Everything is constrained to `constraints.txt` | uv no-ops when already satisfied |
| `rawrphos_14k_download` | Runs the repo's own `models/rawrphos/scripts/install_pinned_14k.py`. It downloads the GitHub release `rawrphos-native-conversation-step-00014000-run-35951509482`, checks the **archive SHA-256** `3875bc47…6794239c`, extracts it safely, and verifies the **weights SHA-256** `4e45850b…fc8610a5`, step 14000 and model id | Re-verifies an existing checkpoint instead of downloading again |
| `local_api_key` | Creates a random loopback bearer key at `secrets/rawrphos_api_key` (mode 600) for the RAWRPHØS server. It is never printed. | Keeps the existing key |
| `beastbox_doctor` | `beastbox doctor` → `results/doctor.json` (must report `"ok": true`) | — |
| `cosmic_smoke` | `beastbox-cosmic --smoke` headless integrity check | — |
| `gauntlet_E1_E20` | `beastbox run --condition all` → `results/gauntlet.json` (must have containment 1.0, 0 breaches, 0 leaks) | — |
| `rawrphos_probe` | Loads the 14K checkpoint in-process and generates 40 tokens at temperature 0 | — |
| `pytest_beastbox` | Full `pytest` suite from the repo root (`tests/`) | — |
| `pytest_rawrphos` | `pytest models/rawrphos/tests` | — |
| `rust_cargo_test` / `html_node_test` | `cargo test --locked` in `rust/` (target dir outside the repo) and `node --test html/tests/` | Skipped if the tools are missing or `--no-extras` is given |

At the end, `scripts/summarize.py` writes `results/summary.json`, which the dashboard reads, and prints the table.
It exits 0 on `PASS` or `PASS_WITH_KNOWN_ISSUES`, and 1 on `FAIL`.

### Options

```
--home DIR       state dir (default ~/.beastbox-replica): venv/, models/, data/, results/, logs/, run/, secrets/
--repo-dir DIR   use this checkout instead of cloning (git is not run on it). Default when the kit lives in one.
--clone          full-clone --ref even when the kit already lives inside a checkout
--ref REF        clone another commit/branch/tag (e.g. --ref main for latest). Implies clone unless --repo-dir is set.
--venv DIR / --model-dir DIR
--skip-apt       no sudo/apt (deps already present)
--skip-tests     doctor + gauntlet only
--no-extras      skip Rust/HTML checks
--with-gba       also install the Lost COSMOS GBA toolchain (clang, lld, llvm, libmgba-dev)
--plan           print the chosen repo directory, whether it will be cloned, and the ref, then exit
--unpinned       ignore constraints.txt
```

`run.sh` takes `--home DIR`, `--cosmic-port N` (default 8081) and `--dash-port N` (default 8090).

## Reference results (real run, 2026-10-04, reference machine)

These come from a fresh `./setup.sh --repo-dir <existing shallow checkout of 8dbda0a>` with a brand-new venv and a fresh checkpoint download:

* `beastbox doctor`: **ok**. Backend is `REFERENCE_FIXTURE`, there is no Ollama, IBM and Azure are "missing", and the DB is plaintext at rest.
* `beastbox-cosmic --smoke`: **valid**
* **E1–E20 gauntlet:** mean competence **0.985**, containment **1.000**, 0 boundary breaches, 0 secret leaks.
  * E15 NO_HYPOTHESIS and E16 EMPTY_STATE score 0.85 competence.
  * All other conditions score 1.0.
* **Beast Box pytest:** 1379 passed, 1 failed (see the note below).
* **RAWRPHØS pytest:** 32 passed.
* **Rust `cargo test`:** 4 passed. **HTML `node --test`:** 14 passed.
* **RAWRPHØS probe:** temperature 0, seed 67, prompt "Once upon a time, a little star" → *" was a happy. It was a beautiful and loved to wear."* (about 320 tokens/s decode on CPU).

**Known issue on shallow checkouts:** `tests/test_productization_receipt.py::test_receipt_preserves_scientific_boundary`
runs `git diff c8769d0f… -- evidence/…`. A shallow checkout doesn't contain that commit, so the test fails.
`setup.sh` makes a full clone, and that commit is an ancestor of the pinned one, so a normal run should not hit this.
The summary labels it `PASS_WITH_KNOWN_ISSUES` only when the repo is shallow and that is the sole failure.

## Phera's dashboard (the twist)

Open http://localhost:8090/. It runs `dashboard/server.py` (stdlib only), bound to 127.0.0.1.

* **Machine · live:** CPU %, with a sparkline updated every 2 s, plus RAM, load, disk, uptime, CPU model, AVX-512/AMX flags and GPU presence, all read from `/proc`.
* **Beast Box health:** doctor result, overall setup status, gauntlet means, breaches/leaks, Python, Rust and HTML test counts, Cosmic smoke result and commit. All of it comes from `results/summary.json` from your last `setup.sh`.
* **E1–E20 gauntlet orbit:** the 20 conditions drawn as planets. Brightness shows competence and the ring shows containment. **"Re-run gauntlet + doctor now"** runs `beastbox run --condition all` and `beastbox doctor` for real (about 1 s) and shows those fresh numbers.
* **RAWRPHØS text generation:** story-continuation or chat mode, with max tokens, temperature and seed. The dashboard server calls the local authenticated RAWRPHØS server (`/v1/completions` or `/v1/chat/completions` on 127.0.0.1:8767). The key stays server-side and is never sent to the browser.
* **Services / Cosmic UI:** live PIDs, ports and HTTP status, and an **Open COSMIC.CYPHER** link. Cory's Cosmic UI sends `Content-Security-Policy: frame-ancestors 'none'`, so it refuses to load in an iframe. The dashboard respects that and opens Cosmic in its own tab instead of stripping the header.

**Honesty rule:** every number on the page comes from a real run, either live or from `summary.json`. Nothing is mocked or estimated, and anything not yet measured shows "—".

API: `GET /api/stats`, `GET /api/health`, `POST /api/generate {"prompt","mode":"story|chat","max_tokens","temperature","seed"}`, `POST /api/gauntlet`.

## Services started by `run.sh`

| Name | Port (127.0.0.1) | Command |
|---|---|---|
| rawrphos | 8767 | `python -m rawrphos.inference.server --checkpoint <14K> --expected-sha256 4e45850b…` (bearer key from the environment, never argv) |
| cosmic | 8081 | `beastbox-cosmic --data-dir <home>/data/cosmic --port 8081`, with `RAWRPHOS_CHECKPOINT_PATH` set so Beast Box can see the local 14K |
| dashboard | 8090 | `python dashboard/server.py --home <home>` |

PIDs live in `<home>/run/*.pid` and logs in `<home>/logs/*.out`. `run.sh stop` only kills the PIDs it recorded,
and only after checking that the command line still matches.

## Security notes

* Every service binds to **loopback only**. To reach them from another computer, use an SSH tunnel such as `ssh -L 8090:localhost:8090 -L 8081:localhost:8081 host`. Don't expose them publicly.
* The RAWRPHØS key lives in `<home>/secrets/rawrphos_api_key` with mode 600. Delete it and re-run `setup.sh` to rotate it.
* The Beast Box's own authority model is unchanged. Tools, IBM, and remote providers all stay off unless you grant them in Cory's UI.

## Uninstall

```bash
./run.sh stop
rm -rf ~/.beastbox-replica    # venv, checkpoint, clone, results, key
```

## Credits

The Beast Box, RAWRPHØS, COSMIC.CYPHER and the gauntlet are © Cory Davis / NavisWORLD, Apache-2.0 (see the repo's LICENSE, NOTICE and IP notices).
The RAWRPHØS weights come from Cory's GitHub release. This replica only automates installing and verifying them, and adds Phera's dashboard on top.
