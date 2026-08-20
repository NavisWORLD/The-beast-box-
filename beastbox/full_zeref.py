from __future__ import annotations

import argparse
import dataclasses
import json
import time
from pathlib import Path
from typing import Any, Callable, Sequence

from .config import RuntimeConfig
from .runtime import CosmosRuntime
from .quantum_divergence.native_trinity import NativeTrinityAdapter, load_qc67_native, projection_hashes_for_native
from .quantum_divergence.resident_broker import validate_sanitized_receipt
from .quantum_divergence.trinity_state import SensorFixture, TrinityConfig, TrinityState, compose_trinity_state


def state_from_entropy12(
    entropy12: Sequence[float],
    *,
    config: TrinityConfig | None = None,
    now: float | None = None,
) -> TrinityState:
    stamp = float(time.time() if now is None else now)
    return compose_trinity_state(
        sensor_fixture=SensorFixture.fixed(seed=0, captured_at=stamp),
        entropy12=[float(x) for x in entropy12],
        include_sensors=False,
        config=config or TrinityConfig(),
        now=stamp,
    )


def load_ibm_receipt(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_sanitized_receipt(value)


def _telemetry_dict(value: Any) -> dict[str, Any]:
    if dataclasses.is_dataclass(value):
        raw = dataclasses.asdict(value)
    elif isinstance(value, dict):
        raw = dict(value)
    else:
        raw = {
            name: getattr(value, name)
            for name in (
                "enabled",
                "zero_state_identity",
                "hidden_modulation_norm",
                "geometry_modulation_norm",
                "gate_before",
                "gate_after",
                "sigma_before",
                "sigma_after",
                "affinity_divergence",
                "logits_sha256",
                "internal12_summary",
                "layer_count",
            )
            if hasattr(value, name)
        }
    return raw


class NativeTrinityTextProvider:
    """Character generator that applies native QC67 Trinity state at every step."""

    def __init__(
        self,
        native: Any,
        state: TrinityState,
        *,
        adapter: Any | None = None,
        max_new_tokens: int = 192,
        token_selector: Callable[[Any], int] | None = None,
        stop_on_newline: bool = True,
    ) -> None:
        self.native = native
        self.state = state
        self.adapter = adapter or NativeTrinityAdapter(native)
        self.max_new_tokens = max(1, int(max_new_tokens))
        self.token_selector = token_selector or self._default_token_selector
        self.stop_on_newline = bool(stop_on_newline)
        self.last_telemetry: dict[str, Any] = {
            "native_enabled": True,
            "generated_tokens": 0,
            "state_step": int(state.step),
        }

    @staticmethod
    def _default_token_selector(logits: Any) -> int:
        last = logits[0, -1]
        argmax = getattr(last, "argmax", None)
        if callable(argmax):
            selected = argmax()
            item = getattr(selected, "item", None)
            return int(item() if callable(item) else selected)
        values = list(last)
        if not values:
            raise RuntimeError("native model returned empty logits")
        return max(range(len(values)), key=lambda i: float(values[i]))

    def _decode(self, index: int) -> str:
        mapping = getattr(self.native, "itos", None)
        if mapping is None:
            raise ValueError("native QC67 runtime does not expose itos vocabulary")
        if isinstance(mapping, dict):
            value = mapping.get(int(index))
        else:
            value = mapping[int(index)]
        if value is None:
            raise ValueError(f"native vocabulary does not contain token index {index}")
        return str(value)

    def generate(self, prompt: str) -> str:
        running = str(prompt)
        out: list[str] = []
        telemetry_rows: list[dict[str, Any]] = []
        for _ in range(self.max_new_tokens):
            logits, telemetry = self.adapter.score(running, self.state, enabled=True)
            row = _telemetry_dict(telemetry)
            telemetry_rows.append(row)
            summary = [float(x) for x in row.get("internal12_summary", [0.0] * 12)]
            if len(summary) == 12:
                self.state.apply_feedback(summary)
            token = self._decode(int(self.token_selector(logits)))
            out.append(token)
            running += token
            if self.stop_on_newline and "\n" in token:
                break

        def mean(name: str) -> float:
            values = [float(row[name]) for row in telemetry_rows if row.get(name) is not None]
            return sum(values) / len(values) if values else 0.0

        self.last_telemetry = {
            "native_enabled": True,
            "generated_tokens": len(out),
            "state_step": int(self.state.step),
            "hidden_modulation_norm": mean("hidden_modulation_norm"),
            "geometry_modulation_norm": mean("geometry_modulation_norm"),
            "affinity_divergence": mean("affinity_divergence"),
            "gate_before": mean("gate_before"),
            "gate_after": mean("gate_after"),
            "sigma_before": mean("sigma_before"),
            "sigma_after": mean("sigma_after"),
            "last_logits_sha256": telemetry_rows[-1].get("logits_sha256") if telemetry_rows else None,
            "projection_hashes": self.state.projection_hashes,
        }
        return "".join(out)


class FullZerefRuntime:
    """Persistent COSMOS conversation whose text provider is native Trinity QC67."""

    def __init__(
        self,
        *,
        config: RuntimeConfig,
        native: Any,
        ibm_receipt: dict[str, Any],
        max_new_tokens: int = 192,
    ) -> None:
        self.receipt = validate_sanitized_receipt(dict(ibm_receipt))
        self.state = state_from_entropy12(self.receipt["entropy12"])
        self.provider = NativeTrinityTextProvider(native, self.state, max_new_tokens=max_new_tokens)
        self.runtime = CosmosRuntime(config, provider=self.provider)
        self.native = native

    @classmethod
    def from_paths(
        cls,
        *,
        config_path: str | Path,
        native_server: str | Path,
        checkpoint: str | Path,
        ibm_receipt: str | Path,
        max_new_tokens: int = 192,
    ) -> "FullZerefRuntime":
        config = RuntimeConfig.load(Path(config_path))
        native = load_qc67_native(str(native_server), str(checkpoint))
        receipt = load_ibm_receipt(ibm_receipt)
        return cls(config=config, native=native, ibm_receipt=receipt, max_new_tokens=max_new_tokens)

    def respond(self, text: str, *, system_prompt: str | None = None) -> dict[str, Any]:
        out = self.runtime.respond(str(text), system_prompt=system_prompt)
        out["native_trinity"] = dict(self.provider.last_telemetry)
        out["ibm_provenance"] = {
            "backend": self.receipt["backend"],
            "job_id": self.receipt["job_id"],
            "job_status": self.receipt["job_status"],
            "entropy_source_sha256": self.receipt["entropy_source_sha256"],
            "counts_sha256": self.receipt["counts_sha256"],
            "secret_exposed_to_subject": False,
        }
        return out

    def doctor(self) -> dict[str, Any]:
        layers = len(getattr(getattr(self.native, "m", None), "blocks", []))
        embd = int(getattr(getattr(self.native, "m", None), "embd", 0) or getattr(getattr(self.native, "meta", {}), "get", lambda *_: 0)("embd", 0) or 0)
        return {
            "ok": bool(layers),
            "native_trinity": True,
            "state_step": int(self.state.step),
            "projection_hashes": self.state.projection_hashes,
            "native_projection_hashes": projection_hashes_for_native(embd, layers) if embd > 0 and layers > 0 else {},
            "ibm": {
                "authenticated": self.receipt["authenticated"],
                "backend": self.receipt["backend"],
                "job_id": self.receipt["job_id"],
                "job_status": self.receipt["job_status"],
                "secret_exposed_to_subject": False,
            },
        }

    def close(self) -> None:
        self.runtime.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="full-zeref", description="QC67 + COSMOS + native Trinity + sanitized IBM provenance")
    parser.add_argument("command", choices=["doctor", "chat"])
    parser.add_argument("--config", default="beastbox.json")
    parser.add_argument("--native-server", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--ibm-receipt", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("message", nargs="?")
    args = parser.parse_args(argv)

    runtime = FullZerefRuntime.from_paths(
        config_path=args.config,
        native_server=args.native_server,
        checkpoint=args.checkpoint,
        ibm_receipt=args.ibm_receipt,
        max_new_tokens=args.max_new_tokens,
    )
    try:
        if args.command == "doctor":
            print(json.dumps(runtime.doctor(), indent=2, sort_keys=True))
            return 0
        if args.message:
            print(json.dumps(runtime.respond(args.message), indent=2, sort_keys=True, default=str))
            return 0
        while True:
            try:
                text = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if text in {"/exit", "/quit"}:
                return 0
            if text:
                out = runtime.respond(text)
                print("zeref> " + str(out["response"]))
    finally:
        runtime.close()


if __name__ == "__main__":
    raise SystemExit(main())
