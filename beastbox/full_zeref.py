from __future__ import annotations

import argparse
import dataclasses
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .config import RuntimeConfig
from .runtime import CosmosRuntime
from .quantum_divergence.native_trinity import NativeTrinityAdapter, load_qc67_native, projection_hashes_for_native
from .quantum_divergence.resident_broker import receipt_is_fresh, validate_sanitized_receipt
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


def load_ibm_receipt(path: str | Path, *, require_fresh: bool = False) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_sanitized_receipt(value, require_fresh=require_fresh)


def subject_environment_safe(environ: Mapping[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return "IBM_QUANTUM_TOKEN" not in env


def projection_readiness(state_hashes: Mapping[str, Any], native_hashes: Mapping[str, Any]) -> bool:
    required_state = {"sensor_to_12_seed", "12_to_42", "54_block_balance"}
    return required_state.issubset(set(state_hashes)) and bool(native_hashes.get("native_trinity"))


def _telemetry_dict(value: Any) -> dict[str, Any]:
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if isinstance(value, dict):
        return dict(value)
    return {
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


class NativeTrinityTextProvider:
    """Deterministic QC67 character generator with optional native Trinity injection."""

    def __init__(
        self,
        native: Any,
        state: TrinityState,
        *,
        adapter: Any | None = None,
        enabled: bool = True,
        max_new_tokens: int = 192,
        token_selector: Callable[[Any], int] | None = None,
        stop_on_newline: bool = True,
    ) -> None:
        self.native = native
        self.state = state
        self.adapter = adapter or NativeTrinityAdapter(native)
        self.enabled = bool(enabled)
        self.max_new_tokens = max(1, int(max_new_tokens))
        self.token_selector = token_selector or self._default_token_selector
        self.stop_on_newline = bool(stop_on_newline)
        self.last_telemetry: dict[str, Any] = {
            "native_enabled": self.enabled,
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
        value = mapping.get(int(index)) if isinstance(mapping, dict) else mapping[int(index)]
        if value is None:
            raise ValueError(f"native vocabulary does not contain token index {index}")
        return str(value)

    def generate(self, prompt: str) -> str:
        running = str(prompt)
        out: list[str] = []
        telemetry_rows: list[dict[str, Any]] = []
        for _ in range(self.max_new_tokens):
            logits, telemetry = self.adapter.score(running, self.state, enabled=self.enabled)
            row = _telemetry_dict(telemetry)
            telemetry_rows.append(row)
            if self.enabled:
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
            "native_enabled": self.enabled,
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
        require_fresh_ibm: bool = False,
    ) -> None:
        self.receipt = validate_sanitized_receipt(dict(ibm_receipt), require_fresh=require_fresh_ibm)
        self.receipt_fresh = receipt_is_fresh(self.receipt)
        self.state = state_from_entropy12(self.receipt["entropy12"])
        self.provider = NativeTrinityTextProvider(native, self.state, enabled=True, max_new_tokens=max_new_tokens)
        config.local_model_name = "qc67-cosmos-cst"
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
        require_fresh_ibm: bool = False,
    ) -> "FullZerefRuntime":
        config = RuntimeConfig.load(Path(config_path))
        native = load_qc67_native(str(native_server), str(checkpoint))
        receipt = load_ibm_receipt(ibm_receipt, require_fresh=require_fresh_ibm)
        return cls(
            config=config,
            native=native,
            ibm_receipt=receipt,
            max_new_tokens=max_new_tokens,
            require_fresh_ibm=require_fresh_ibm,
        )

    def respond(self, text: str, *, system_prompt: str | None = None) -> dict[str, Any]:
        out = self.runtime.respond(str(text), system_prompt=system_prompt)
        out["native_trinity"] = dict(self.provider.last_telemetry)
        out["ibm_provenance"] = {
            "backend": self.receipt["backend"],
            "job_id": self.receipt["job_id"],
            "job_status": self.receipt["job_status"],
            "fresh": receipt_is_fresh(self.receipt),
            "entropy_source_sha256": self.receipt["entropy_source_sha256"],
            "counts_sha256": self.receipt["counts_sha256"],
            "secret_exposed_to_subject": False,
        }
        return out

    def doctor(self) -> dict[str, Any]:
        blocks = list(getattr(getattr(self.native, "m", None), "blocks", []) or [])
        layers = len(blocks)
        meta = getattr(self.native, "meta", {})
        embd = int(getattr(getattr(self.native, "m", None), "embd", 0) or (meta.get("embd", 0) if isinstance(meta, dict) else 0) or 0)
        if embd <= 0 and blocks:
            embd = int(getattr(getattr(blocks[0].attn, "qkv", None), "in_features", 0) or 0)
        native_hashes = projection_hashes_for_native(embd, layers) if embd > 0 and layers > 0 else {}
        projection_ok = projection_readiness(self.state.projection_hashes, native_hashes)
        env_safe = subject_environment_safe()
        zero_identity = False
        zero_error: str | None = None
        try:
            zero_state = state_from_entropy12([0.0] * 12)
            _, telemetry = self.provider.adapter.score("0", zero_state, enabled=True)
            zero_identity = bool(
                telemetry.zero_state_identity
                and float(telemetry.hidden_modulation_norm) == 0.0
                and float(telemetry.geometry_modulation_norm) == 0.0
                and float(telemetry.affinity_divergence or 0.0) == 0.0
            )
        except Exception as exc:
            zero_error = type(exc).__name__
        return {
            "ok": bool(layers and projection_ok and env_safe and zero_identity),
            "native_trinity": True,
            "zero_state_identity": zero_identity,
            "zero_state_check_error": zero_error,
            "subject_environment_safe": env_safe,
            "projection_hashes_complete": projection_ok,
            "state_step": int(self.state.step),
            "projection_hashes": self.state.projection_hashes,
            "native_projection_hashes": native_hashes,
            "ibm": {
                "authenticated": self.receipt["authenticated"],
                "fresh": receipt_is_fresh(self.receipt),
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
    parser.add_argument("--require-fresh-ibm", action="store_true")
    parser.add_argument("message", nargs="?")
    args = parser.parse_args(argv)

    runtime = FullZerefRuntime.from_paths(
        config_path=args.config,
        native_server=args.native_server,
        checkpoint=args.checkpoint,
        ibm_receipt=args.ibm_receipt,
        max_new_tokens=args.max_new_tokens,
        require_fresh_ibm=args.require_fresh_ibm,
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
