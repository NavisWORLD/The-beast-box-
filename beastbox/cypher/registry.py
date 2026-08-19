from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from .models import ModelSpec, list_ollama_models


def default_registry_path() -> Path:
    root = Path(os.environ.get("COSMIC_CYPHER_HOME", Path.home() / ".cosmic-cypher"))
    return root / "models.json"


class ModelRegistry:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path).expanduser() if path else default_registry_path()

    def _load_raw(self) -> dict:
        if not self.path.exists():
            return {"version": 2, "models": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("models", {}), dict):
            raise ValueError(f"invalid model registry: {self.path}")
        return data

    def _save_raw(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)

    def list(self) -> list[ModelSpec]:
        raw = self._load_raw().get("models", {})
        return [ModelSpec.from_dict(v) for _, v in sorted(raw.items())]

    def get(self, alias: str) -> ModelSpec:
        raw = self._load_raw().get("models", {})
        if alias not in raw:
            raise KeyError(f"unknown local model alias {alias!r}")
        return ModelSpec.from_dict(raw[alias])

    def active_alias(self) -> str | None:
        data = self._load_raw()
        alias = data.get("active")
        if not alias or alias not in data.get("models", {}):
            return None
        return str(alias)

    def active(self) -> ModelSpec | None:
        alias = self.active_alias()
        return self.get(alias) if alias else None

    def set_active(self, alias: str) -> None:
        self.get(alias)
        data = self._load_raw()
        data["version"] = max(2, int(data.get("version", 1)))
        data["active"] = alias
        self._save_raw(data)

    def register(self, spec: ModelSpec, *, overwrite: bool = False) -> None:
        if not spec.alias.strip():
            raise ValueError("model alias cannot be empty")
        data = self._load_raw()
        models = data.setdefault("models", {})
        if spec.alias in models and not overwrite:
            raise ValueError(f"alias {spec.alias!r} already exists; pass --overwrite to replace it")
        models[spec.alias] = spec.to_dict()
        self._save_raw(data)

    def remove(self, alias: str) -> bool:
        data = self._load_raw()
        existed = alias in data.setdefault("models", {})
        data["models"].pop(alias, None)
        if data.get("active") == alias:
            data.pop("active", None)
        self._save_raw(data)
        return existed

    def register_ollama(self, base_url: str = "http://127.0.0.1:11434", *, overwrite: bool = False) -> list[str]:
        added: list[str] = []
        for name in list_ollama_models(base_url):
            alias = f"ollama-{name.replace(':', '-').replace('/', '-')}"
            try:
                self.register(
                    ModelSpec(alias=alias, backend="ollama", model=name, base_url=base_url),
                    overwrite=overwrite,
                )
                added.append(alias)
            except ValueError:
                if overwrite:
                    raise
        return added

    def register_gguf_paths(
        self,
        paths: Iterable[str | Path],
        *,
        recursive: bool = False,
        backend: str = "llama-cpp-python",
        overwrite: bool = False,
        context: int = 8192,
        n_gpu_layers: int = 0,
    ) -> list[str]:
        files: list[Path] = []
        for raw in paths:
            p = Path(raw).expanduser()
            if p.is_file() and p.suffix.lower() == ".gguf":
                files.append(p)
            elif p.is_dir():
                files.extend(p.rglob("*.gguf") if recursive else p.glob("*.gguf"))
        added: list[str] = []
        for p in sorted(set(x.resolve() for x in files)):
            base = p.stem.lower().replace(" ", "-")
            alias = f"gguf-{''.join(ch for ch in base if ch.isalnum() or ch in '-_.')[:60]}"
            suffix, original = 2, alias
            while True:
                try:
                    self.register(
                        ModelSpec(
                            alias=alias,
                            backend=backend,
                            model=str(p),
                            context=context,
                            options={"n_gpu_layers": n_gpu_layers},
                        ),
                        overwrite=overwrite,
                    )
                    break
                except ValueError:
                    if overwrite:
                        raise
                    alias = f"{original}-{suffix}"
                    suffix += 1
            added.append(alias)
        return added
