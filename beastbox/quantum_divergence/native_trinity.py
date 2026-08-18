from __future__ import annotations

import hashlib
import json
import math
import types
from array import array
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Sequence

from .trinity_state import TrinityState, balance_54_blocks, projection_matrix


def _torch():
    import torch
    import torch.nn.functional as F

    return torch, F


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _tensor_sha256(tensor: Any) -> str:
    values = tensor.detach().cpu().to(dtype=_torch()[0].float32).contiguous().view(-1).tolist()
    return hashlib.sha256(array("f", values).tobytes()).hexdigest()


def _project(values: Sequence[float], rows: int, seed: str) -> list[float]:
    src = [float(x) for x in values]
    if not src:
        raise ValueError("projection source must not be empty")
    matrix = projection_matrix(int(rows), len(src), seed)
    denom = math.sqrt(len(src))
    return [
        math.tanh(sum(float(w) * value for w, value in zip(row, src)) / denom)
        for row in matrix
    ]


def _scalar(values: Sequence[float], seed: str) -> float:
    return _project(values, 1, seed)[0]


def _zero_state(state: TrinityState, tol: float = 1e-15) -> bool:
    return max((abs(float(x)) for x in state.external54), default=0.0) <= tol


def _effective54(state: TrinityState) -> list[float]:
    if _zero_state(state):
        return [0.0] * 54
    mixed = [
        math.tanh(0.5 * float(ext) + 0.5 * float(dyn))
        for ext, dyn in zip(state.external54, state.dyn54)
    ]
    return balance_54_blocks(mixed)


def _effective12(state: TrinityState) -> list[float]:
    if _zero_state(state):
        return [0.0] * 12
    return [
        math.tanh(0.5 * float(ext) + 0.5 * float(dyn))
        for ext, dyn in zip(state.external12, state.dyn12)
    ]


@dataclass(frozen=True)
class NativeStepTelemetry:
    enabled: bool
    zero_state_identity: bool
    hidden_modulation_norm: float
    geometry_modulation_norm: float
    gate_before: float | None
    gate_after: float | None
    sigma_before: float | None
    sigma_after: float | None
    affinity_divergence: float | None
    logits_sha256: str
    internal12_summary: list[float]
    layer_count: int


@dataclass(frozen=True)
class CandidateDigitResult:
    selected_digit: str
    logits: dict[str, float]
    probabilities: dict[str, float]
    telemetry: NativeStepTelemetry


@dataclass
class _Accumulator:
    hidden_norms: list[float]
    geometry_norms: list[float]
    gate_before: list[float]
    gate_after: list[float]
    sigma_before: list[float]
    sigma_after: list[float]
    affinity_divergence: list[float]
    internal12: list[list[float]]

    @classmethod
    def empty(cls) -> "_Accumulator":
        return cls([], [], [], [], [], [], [], [])


class NativeTrinityAdapter:
    """Request-scoped native CST modulation for the QC67 `cosmos-cst` runtime.

    The adapter never mutates checkpoint parameters. For a non-zero Trinity state it
    temporarily replaces each CST attention block's forward method, computes the same
    native attention path with bounded external modulation, records telemetry, and
    restores the exact bound methods and `last_gate` values in `finally`.
    """

    def __init__(self, native: Any):
        self.native = native
        self.hooks_remaining = 0
        self._validate_contract()

    def _validate_contract(self) -> None:
        missing: list[str] = []
        for name in ("encode", "_logits", "stoi", "block", "m", "lock"):
            if not hasattr(self.native, name):
                missing.append(name)
        blocks = getattr(getattr(self.native, "m", None), "blocks", None)
        if blocks is None:
            missing.append("m.blocks")
        else:
            for index, block in enumerate(blocks):
                attn = getattr(block, "attn", None)
                for name in ("qkv", "proj", "drop", "w54", "log_sigma", "gate", "nh", "hd", "use_cst"):
                    if attn is None or not hasattr(attn, name):
                        missing.append(f"m.blocks[{index}].attn.{name}")
        for digit in "0123456789":
            if digit not in getattr(self.native, "stoi", {}):
                missing.append(f"stoi[{digit!r}]")
        if missing:
            raise ValueError("native QC67 Trinity contract missing: " + ", ".join(missing))

    def _base_gate_sigma(self) -> tuple[float | None, float | None]:
        torch, _ = _torch()
        gates: list[float] = []
        sigmas: list[float] = []
        for block in self.native.m.blocks:
            attn = block.attn
            if not bool(attn.use_cst):
                continue
            gates.append(float(attn.gate.detach().clamp(0.01, 1.0).reshape(-1)[0]))
            sigmas.append(float(torch.exp(attn.log_sigma.detach()).clamp(0.05, 50.0)))
        if not gates:
            return None, None
        return sum(gates) / len(gates), sum(sigmas) / len(sigmas)

    def _identity_telemetry(self, logits: Any, *, enabled: bool, zero_state: bool) -> NativeStepTelemetry:
        gate, sigma = self._base_gate_sigma()
        return NativeStepTelemetry(
            enabled=bool(enabled),
            zero_state_identity=bool(zero_state),
            hidden_modulation_norm=0.0,
            geometry_modulation_norm=0.0,
            gate_before=gate,
            gate_after=gate,
            sigma_before=sigma,
            sigma_after=sigma,
            affinity_divergence=0.0 if gate is not None else None,
            logits_sha256=_tensor_sha256(logits),
            internal12_summary=[0.0] * 12,
            layer_count=len(getattr(self.native.m, "blocks", [])),
        )

    @contextmanager
    def _patched(self, state: TrinityState) -> Iterator[_Accumulator]:
        torch, F = _torch()
        effective54 = _effective54(state)
        effective12 = _effective12(state)
        originals: list[tuple[Any, Any, float]] = []
        accumulator = _Accumulator.empty()

        def make_forward(layer_index: int):
            def patched(attn: Any, x: Any, mask: Any):
                B, T, C = x.shape
                dtype = x.dtype
                device = x.device
                positions = torch.arange(1, T + 1, device=device, dtype=dtype)

                hidden_base = torch.tensor(
                    _project(effective54, C, f"trinity-hidden-v1:{layer_index}"),
                    dtype=dtype,
                    device=device,
                )
                hidden_phase = torch.sin(positions * (0.17320508075688773 + 0.031 * (layer_index + 1)))
                hidden_mod = hidden_phase.view(1, T, 1) * hidden_base.view(1, 1, C)
                x_hidden = x * (1.0 + float(state.config.hidden_gain) * hidden_mod)
                hidden_delta = x_hidden - x
                accumulator.hidden_norms.append(
                    float(torch.linalg.vector_norm(hidden_delta).detach()) / math.sqrt(max(1, hidden_delta.numel()))
                )

                q, k, v = attn.qkv(x_hidden).split(C, dim=2)
                sh = lambda t: t.view(B, T, attn.nh, attn.hd).transpose(1, 2)
                q, k, v = sh(q), sh(k), sh(v)
                a = F.softmax(
                    (q @ k.transpose(-2, -1)) / math.sqrt(attn.hd) + mask[:T, :T],
                    dim=-1,
                )

                if bool(attn.use_cst):
                    x54_base = attn.w54(x)
                    base_sigma = torch.exp(attn.log_sigma).clamp(0.05, 50.0)
                    d2_base = torch.cdist(x54_base, x54_base, p=2.0) ** 2
                    H_base = torch.exp(-d2_base / (2 * base_sigma * base_sigma))
                    H_base = H_base.masked_fill(mask[:T, :T] < 0, 0.0)
                    H_base = H_base / H_base.sum(-1, keepdim=True).clamp_min(1e-9)

                    x54 = attn.w54(x_hidden)
                    geom_base = torch.tensor(effective54, dtype=dtype, device=device)
                    geom_phase = torch.sin(positions * (0.311 + 0.047 * (layer_index + 1)))
                    geom_mod = geom_phase.view(1, T, 1) * geom_base.view(1, 1, 54)
                    x54_mod = x54 * (1.0 + float(state.config.geometry_gain) * geom_mod)
                    geometry_delta = x54_mod - x54_base
                    accumulator.geometry_norms.append(
                        float(torch.linalg.vector_norm(geometry_delta).detach())
                        / math.sqrt(max(1, geometry_delta.numel()))
                    )

                    gate_shift = float(state.config.gate_gain) * _scalar(
                        effective12, f"trinity-gate-v1:{layer_index}"
                    )
                    sigma_shift = float(state.config.sigma_gain) * _scalar(
                        effective12, f"trinity-sigma-v1:{layer_index}"
                    )
                    raw = attn.gate
                    base_gate = raw + (raw.clamp(0.01, 1.0) - raw).detach()
                    effective_gate = (base_gate + gate_shift).clamp(0.01, 0.99)
                    effective_sigma = (base_sigma * math.exp(sigma_shift)).clamp(0.05, 50.0)

                    d2 = torch.cdist(x54_mod, x54_mod, p=2.0) ** 2
                    H = torch.exp(-d2 / (2 * effective_sigma * effective_sigma))
                    H = H.masked_fill(mask[:T, :T] < 0, 0.0)
                    H = H / H.sum(-1, keepdim=True).clamp_min(1e-9)
                    a = (1 - effective_gate) * a + effective_gate * H.unsqueeze(1)

                    accumulator.gate_before.append(float(base_gate.detach().reshape(-1)[0]))
                    accumulator.gate_after.append(float(effective_gate.detach().reshape(-1)[0]))
                    accumulator.sigma_before.append(float(base_sigma.detach()))
                    accumulator.sigma_after.append(float(effective_sigma.detach()))
                    accumulator.affinity_divergence.append(float((H - H_base).abs().mean().detach()))
                    attn.last_gate = float(effective_gate.detach().reshape(-1)[0])

                summary_hidden = x_hidden.mean(dim=(0, 1)).detach().to(dtype=torch.float32).cpu().tolist()
                accumulator.internal12.append(
                    _project(summary_hidden, 12, f"trinity-feedback-v1:{layer_index}")
                )

                y = (attn.drop(a) @ v).transpose(1, 2).contiguous().view(B, T, C)
                return attn.proj(y)

            return patched

        try:
            for index, block in enumerate(self.native.m.blocks):
                attn = block.attn
                originals.append((attn, attn.forward, float(getattr(attn, "last_gate", 0.0))))
                attn.forward = types.MethodType(make_forward(index), attn)
            self.hooks_remaining = len(originals)
            yield accumulator
        finally:
            for attn, original_forward, last_gate in originals:
                attn.forward = original_forward
                attn.last_gate = last_gate
            self.hooks_remaining = 0

    def score(self, prompt: str, state: TrinityState, *, enabled: bool) -> tuple[Any, NativeStepTelemetry]:
        torch, _ = _torch()
        ids = self.native.encode(str(prompt))
        if not ids:
            raise ValueError("prompt has no characters in the native QC67 vocabulary")
        idx = torch.tensor([ids], dtype=torch.long)
        idx = idx[:, -int(self.native.block):]

        with torch.no_grad(), self.native.lock:
            if not enabled:
                logits = self.native._logits(idx)
                return logits, self._identity_telemetry(logits, enabled=False, zero_state=False)
            if _zero_state(state):
                logits = self.native._logits(idx)
                return logits, self._identity_telemetry(logits, enabled=True, zero_state=True)

            with self._patched(state) as acc:
                logits = self.native._logits(idx)

        def mean_or_none(values: Sequence[float]) -> float | None:
            return None if not values else sum(float(x) for x in values) / len(values)

        internal12 = [0.0] * 12
        if acc.internal12:
            internal12 = [
                math.tanh(sum(layer[i] for layer in acc.internal12) / len(acc.internal12))
                for i in range(12)
            ]

        telemetry = NativeStepTelemetry(
            enabled=True,
            zero_state_identity=False,
            hidden_modulation_norm=float(mean_or_none(acc.hidden_norms) or 0.0),
            geometry_modulation_norm=float(mean_or_none(acc.geometry_norms) or 0.0),
            gate_before=mean_or_none(acc.gate_before),
            gate_after=mean_or_none(acc.gate_after),
            sigma_before=mean_or_none(acc.sigma_before),
            sigma_after=mean_or_none(acc.sigma_after),
            affinity_divergence=mean_or_none(acc.affinity_divergence),
            logits_sha256=_tensor_sha256(logits),
            internal12_summary=internal12,
            layer_count=len(self.native.m.blocks),
        )
        return logits, telemetry

    def score_candidate_digits(self, prompt: str, state: TrinityState, *, enabled: bool) -> CandidateDigitResult:
        torch, _ = _torch()
        logits, telemetry = self.score(prompt, state, enabled=enabled)
        last = logits[0, -1]
        digit_values = torch.stack([last[int(self.native.stoi[digit])] for digit in "0123456789"])
        probabilities = torch.softmax(digit_values, dim=0)
        logit_map = {digit: float(digit_values[i].detach()) for i, digit in enumerate("0123456789")}
        probability_map = {digit: float(probabilities[i].detach()) for i, digit in enumerate("0123456789")}
        selected = "0123456789"[int(torch.argmax(digit_values).item())]
        return CandidateDigitResult(
            selected_digit=selected,
            logits=logit_map,
            probabilities=probability_map,
            telemetry=telemetry,
        )


def load_qc67_native(server_path: str, checkpoint_path: str):
    from .forced_choice import _load_native_model

    native = _load_native_model(server_path, checkpoint_path)
    NativeTrinityAdapter(native)._validate_contract()
    return native


def projection_hashes_for_native(embd: int, layers: int) -> dict[str, str]:
    payload = {
        "hidden": [projection_matrix(embd, 54, f"trinity-hidden-v1:{i}") for i in range(layers)],
        "gate": [projection_matrix(1, 12, f"trinity-gate-v1:{i}") for i in range(layers)],
        "sigma": [projection_matrix(1, 12, f"trinity-sigma-v1:{i}") for i in range(layers)],
        "feedback": [f"trinity-feedback-v1:{i}" for i in range(layers)],
        "geometry": "token-phase-multiplicative-block-balanced-v2",
        "54_block_balance": {
            "version": "trinity-54-block-balance-v1",
            "scale12": math.sqrt(54.0 / (2.0 * 12.0)),
            "scale42": math.sqrt(54.0 / (2.0 * 42.0)),
        },
    }
    return {"native_trinity": hashlib.sha256(_canonical(payload)).hexdigest()}
