# Quantum Beast Starter Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the sealed Beast Box scientific release into a clean, reproducible, local-first starter kit without modifying the sealed scientific evidence or overstating the final result.

**Architecture:** Keep the existing `beastbox` runtime and `beastbox.cypher` model adapters as the only implementation. Add a thin `QUANTUM_BEAST_STARTER/` onboarding layer, a small configuration/logging surface, stricter CI, and a separate productization receipt that continuously checks the scientific anchor `c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f` remains unchanged under `evidence/final-whole-organism-001/`.

**Tech Stack:** Python 3.10-3.12, stdlib JSON/logging/urllib, pytest, GitHub Actions, Docker Compose, existing Ollama / llama.cpp / LM Studio / GGUF adapters, optional Qiskit extras.

**Spec:** `docs/superpowers/specs/2026-08-28-quantum-beast-starter-productization-design.md`

## Global Constraints

- Scientific anchor is exactly `c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f`.
- Public scientific classification remains exactly `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`.
- Do not modify or rewrite `evidence/final-whole-organism-001/`.
- Do not submit new IBM jobs as part of productization.
- Core Beast operation must not require IBM credentials.
- Local model URLs remain loopback-only through existing adapter checks.
- Python support remains 3.10, 3.11, and 3.12 as declared by `pyproject.toml`.
- Preserve optional dependency separation; basic CI must not require Qiskit, Torch, or llama-cpp-python unless a lane explicitly installs them.
- Use genuine focused commits only; no fabricated history, authors, timestamps, or experimental evidence.

---

## File structure

### New files

- `QUANTUM_BEAST_STARTER/README.md` — ten-minute local onboarding path.
- `QUANTUM_BEAST_STARTER/SCIENTIFIC_ANCHOR.md` — immutable result boundary and claim language.
- `QUANTUM_BEAST_STARTER/config/beastbox.example.json` — starter runtime config.
- `QUANTUM_BEAST_STARTER/models/ollama.example.json` — Ollama model profile.
- `QUANTUM_BEAST_STARTER/models/lm-studio.example.json` — LM Studio model profile.
- `QUANTUM_BEAST_STARTER/models/llama-server.example.json` — loopback llama.cpp server profile.
- `QUANTUM_BEAST_STARTER/models/gguf.example.json` — direct GGUF profile.
- `QUANTUM_BEAST_STARTER/docker-compose.yml` — optional application-layer orchestration.
- `beastbox/logging_config.py` — human/JSON logging setup and secret redaction.
- `scripts/productization_receipt.py` — productization receipt generator and sealed-tree guard.
- `tests/test_starter_kit.py` — starter/config/profile contracts.
- `tests/test_logging_config.py` — logging/redaction contracts.
- `tests/test_productization_receipt.py` — receipt/anchor guard tests.
- `requirements-dev.txt` — pinned development/CI dependencies.

### Modified files

- `.env.example` — document verified environment variables only.
- `beastbox/config.py` — environment override helper for starter-owned runtime settings.
- `beastbox/cli.py` — add `starter` command that reports first-run guidance without network calls.
- `pyproject.toml` — add lightweight dev quality tools and coverage configuration.
- `.github/workflows/ci.yml` — canonical quality lane.
- `README.md` — product/research landing-page rewrite.

---

### Task 1: Starter kit skeleton and model profiles

**Files:**
- Create: `QUANTUM_BEAST_STARTER/README.md`
- Create: `QUANTUM_BEAST_STARTER/SCIENTIFIC_ANCHOR.md`
- Create: `QUANTUM_BEAST_STARTER/config/beastbox.example.json`
- Create: `QUANTUM_BEAST_STARTER/models/ollama.example.json`
- Create: `QUANTUM_BEAST_STARTER/models/lm-studio.example.json`
- Create: `QUANTUM_BEAST_STARTER/models/llama-server.example.json`
- Create: `QUANTUM_BEAST_STARTER/models/gguf.example.json`
- Create: `tests/test_starter_kit.py`

**Interfaces:**
- Consumes: `beastbox.config.RuntimeConfig`, `beastbox.cypher.models.ModelSpec`, `beastbox.cypher.models.create_model`.
- Produces: four JSON model profiles parseable by `ModelSpec.from_dict`, one runtime config parseable by `RuntimeConfig`, and user-facing onboarding docs.

- [ ] **Step 1: Write the failing starter profile tests**

```python
import json
from pathlib import Path

from beastbox.config import RuntimeConfig
from beastbox.cypher.models import ModelSpec, create_model

ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "QUANTUM_BEAST_STARTER"


def test_runtime_example_matches_runtime_config_fields():
    raw = json.loads((STARTER / "config" / "beastbox.example.json").read_text())
    cfg = RuntimeConfig(**raw)
    assert cfg.local_model_url.startswith("http://127.0.0.1")
    assert cfg.quantum_heart_mode == "off"


def test_model_profiles_parse_and_stay_local():
    for name in ["ollama", "lm-studio", "llama-server", "gguf"]:
        raw = json.loads((STARTER / "models" / f"{name}.example.json").read_text())
        spec = ModelSpec.from_dict(raw)
        assert spec.alias
        if spec.base_url:
            assert spec.base_url.startswith(("http://127.0.0.1", "http://localhost"))
        if spec.backend != "gguf":
            create_model(spec)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_starter_kit.py -q`
Expected: FAIL because `QUANTUM_BEAST_STARTER/` files do not exist.

- [ ] **Step 3: Add the starter JSON files**

`QUANTUM_BEAST_STARTER/config/beastbox.example.json`:

```json
{
  "data_dir": ".beastbox",
  "memory_db": ".beastbox/reconciliation.sqlite3",
  "evidence_dir": ".beastbox/evidence",
  "proposals_dir": ".beastbox/proposals",
  "local_model_url": "http://127.0.0.1:11434",
  "local_model_name": "my-model",
  "sensory_max_age_seconds": 5.0,
  "heartbeat_every_ticks": 5,
  "quantum_heart_mode": "off",
  "enable_dyn12": true,
  "enable_phos_reference": true,
  "extras": {}
}
```

`ollama.example.json` uses backend `ollama`, model `my-model`, base URL `http://127.0.0.1:11434`.

`lm-studio.example.json` uses backend `lm-studio`, model `local-model`, base URL `http://127.0.0.1:1234`.

`llama-server.example.json` uses backend `llama.cpp-server`, model `local`, base URL `http://127.0.0.1:8080`.

`gguf.example.json` uses backend `gguf`, model `./models/model.gguf`, no `base_url`, context `8192`, temperature `0.2`, max tokens `2048`, and options `{"n_gpu_layers": 0}`.

- [ ] **Step 4: Write starter docs**

`QUANTUM_BEAST_STARTER/README.md` must show these exact paths:

```bash
python -m venv .venv
pip install -e .
beastbox init
beastbox doctor
cosmic.cypher-cli models scan-ollama
cosmic.cypher-cli beast <alias>
```

It must state IBM is optional and model download time is excluded from the ten-minute onboarding target.

`SCIENTIFIC_ANCHOR.md` must include the exact anchor SHA and exact classification from Global Constraints and state `fresh_ibm_jobs_submitted: false` for this productization effort.

- [ ] **Step 5: Run starter tests**

Run: `pytest tests/test_starter_kit.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add QUANTUM_BEAST_STARTER tests/test_starter_kit.py
git commit -m "feat(starter): add local model onboarding kit"
```

---

### Task 2: Configuration contract and environment overrides

**Files:**
- Modify: `beastbox/config.py`
- Modify: `.env.example`
- Modify: `beastbox/cli.py`
- Modify: `tests/test_starter_kit.py`

**Interfaces:**
- Produces: `RuntimeConfig.with_env(environ: Mapping[str, str] | None = None) -> RuntimeConfig` and `beastbox starter` CLI output.

- [ ] **Step 1: Add failing environment override tests**

```python
from beastbox.config import RuntimeConfig


def test_runtime_config_environment_overrides():
    cfg = RuntimeConfig(local_model_name="original").with_env({
        "BEASTBOX_MODEL_NAME": "my-model",
        "BEASTBOX_MODEL_URL": "http://127.0.0.1:1234",
        "BEASTBOX_QUANTUM_HEART_MODE": "off",
    })
    assert cfg.local_model_name == "my-model"
    assert cfg.local_model_url == "http://127.0.0.1:1234"
    assert cfg.quantum_heart_mode == "off"
```

- [ ] **Step 2: Run test and verify failure**

Run: `pytest tests/test_starter_kit.py::test_runtime_config_environment_overrides -q`
Expected: FAIL because `RuntimeConfig.with_env` does not exist.

- [ ] **Step 3: Implement minimal environment override support**

In `beastbox/config.py`, import `os`, `replace` from `dataclasses`, and `Mapping` from `typing`; add:

```python
    def with_env(self, environ: Mapping[str, str] | None = None) -> "RuntimeConfig":
        env = os.environ if environ is None else environ
        values: dict[str, object] = {}
        if env.get("BEASTBOX_MODEL_NAME"):
            values["local_model_name"] = env["BEASTBOX_MODEL_NAME"]
        if env.get("BEASTBOX_MODEL_URL"):
            values["local_model_url"] = env["BEASTBOX_MODEL_URL"]
        if env.get("BEASTBOX_QUANTUM_HEART_MODE"):
            values["quantum_heart_mode"] = env["BEASTBOX_QUANTUM_HEART_MODE"]
        return replace(self, **values)
```

Update the `chat` path in `beastbox/cli.py` to call `RuntimeConfig.load(args.config).with_env()` before constructing the provider.

- [ ] **Step 4: Expand `.env.example`**

Keep the IBM variables and add only:

```dotenv
BEASTBOX_MODEL_NAME=my-model
BEASTBOX_MODEL_URL=http://127.0.0.1:11434
BEASTBOX_QUANTUM_HEART_MODE=off
```

with comments that IBM variables are optional host-side research credentials and must not be committed with real values.

- [ ] **Step 5: Add `beastbox starter` guidance**

Add a parser with `sub.add_parser("starter", help="show the shortest safe path to a first local Beast conversation")` and a handler that prints JSON containing keys `steps`, `ibm_required`, `scientific_anchor`, and `classification`, where `ibm_required` is `False` and the anchor/classification match Global Constraints.

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_starter_kit.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add beastbox/config.py beastbox/cli.py .env.example tests/test_starter_kit.py
git commit -m "feat(config): add starter environment contract"
```

---

### Task 3: Structured logging with redaction

**Files:**
- Create: `beastbox/logging_config.py`
- Create: `tests/test_logging_config.py`

**Interfaces:**
- Produces: `configure_logging(json_output: bool = False, level: int = logging.INFO) -> logging.Logger` and `redact_mapping(values: Mapping[str, object]) -> dict[str, object]`.

- [ ] **Step 1: Write failing logging tests**

```python
import json
import logging

from beastbox.logging_config import configure_logging, redact_mapping


def test_redact_mapping_masks_secrets():
    assert redact_mapping({"IBM_QUANTUM_TOKEN": "secret", "event": "boot"}) == {
        "IBM_QUANTUM_TOKEN": "***REDACTED***",
        "event": "boot",
    }


def test_json_logging_emits_stable_event(capsys):
    logger = configure_logging(json_output=True, level=logging.INFO)
    logger.info("starter_ready", extra={"event_data": {"backend": "ollama"}})
    record = json.loads(capsys.readouterr().err.strip())
    assert record["message"] == "starter_ready"
    assert record["event_data"]["backend"] == "ollama"
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/test_logging_config.py -q`
Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement logging module**

Use stdlib `logging`, `json`, and `datetime`. Redact keys whose uppercase form contains any of `TOKEN`, `SECRET`, `PASSWORD`, `API_KEY`, or `PRIVATE_KEY`. JSON records must include `timestamp`, `level`, `logger`, `message`, and redacted `event_data` when supplied. The human formatter remains `%(levelname)s %(name)s %(message)s`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_logging_config.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add beastbox/logging_config.py tests/test_logging_config.py
git commit -m "feat(logging): add structured runtime logging"
```

---

### Task 4: Reproducible development dependencies and canonical CI

**Files:**
- Create: `requirements-dev.txt`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: one canonical quality lane that installs a pinned lightweight dev toolchain and runs tests, lint, type checks, package smoke, starter guard, and evidence immutability guard.

- [ ] **Step 1: Define pinned dev toolchain**

Create `requirements-dev.txt` with exact pins:

```text
pytest==8.4.2
coverage==7.10.6
ruff==0.12.12
mypy==1.17.1
build==1.3.0
```

- [ ] **Step 2: Add quality configuration**

In `pyproject.toml`, set `dev = ["pytest>=8.0", "coverage>=7.0", "ruff>=0.12", "mypy>=1.17"]`.

Add:

```toml
[tool.ruff]
target-version = "py310"
line-length = 120

[tool.mypy]
python_version = "3.10"
check_untyped_defs = true
warn_unused_ignores = true
files = ["beastbox/config.py", "beastbox/providers.py", "beastbox/cypher/models.py", "beastbox/logging_config.py"]

[tool.coverage.run]
source = ["beastbox"]

[tool.coverage.report]
fail_under = 0
show_missing = true
```

The initial `fail_under = 0` is intentional until CI measures the reproducible baseline; do not invent a higher floor in this first productization commit.

- [ ] **Step 3: Rewrite canonical CI steps**

Keep Python 3.10 and 3.12 test matrix. Install `-r requirements-dev.txt`, then `pip install -e .` for the core lane. Run:

```bash
ruff check beastbox tests/test_starter_kit.py tests/test_logging_config.py tests/test_productization_receipt.py
mypy
coverage run -m pytest
coverage report
python scripts/productization_receipt.py --check-only
```

Keep package-smoke and add `beastbox starter` to entry-point verification.

Add an explicit immutable-evidence shell step:

```bash
git diff --exit-code c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f -- evidence/final-whole-organism-001/
```

- [ ] **Step 4: Validate config syntactically**

Run: `python -m tomllib pyproject.toml` is not a valid CLI, so instead run:

```bash
python -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); print('pyproject ok')"
```

Expected: `pyproject ok`.

- [ ] **Step 5: Run focused quality checks**

Run:

```bash
ruff check beastbox/config.py beastbox/providers.py beastbox/cypher/models.py beastbox/logging_config.py tests/test_starter_kit.py tests/test_logging_config.py
mypy
pytest tests/test_starter_kit.py tests/test_logging_config.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add requirements-dev.txt pyproject.toml .github/workflows/ci.yml
git commit -m "ci: establish canonical product quality lane"
```

---

### Task 5: Productization receipt and scientific anchor guard

**Files:**
- Create: `scripts/productization_receipt.py`
- Create: `tests/test_productization_receipt.py`
- Create: `QUANTUM_BEAST_STARTER/productization-receipt.example.json`

**Interfaces:**
- Produces: `build_receipt(repo_root: Path, head_sha: str) -> dict[str, object]`, `hash_file(path: Path) -> str`, and CLI flags `--check-only`, `--head-sha`, `--out`.

- [ ] **Step 1: Write failing receipt tests**

```python
from pathlib import Path

from scripts.productization_receipt import ANCHOR_SHA, CLASSIFICATION, build_receipt


def test_receipt_preserves_scientific_boundary(tmp_path: Path):
    receipt = build_receipt(Path.cwd(), "abc123")
    assert receipt["scientific_anchor"] == ANCHOR_SHA
    assert receipt["scientific_classification"] == CLASSIFICATION
    assert receipt["fresh_ibm_jobs_submitted"] is False
    assert receipt["productization_commit"] == "abc123"
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/test_productization_receipt.py -q`
Expected: FAIL because script does not exist.

- [ ] **Step 3: Implement receipt builder**

Constants:

```python
ANCHOR_SHA = "c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f"
CLASSIFICATION = "ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED"
```

`build_receipt` must hash these files when present:

- `QUANTUM_BEAST_STARTER/README.md`
- `QUANTUM_BEAST_STARTER/SCIENTIFIC_ANCHOR.md`
- `QUANTUM_BEAST_STARTER/config/beastbox.example.json`
- `QUANTUM_BEAST_STARTER/docker-compose.yml`
- `README.md`

It must include supported backends `ollama`, `gguf`, `llama.cpp-server`, `lm-studio`, `openai-compatible` and `fresh_ibm_jobs_submitted: false`.

For `--check-only`, run `git diff --quiet ANCHOR_SHA -- evidence/final-whole-organism-001/` via `subprocess.run(..., check=False)` and exit nonzero if evidence differs.

- [ ] **Step 4: Run receipt tests**

Run: `pytest tests/test_productization_receipt.py -q`
Expected: PASS.

- [ ] **Step 5: Generate example receipt**

Run:

```bash
python scripts/productization_receipt.py --head-sha local-productization-example --out QUANTUM_BEAST_STARTER/productization-receipt.example.json
```

Expected: JSON file with the constants above and `fresh_ibm_jobs_submitted` false.

- [ ] **Step 6: Commit**

```bash
git add scripts/productization_receipt.py tests/test_productization_receipt.py QUANTUM_BEAST_STARTER/productization-receipt.example.json
git commit -m "feat(release): add scientific anchor product receipt"
```

---

### Task 6: Docker Compose starter

**Files:**
- Create: `QUANTUM_BEAST_STARTER/docker-compose.yml`
- Modify: `tests/test_starter_kit.py`

**Interfaces:**
- Produces: an optional app profile that never embeds credentials or downloads a model automatically.

- [ ] **Step 1: Add failing Compose contract test**

```python

def test_compose_does_not_embed_ibm_credentials():
    text = (STARTER / "docker-compose.yml").read_text()
    assert "IBM_QUANTUM_TOKEN=" not in text
    assert "127.0.0.1" in text or "host.docker.internal" in text
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/test_starter_kit.py::test_compose_does_not_embed_ibm_credentials -q`
Expected: FAIL because Compose file does not exist.

- [ ] **Step 3: Add Compose file**

Create a Compose v2 file with service `beastbox` that builds from repository root, runs `beastbox doctor --ollama-url http://host.docker.internal:11434`, adds `host.docker.internal:host-gateway`, mounts `./runtime:/work/.beastbox`, and reads optional environment from `../.env` only if the user creates it. Do not include IBM credential values in the YAML.

- [ ] **Step 4: Validate**

Run when Compose is available:

```bash
docker compose -f QUANTUM_BEAST_STARTER/docker-compose.yml config
```

Expected: exit 0. If Docker is unavailable locally, CI keeps the text contract test and the release note records Compose runtime validation as not executed locally rather than fabricating success.

- [ ] **Step 5: Commit**

```bash
git add QUANTUM_BEAST_STARTER/docker-compose.yml tests/test_starter_kit.py
git commit -m "feat(starter): add optional compose profile"
```

---

### Task 7: README product/research landing page

**Files:**
- Modify: `README.md`
- Modify: `QUANTUM_BEAST_STARTER/README.md`

**Interfaces:**
- Produces: a front page that separates verified engineering results from hypotheses and makes the starter path obvious.

- [ ] **Step 1: Preserve the existing factual model backend claims**

Keep references to Ollama, direct GGUF through `llama-cpp-python`, llama.cpp server, LM Studio, and loopback OpenAI-compatible endpoints because they are implemented by `beastbox/cypher/models.py`.

- [ ] **Step 2: Put the starter path before deep architecture**

The first major sections must be:

1. What The Beast Box is.
2. Final whole-organism result.
3. What it did not establish.
4. Ten-minute local quick start.
5. Build your own Quantum Beast.
6. Optional IBM Quantum research path.
7. Scientific evidence/reproduction.
8. Development and contribution.

- [ ] **Step 3: Use exact scientific language**

Include the exact anchor SHA and classification from Global Constraints. Explicitly state that no verified IBM/quantum resource-to-Zeref causal consumer edge was established and that IBM is not required for ordinary Beast operation.

- [ ] **Step 4: Verify commands and wording**

Run:

```bash
beastbox --help
beastbox starter
cosmic.cypher-cli --help
pytest tests/test_starter_kit.py -q
```

Expected: all commands exit 0; starter tests pass.

- [ ] **Step 5: Commit**

```bash
git add README.md QUANTUM_BEAST_STARTER/README.md
git commit -m "docs: make Quantum Beast starter the public entry point"
```

---

### Task 8: Full verification and final productization receipt

**Files:**
- Modify: `QUANTUM_BEAST_STARTER/productization-receipt.example.json` or create final release receipt path `QUANTUM_BEAST_STARTER/productization-receipt.json`.

**Interfaces:**
- Consumes all prior tasks.
- Produces final verified productization branch state.

- [ ] **Step 1: Run immutable scientific evidence guard**

Run:

```bash
git diff --exit-code c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f -- evidence/final-whole-organism-001/
```

Expected: no output, exit 0.

- [ ] **Step 2: Run core test suite**

Run: `pytest -q`
Expected: PASS. Any pre-existing unrelated failure must be diagnosed and documented; do not hide or delete it.

- [ ] **Step 3: Run quality checks**

Run:

```bash
ruff check beastbox tests/test_starter_kit.py tests/test_logging_config.py tests/test_productization_receipt.py
mypy
coverage run -m pytest
coverage report
python -m build
```

Expected: all configured checks pass. Record measured coverage; only after observing it may a future commit set a nonzero `fail_under` floor at or below the reproducible baseline.

- [ ] **Step 4: Run package smoke**

Create a fresh virtual environment, install the built wheel, and run:

```bash
beastbox --help
beastbox starter
cosmic.cypher-cli --help
cosmic-cypher --help
cypher --help
```

Expected: exit 0 for every command.

- [ ] **Step 5: Generate final receipt from actual HEAD**

Run:

```bash
python scripts/productization_receipt.py --check-only
python scripts/productization_receipt.py --head-sha "$(git rev-parse HEAD)" --out QUANTUM_BEAST_STARTER/productization-receipt.json
```

Expected: receipt contains actual productization HEAD, anchor SHA, exact classification, supported backend list, file hashes, and `fresh_ibm_jobs_submitted: false`.

- [ ] **Step 6: Commit receipt**

```bash
git add QUANTUM_BEAST_STARTER/productization-receipt.json
git commit -m "release(starter): seal Quantum Beast productization receipt"
```

- [ ] **Step 7: Verify branch ancestry**

Run:

```bash
git merge-base --is-ancestor c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f HEAD
git diff --exit-code c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f -- evidence/final-whole-organism-001/
```

Expected: both exit 0.

- [ ] **Step 8: Open productization PR**

Open a PR from `quantum-beast-starter-productization-001` into the intended integration branch only after CI is green. The PR body must state the scientific anchor, exact final classification, that no new IBM jobs were submitted, and that sealed evidence is unchanged.
