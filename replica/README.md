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

The virtualenv, checkpoint, Ollama files, results, and the RAWRPHØS loopback key are written under `~/.beastbox-replica` (or `--home`), outside the repository. The key file is created at runtime with mode 600 and is never committed.

```
replica/
├── setup.sh             idempotent installer + verifier, prints a PASS/FAIL summary
├── run.sh               start | stop | restart | status of the background stack
├── constraints.txt      exact Python package versions from the verified reference run
├── scripts/summarize.py collects real results into results/summary.json
├── scripts/ollama_registry_pull.py  SHA-256-verified fallback for `ollama pull` behind fake-IP DNS
├── scripts/cosmic_client.py         tiny loopback client for the Cosmic owner API
├── scripts/cosmic_feature_sweep.py  exercises every Cosmic UI feature/setting via its API
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
* **Accounts:** none. No API keys, IBM or Azure credentials are needed. Those optional Beast Box features stay off, and `beastbox doctor` reports them as "missing", which is expected.
* **Optional real LLM chat (`--with-ollama`):** about 3.1 GB more disk (Ollama CPU runtime ~60 MB, `qwen2.5:1.5b` 0.99 GB, `qwen2.5:3b` 1.93 GB) and about 2.5 GB of free RAM while `qwen2.5:3b` is loaded. Only one model is held in RAM at a time. Speed is roughly 45 tok/s for 1.5B and 20–30 tok/s for 3B on the reference CPU. `--with-qc67` adds about 150 MB of disk and about 430 MB of RAM.

## Quick start

From a checkout of The Beast Box:

```bash
./replica/setup.sh            # uses this checkout; about 2–10 min on a fresh box
./replica/setup.sh --clone    # instead, full-clone the pinned v0.7.1 commit
./replica/setup.sh --with-ollama --ollama-models "qwen2.5:1.5b"
./replica/run.sh start        # Cosmic UI + RAWRPHØS + dashboard; Ollama too if it was installed
```

From a standalone copy of this folder (no surrounding checkout):

```bash
cd replica
./setup.sh            # full-clones the pinned commit; safe to re-run
./setup.sh --with-ollama --with-qc67
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
| `rust_cargo_test` / `html_node_test` | `cargo test --locked` in `rust/` (target dir outside the repo) and `node --test` on each `html/tests/*.js` file. The files are passed explicitly so Node 22 runs them; Debian/Ubuntu's `nodejs` package accepts a directory, but Node 22 tries to load that directory as a module. | Skipped if the tools are missing or `--no-extras` is given |
| `ollama_install` / `ollama_models` / `ollama_chat_probe` | only with `--with-ollama`: CPU-only Ollama into `<home>/ollama`, pull the models (verified fallback if `ollama pull` is blocked), `beastbox doctor --provider ollama`, and a 2-turn `beastbox runtime chat` memory probe | Reuses an existing binary and skips models already pulled |
| `qc67_install` | only with `--with-qc67`: `models/qc67/install_pinned.py` (pinned HF revision, SHA-256 per file) + `tiktoken` | Re-verifies an existing install |

At the end, `scripts/summarize.py` writes `results/summary.json`, which the dashboard reads, and prints the table.
It exits 0 on `PASS` or `PASS_WITH_KNOWN_ISSUES`, and 1 on `FAIL`.

### Options

```
--home DIR       state dir (default ~/.beastbox-replica): venv/, models/, data/, results/, logs/, run/, secrets/, ollama/
--repo-dir DIR   use this checkout instead of cloning (git is not run on it). Default when the kit lives in one.
--clone          full-clone --ref even when the kit already lives inside a checkout
--ref REF        clone another commit/branch/tag (e.g. --ref main for latest). Implies clone unless --repo-dir is set.
--plan           print the chosen repo directory, whether it will be cloned, and the ref, then exit
--venv DIR / --model-dir DIR
--skip-apt       no sudo/apt (deps already present)
--skip-tests     doctor + gauntlet only
--no-extras      skip Rust/HTML checks
--with-gba       also install the Lost COSMOS GBA toolchain (clang, lld, llvm, libmgba-dev)
--unpinned       ignore constraints.txt
--with-ollama    install Ollama (CPU-only, user-local under <home>/ollama) + pull models, then doctor + a 2-turn memory probe
--ollama-models "a b"   which models to pull (default "qwen2.5:1.5b qwen2.5:3b"; implies --with-ollama)
--with-qc67      install Cory's pinned QC67 PHOS/SAMGO weights (~150 MB) + tiktoken for the :8771 sidecar
```

`run.sh` takes `--home DIR`, `--cosmic-port N` (default 8081), `--dash-port N` (default 8090) and `--no-ollama`
(leave Ollama alone on start/stop). Use `./run.sh ollama start|stop|status` and `./run.sh qc67 start|stop|status` to manage just
those servers. If another Ollama is already listening on :11434, `run.sh` uses it and never stops it.

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
* **Brains · pick one:** a live list of every backend Beast Box can use right now. That covers the reference fixture, each installed Ollama
  model (with size, quantization and whether it's in RAM), RAWRPHØS 14K, QC67 PHOS/SAMGO, and LM Studio / llama.cpp servers if they're running.
  It also lists the blocked cloud and HF options with the reason they're blocked. Clicking a brain switches Cory's Cosmic runtime to it.
* **Talk to the Beast:** a chat panel backed by Cosmic's own durable runtime. It shows the same conversation as the Cosmic UI. Each answer is
  labelled with the brain that wrote it, and you can expand the durable memories retrieved for it. A gold marker shows each brain switch.
* **Services / Cosmic UI:** live PIDs, ports and HTTP status, and an **Open COSMIC.CYPHER** link. Cory's Cosmic UI sends `Content-Security-Policy: frame-ancestors 'none'`, so it refuses to load in an iframe. The dashboard respects that and opens Cosmic in its own tab instead of stripping the header.

**Honesty rule:** every number on the page comes from a real run, either live or from `summary.json`. Nothing is mocked or estimated, and anything not yet measured shows "—".

API: `GET /api/stats`, `GET /api/health`, `POST /api/generate {"prompt","mode":"story|chat","max_tokens","temperature","seed"}`, `POST /api/gauntlet`,
`GET /api/backends`, `POST /api/brain {"id"}`, `POST /api/chat {"text","id"?}`, `GET /api/conversation`.
Chat and switching go through Cosmic (`/api/provider`, `/api/chat`, `/api/conversation`), so there is only one substrate. The dashboard reads
Cosmic's per-session CSRF token from Cosmic's own loopback page on the server side. It never reaches the dashboard's browser.

## Services started by `run.sh`

| Name | Port (127.0.0.1) | Command |
|---|---|---|
| ollama (optional) | 11434 | `<home>/ollama/bin/ollama serve` with `OLLAMA_HOST=127.0.0.1:11434`, `OLLAMA_MODELS=<home>/ollama/models`, `OLLAMA_MAX_LOADED_MODELS=1` |
| rawrphos | 8767 | `python -m rawrphos.inference.server --checkpoint <14K> --expected-sha256 4e45850b…` (bearer key from the environment, never argv) |
| qc67 (optional) | 8771 | `python -m models.qc67.inference.server --root <home>/models/qc67-originals` (same bearer key, from the environment) |
| cosmic | 8081 | `beastbox-cosmic --data-dir <home>/data/cosmic --port 8081`, with `RAWRPHOS_CHECKPOINT_PATH` set so Beast Box can see the local 14K |
| dashboard | 8090 | `python dashboard/server.py --home <home>` |

PIDs live in `<home>/run/*.pid` and logs in `<home>/logs/*.out`. `run.sh stop` only kills the PIDs it recorded,
and only after checking that the command line still matches.

## Brains: talking to it and swapping models

The Beast Box keeps **one durable substrate** (memory, checkpoints, provenance) and treats the language model as a
replaceable "brain". Out of the box the active brain is the **COSMOS reference fixture**. It is not an LLM; it just echoes
the composed prompt and retrieved memory. For real conversation, install Ollama and pull a small model:

```bash
./setup.sh --skip-tests --no-extras --with-ollama --with-qc67   # or add the flags to a normal run
./run.sh restart                                                  # now also starts ollama (:11434) and qc67 (:8771)
```

`--with-ollama` installs the official Ollama release archive (the same file `ollama.com/install.sh` downloads) into
`<home>/ollama/`. It extracts only the CPU runtime, which skips the multi-GB CUDA/ROCm libraries, and it doesn't use sudo or systemd.
After that it pulls `qwen2.5:1.5b` (0.99 GB) and `qwen2.5:3b` (1.93 GB, Beast Box's own default model name). To choose
other models, use `--ollama-models "a b"`.
If `ollama pull` fails with `redirect target not allowed … resolves to non-public 198.18.x.x`, the cause is a proxy or sandbox
that uses fake-IP DNS. In that case `scripts/ollama_registry_pull.py` fetches the same public manifest and blobs, checks every
SHA-256 against the manifest, and stores them exactly where `ollama pull` would.

### Backends Beast Box supports

| Backend | How Beast Box talks to it | On this box |
|---|---|---|
| COSMOS reference fixture | built-in `ReferenceTextProvider` (`kind: reference`) | ✅ always. It echoes context and is not an LLM. |
| **Ollama** (local) | `LocalOllamaProvider`, `POST /api/generate`, **loopback URLs only** (`kind: ollama`) | ✅ `qwen2.5:1.5b`, `qwen2.5:3b` |
| **RAWRPHØS 14K** (Cory's 3.9M model) | OpenAI-compatible (`kind: compatible`, `http://127.0.0.1:8767/v1`, model `rawrphos-native`, key env `RAWRPHOS_API_KEY`) | ✅ It's a tiny story model capped at 64 tokens, so it doesn't follow chat. |
| **QC67 PHOS / SAMGO** originals | OpenAI-compatible sidecar `http://127.0.0.1:8771/v1`, models `qc67-phos` and `qc67-samgo`, same key | ✅ (`--with-qc67`, ~150 MB). Experimental. It sees **only your latest message**, not memory. |
| LM Studio / llama.cpp server / any OpenAI-compatible server on loopback | `CompatibleChatProvider` (`http://127.0.0.1:1234/v1`, `:8080/v1`, …) | ⚪ supported, but nothing is running here. The dashboard lists them when they are. |
| GGUF via `cosmic-cypher` / `llama-cpp-python` | COSMIC.CYPHER coding-agent CLI registry (`cypher models add --backend gguf…`) | ⚪ not installed |
| Cloud APIs (OpenAI, Ollama Cloud `https://ollama.com/v1`, OpenRouter, …) | `compatible` + `allow_remote: true` + HTTPS + key **env-var name** + a `cloud` authority grant | ⛔ needs your API key in Cosmic's environment |
| RAWRPHØS 12K on Cory's private HF ZeroGPU Space | `kind: hf_space`, exact pinned Space only | ⛔ needs Cory's HF token from his owner vault, which isn't wired into `beastbox-cosmic` |

`scripts/productization_receipt.py: SUPPORTED_BACKENDS = ["ollama", "gguf", "llama.cpp-server", "lm-studio", "openai-compatible"]`
(checked by `tests/test_productization_receipt.py`).

### How switching works

* **Cosmic UI:** go to *Brain Bay*, choose a Kind (Reference / Ollama / OpenAI-compatible), fill in Model, Base URL and the API-key **env var name**, then press *CLOCK IN BRAIN*.
  This saves `<data>/cosmic-provider.json`. Changing the brain identity **revokes every authority grant** and stops the activation queue.
  Memory and checkpoints are untouched (`substrate_preserved: true`). There is no silent fallback: a failing brain returns an error.
* **Cosmic API:** `POST /api/provider {kind, model, base_url, allow_remote, api_key_env}`. You can also pass `"provider": {...}` inside `POST /api/chat`.
* **Phera's dashboard:** the *Brains* panel lists every backend live, including installed Ollama models, whether each is in RAM, RAWRPHØS, QC67, and blocked cloud options with the reason.
  Click one to switch, then chat in *Talk to the Beast*. Every answer is labelled with the brain that produced it, and you can expand the durable memories that were retrieved for it.
* **Engine CLI:** `beastbox runtime chat --data-dir D --provider ollama --model qwen2.5:3b "…"`, or
  `--provider compatible --model rawrphos-native --url http://127.0.0.1:8767/v1 --api-key-env RAWRPHOS_API_KEY`. Any later
  call on the same `--data-dir` with a different brain reads the same memory.
* `beastbox doctor --provider ollama --model qwen2.5:3b` reports `backend: VERIFIED` once the model is pulled.

Memory is carried by Beast Box's **retrieval** layer, not by the model. Each turn's prompt contains the top-5 lexically matching
durable records (your earlier turns and the brains' answers). A small model can still misread them. In testing, `qwen2.5:1.5b`
sometimes speaks *as* you, and `llama3.2:1b` / `gemma3:1b` refused or ignored the memory in Beast Box's prompt format, so they
were dropped in favour of `qwen2.5:3b`.

Memory demo, run through Cosmic's API on 2026-10-04. Full transcript: `results/brain_switch_transcript.json`.

```
[qwen2.5:1.5b] you: Hi! I'm Zeref. I'm writing a story about a dragon named Ember who guards the Moon Library.
[qwen2.5:3b  ] you: What's my name, and what's the dragon in my story called?  -> "Your name is Zeref, and the dragon in your story is called Ember."
[qwen2.5:3b  ] you: New detail for my story: Ember's only fear is thunderstorms.
[rawrphos    ] you: Tell me a short story about Ember the dragon.             -> " You're welcome. I hope you find the best time to find."
[qc67-samgo  ] you: Ember the dragon guards the Moon Library and fears thunderstorms. -> (wikitext-style babble)
[qwen2.5:1.5b] you: In my story, what is Ember afraid of, and what does she guard?  -> "In your story, Ember is afraid of thunderstorms and guards the Moon Library."
[qwen2.5:3b  ] you: Summarize everything you remember about me and my story. -> "…your name is Zeref … Ember the dragon is the guardian of the Moon Library. Ember's only fear is thunderstorms."
same system_id on every turn, substrate_preserved=true, checkpoint sequence 1→7
```

## COSMIC.CYPHER UI features: status on this box

`scripts/cosmic_feature_sweep.py --port 8082 --workspace <scratch git repo> --out results/cosmic_features.json` drives every
UI action through the same HTTP API the page uses. **Run it against a scratch Cosmic instance**, because it grants authority and writes test
memories. Last run: **116/116 behaved as designed** (allowed calls succeed, guarded calls are refused with the documented reason).

| UI area | Works here | Needs something external |
|---|---|---|
| ORBIT, readiness, Memory Vault, Synapse Trace, Signals, Feature truth matrix | ✅ | – |
| Brain Bay: Reference / Ollama / OpenAI-compatible (RAWRPHØS, QC67), conversation, inline switch | ✅ | – |
| Brain Bay: remote HTTPS endpoints / HF Space | guarded correctly (403 without `cloud`; fails closed, before any network call, without a key) | your API key env var, or Cory's HF vault token |
| Authority: all 10 grants (camera, cloud, device_memory, external_integrations, filesystem, microphone, quantum_live, repo_write, sensors, tools), revoke, MASTER STOP | ✅ | – |
| Reality: authorized sensor observation, queue observation; activation queue resume / run / stop / cancel / maintenance | ✅ | physical sensors are separate hardware |
| Vision / Listen | ✅ API path (bounded feature events) | a real camera / microphone in the browser (`getUserMedia`); none on this headless box |
| Voice (browser TTS) | browser-only `speechSynthesis` | an audio device; not testable headless |
| Files / context: temporary attachment, conversation context, workspace knowledge, persistent memory (confirm), remove | ✅ | – |
| Workspace: allow / select / tree / repo status / read / search / diff preview / write with backup / 3 read-only git commands | ✅ (confined to the selected root; `../` and arbitrary commands refused) | – |
| Q-Bay: IBM hardware / Azure IonQ simulator | ⛔ 503 `Missing provider configuration` | `IBM_QUANTUM_TOKEN`, `IBM_QUANTUM_BACKEND`, `IBM_QUANTUM_INSTANCE` / `AZURE_QUANTUM_RESOURCE_ID`, `AZURE_QUANTUM_LOCATION`, `AZURE_QUANTUM_TARGET` (+ Azure login) |
| Connections (IBM/Azure config status) | ✅ (reports "missing") | same credentials |
| Settings / Storage: status, export v1, sealed v2 export (passphrase), verify, import to a new dir | ✅ | – |
| Launcher settings: `--smoke`, `--demo`, `--profile/--profiles-home`, loopback-only `--host`, `BEASTBOX_CLOSED_LOOP_ENABLED`, `BEASTBOX_UNICODE_NFC_ENABLED`, `BEASTBOX_WORKSPACE_ROOTS` | ✅ | – |

## Security notes

* Every service binds to **loopback only**, including Ollama (`OLLAMA_HOST=127.0.0.1:11434`) and the QC67 sidecar. Beast Box itself refuses non-loopback Ollama URLs. To reach them from another computer, use an SSH tunnel such as `ssh -L 8090:localhost:8090 -L 8081:localhost:8081 host`. Don't expose them publicly.
* The RAWRPHØS key lives in `<home>/secrets/rawrphos_api_key` with mode 600. Delete it and re-run `setup.sh` to rotate it.
* The Beast Box's own authority model is unchanged. Tools, IBM, and remote providers all stay off unless you grant them in Cory's UI.

## Uninstall

```bash
./run.sh stop
rm -rf ~/.beastbox-replica    # venv, checkpoint, clone, results, key, ollama/ (binary + models), qc67 weights
```

## Credits

The Beast Box, RAWRPHØS, COSMIC.CYPHER and the gauntlet are © Cory Davis / NavisWORLD, Apache-2.0 (see the repo's LICENSE, NOTICE and IP notices).
The RAWRPHØS weights come from Cory's GitHub release. This replica only automates installing and verifying them, and adds Phera's dashboard on top.
