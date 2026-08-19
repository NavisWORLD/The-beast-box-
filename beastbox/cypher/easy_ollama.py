from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

DEFAULT_BASE_MODEL = os.environ.get("ZEREF_BASE_MODEL", "qwen2.5:1.5b")
DEFAULT_PROFILE = os.environ.get("ZEREF_OLLAMA_PROFILE", "zeref")
DEFAULT_URL = "http://127.0.0.1:11434"


def default_user_config_path() -> Path:
    root = Path(os.environ.get("ZEREF_HOME", Path.home() / ".cosmos-zeref")).expanduser()
    return root / "beastbox.json"


def load_zeref_runtime_config(path: str | Path):
    from ..config import RuntimeConfig

    p = Path(path).expanduser()
    if p.exists():
        return RuntimeConfig.load(p)

    root = p.parent.resolve()
    cfg = RuntimeConfig(
        data_dir=str(root / "data"),
        memory_db=str(root / "reconciliation.sqlite3"),
        evidence_dir=str(root / "evidence"),
        proposals_dir=str(root / "proposals"),
        local_model_url=DEFAULT_URL,
        local_model_name=DEFAULT_PROFILE,
    )
    cfg.save(p)
    return cfg


def make_zeref_modelfile(base_model: str = DEFAULT_BASE_MODEL) -> str:
    return (
        f"FROM {base_model}\n"
        "PARAMETER temperature 0.7\n"
        "PARAMETER num_ctx 8192\n\n"
        'SYSTEM """You are Zeref, the local conversational profile used by an owner-controlled COSMOS/CST runtime.\n'
        "COSMOS may supply retrieved memory, user preferences, measured state, and bounded tool results as context.\n"
        "Answer naturally and directly. Do not pretend the underlying language-model weights are retrained by ordinary chat.\n"
        "Durable growth comes from the COSMOS memory/state layer unless the owner explicitly runs a separate fine-tuning workflow.\n"
        'Do not claim that persistence, autonomy, quantum provenance, or self-description proves consciousness."""\n'
    )


def _run_checked(command: list[str], *, timeout: float | None = None) -> None:
    try:
        subprocess.run(command, check=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Ollama is not installed or is not on PATH. Install Ollama, then run `zeref` again."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Ollama command failed: {' '.join(command)}") from exc


def pull_ollama_model(model: str, *, runner: Callable[..., None] = _run_checked) -> None:
    print(f"Zeref setup: downloading {model} with Ollama...")
    runner(["ollama", "pull", model], timeout=None)


def create_ollama_profile(
    name: str,
    modelfile_text: str,
    *,
    runner: Callable[..., None] = _run_checked,
) -> None:
    print(f"Zeref setup: creating Ollama profile {name!r}...")
    path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".Modelfile",
            delete=False,
        ) as handle:
            handle.write(modelfile_text)
            path = handle.name
        runner(["ollama", "create", name, "-f", path], timeout=None)
    finally:
        if path:
            try:
                Path(path).unlink()
            except FileNotFoundError:
                pass


def ensure_ollama_service(
    *,
    base_url: str = DEFAULT_URL,
    probe: Callable[..., list[str]] | None = None,
    attempts: int = 24,
    delay: float = 0.25,
) -> list[str]:
    from .models import list_ollama_models

    check = probe or list_ollama_models
    try:
        return check(base_url)
    except Exception:
        pass

    ollama = shutil.which("ollama")
    if not ollama:
        raise RuntimeError(
            "Ollama is required for the easy Zeref launcher. Install Ollama, then run `zeref` again."
        )

    kwargs: dict[str, object] = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    subprocess.Popen([ollama, "serve"], **kwargs)

    last_error: Exception | None = None
    for _ in range(attempts):
        time.sleep(delay)
        try:
            return check(base_url)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(
        f"Ollama was started but its local API did not become ready at {base_url}"
    ) from last_error


def _register_and_activate(registry, spec) -> None:
    registry.register(spec, overwrite=True)
    registry.set_active(spec.alias)


def ensure_zeref_profile(
    registry,
    *,
    base_model: str = DEFAULT_BASE_MODEL,
    profile_name: str = DEFAULT_PROFILE,
    base_url: str = DEFAULT_URL,
    rebuild: bool = False,
    list_models: Callable[..., list[str]] | None = None,
    pull: Callable[[str], None] | None = None,
    create_profile: Callable[[str, str], None] | None = None,
):
    from .models import ModelSpec, list_ollama_models

    listing = list_models or list_ollama_models
    installed = set(listing(base_url))
    if profile_name not in installed or rebuild:
        if base_model not in installed:
            (pull or pull_ollama_model)(base_model)
            installed = set(listing(base_url))
        (create_profile or create_ollama_profile)(
            profile_name,
            make_zeref_modelfile(base_model),
        )

    spec = ModelSpec(
        alias="zeref",
        backend="ollama",
        model=profile_name,
        base_url=base_url,
        context=8192,
        temperature=0.7,
    )
    _register_and_activate(registry, spec)
    return spec


def _model_alias(model: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in model.lower())
    cleaned = cleaned.strip("-") or "model"
    return f"ollama-{cleaned[:70]}"


def ensure_plain_ollama_model(
    registry,
    model: str,
    *,
    alias: str | None = None,
    base_url: str = DEFAULT_URL,
    list_models: Callable[..., list[str]] | None = None,
    pull: Callable[[str], None] | None = None,
):
    from .models import ModelSpec, list_ollama_models

    listing = list_models or list_ollama_models
    installed = set(listing(base_url))
    if model not in installed:
        (pull or pull_ollama_model)(model)

    spec = ModelSpec(
        alias=alias or _model_alias(model),
        backend="ollama",
        model=model,
        base_url=base_url,
    )
    _register_and_activate(registry, spec)
    return spec


def switch_runtime_backend(runtime, spec, *, factory=None) -> None:
    from .models import create_model
    from .session import BackendTextProvider

    model_factory = factory or create_model
    runtime.provider = BackendTextProvider(model_factory(spec))


def choose_startup_spec(
    registry,
    *,
    requested: str | None = None,
    base_model: str = DEFAULT_BASE_MODEL,
    profile_name: str = DEFAULT_PROFILE,
    base_url: str = DEFAULT_URL,
    rebuild_zeref: bool = False,
    installed_models: set[str] | None = None,
):
    def ensure_registered_available(spec):
        if (
            installed_models is not None
            and spec.backend == "ollama"
            and spec.model not in installed_models
        ):
            if spec.alias == "zeref" or spec.model == profile_name:
                return ensure_zeref_profile(
                    registry,
                    base_model=base_model,
                    profile_name=profile_name,
                    base_url=base_url,
                    rebuild=True,
                )
            return ensure_plain_ollama_model(
                registry,
                spec.model,
                alias=spec.alias,
                base_url=base_url,
            )
        registry.set_active(spec.alias)
        return spec

    if requested:
        try:
            spec = registry.get(requested)
        except KeyError:
            spec = None
        if spec is not None:
            return ensure_registered_available(spec)
        if requested == "zeref":
            return ensure_zeref_profile(
                registry,
                base_model=base_model,
                profile_name=profile_name,
                base_url=base_url,
                rebuild=rebuild_zeref,
            )
        return ensure_plain_ollama_model(registry, requested, base_url=base_url)

    active = registry.active()
    if active is not None:
        return ensure_registered_available(active)

    return ensure_zeref_profile(
        registry,
        base_model=base_model,
        profile_name=profile_name,
        base_url=base_url,
        rebuild=rebuild_zeref,
    )


def _print_models(registry, *, base_url: str = DEFAULT_URL) -> None:
    from .models import list_ollama_models

    active = registry.active_alias()
    registered = {spec.model: spec.alias for spec in registry.list() if spec.backend == "ollama"}
    print("\nOllama models:")
    try:
        installed = list_ollama_models(base_url)
    except Exception as exc:
        print(f"  unable to list models: {exc}")
        return
    for model in installed:
        alias = registered.get(model)
        marker = " * active" if alias and alias == active else ""
        alias_text = f"  alias={alias}" if alias else ""
        print(f"  {model}{alias_text}{marker}")
    print()


def _interactive(runtime, registry, *, system_prompt: str, base_url: str = DEFAULT_URL) -> int:
    spec = registry.active()
    print("ZEREF // COSMOS growing local AI")
    print(f"model: {spec.model if spec else 'unknown'}")
    print("commands: /model  /models  /use <model-or-alias>  /exit")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not text:
            continue
        if text in {"/exit", "/quit"}:
            return 0
        if text == "/model":
            current = registry.active()
            if current:
                print(f"model> {current.model} ({current.alias})")
            else:
                print("model> none")
            continue
        if text == "/models":
            _print_models(registry, base_url=base_url)
            continue
        if text.startswith("/use "):
            requested = text[5:].strip()
            if not requested:
                print("usage> /use <ollama-model-or-registered-alias>")
                continue
            try:
                from .models import list_ollama_models

                spec = choose_startup_spec(
                    registry,
                    requested=requested,
                    base_url=base_url,
                    installed_models=set(list_ollama_models(base_url)),
                )
                switch_runtime_backend(runtime, spec)
            except Exception as exc:
                print(f"model error> {exc}")
                continue
            print(
                f"model> switched to {spec.model}. "
                "COSMOS memory and runtime state stayed attached."
            )
            continue

        try:
            out = runtime.respond(text, system_prompt=system_prompt)
            print("zeref> " + str(out["response"]))
        except Exception as exc:
            print(f"zeref error> {exc}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zeref",
        description="One-command local COSMOS/Zeref launcher for Ollama with persistent memory and switchable models.",
    )
    parser.add_argument(
        "--model",
        help="registered alias or Ollama model name to use; missing Ollama models are pulled automatically",
    )
    parser.add_argument(
        "--base-model",
        default=DEFAULT_BASE_MODEL,
        help=f"base model for the Zeref Ollama profile (default: {DEFAULT_BASE_MODEL})",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=default_user_config_path(),
        help="COSMOS runtime config; defaults to a stable per-user Zeref home",
    )
    parser.add_argument("--registry", type=Path, help="override ~/.cosmic-cypher/models.json")
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="install/pull/register the selected model, then exit",
    )
    parser.add_argument(
        "--rebuild-zeref",
        action="store_true",
        help="recreate the local Ollama zeref profile from --base-model",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    from ..runtime import CosmosRuntime
    from .models import create_model
    from .registry import ModelRegistry
    from .session import BackendTextProvider, OWNER_PROFILE

    args = build_parser().parse_args(argv)
    registry = ModelRegistry(args.registry) if args.registry else ModelRegistry()

    try:
        installed_models = set(ensure_ollama_service(base_url=DEFAULT_URL))
        spec = choose_startup_spec(
            registry,
            requested=args.model,
            base_model=args.base_model,
            profile_name=DEFAULT_PROFILE,
            base_url=DEFAULT_URL,
            rebuild_zeref=args.rebuild_zeref,
            installed_models=installed_models,
        )
    except Exception as exc:
        print(f"Zeref setup failed: {exc}")
        return 2

    if args.setup_only:
        print(f"Zeref is ready. Active Ollama model: {spec.model}")
        print(f"Model registry: {registry.path}")
        print("Run `zeref` to start talking.")
        return 0

    cfg = load_zeref_runtime_config(args.config)
    runtime = CosmosRuntime(cfg, provider=BackendTextProvider(create_model(spec)))
    try:
        return _interactive(runtime, registry, system_prompt=OWNER_PROFILE)
    finally:
        try:
            runtime.save_evidence(Path(cfg.evidence_dir) / "latest.jsonl")
        finally:
            runtime.close()


if __name__ == "__main__":
    raise SystemExit(main())
