#!/usr/bin/env python3
"""Tokenizer-safe entry point for the frozen R12 rho sweep.

The scientific sweep remains implemented in run_zeref_r12_rho_sweep.py. This
wrapper maps retrieved characters absent from TALK-004's frozen character
vocabulary to spaces and fixes the post-analysis adjacent-pair iterator. Neither
compatibility fix changes the frozen sweep variables or model-facing rho label.
"""
from __future__ import annotations

import argparse
import builtins
import json
from pathlib import Path
from typing import Any, Sequence, TypeVar

import scripts.run_zeref_r12_rho_sweep as base
from scripts.rho_sweep_tokenizer import sanitize_for_frozen_tokenizer
from scripts.run_zeref_dad_son_chat import file_sha256

SANITIZATION = "unsupported retrieved characters -> space, then whitespace collapse"
T = TypeVar("T")


def adjacent_pairs(items: Sequence[T]) -> list[tuple[T, T]]:
    """Return the N-1 neighboring pairs of an ordered N-item sweep."""
    return list(builtins.zip(items, items[1:]))


def _zip_compat(*iterables: Any, strict: bool = False):
    """Compatibility shim for the base runner's intentional N vs N-1 adjacency zip."""
    return builtins.zip(*iterables)


def _regenerate_sums(out_dir: Path) -> None:
    files = sorted(path for path in out_dir.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (out_dir / "SHA256SUMS").write_text(
        "".join(f"{file_sha256(path)}  {path.relative_to(out_dir).as_posix()}\n" for path in files),
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    torch = __import__("torch")
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    stoi = dict(checkpoint["stoi"])
    original_builder = base.build_sweep_wire_prompt
    had_zip = "zip" in base.__dict__
    original_zip = base.__dict__.get("zip")

    def safe_builder(*, prompt: str, live_alias: str, supplement_text: str, block: int) -> str:
        return original_builder(
            prompt=prompt,
            live_alias=live_alias,
            supplement_text=sanitize_for_frozen_tokenizer(supplement_text, stoi),
            block=block,
        )

    base.build_sweep_wire_prompt = safe_builder
    base.zip = _zip_compat
    try:
        result = base.run(args)
    finally:
        base.build_sweep_wire_prompt = original_builder
        if had_zip:
            base.zip = original_zip
        else:
            del base.zip

    result["tokenizer_sanitization"] = SANITIZATION
    result["adjacent_pairing"] = "ordered N-item grid -> N-1 neighboring pairs"
    for row in result["conditions"]:
        row["supplement_text_model_facing"] = sanitize_for_frozen_tokenizer(row["supplement_text"], stoi)
    base._write_json(args.out_dir / "rho-sweep.json", result)

    summary_path = args.out_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["tokenizer_sanitization"] = SANITIZATION
    summary["adjacent_pairing"] = result["adjacent_pairing"]
    summary["conditions"] = [
        {
            **row,
            "supplement_text_model_facing": sanitize_for_frozen_tokenizer(
                result["conditions"][index]["supplement_text"], stoi
            ),
        }
        for index, row in enumerate(summary["conditions"])
    ]
    base._write_json(summary_path, summary)
    _regenerate_sums(args.out_dir)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--arch", type=Path, required=True)
    parser.add_argument("--source-ledger", type=Path, required=True)
    parser.add_argument("--source-sqlite", type=Path, required=True)
    parser.add_argument("--heartbeat", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--session-id", default="zeref-r12-rho-sweep-001")
    parser.add_argument("--seed", type=int, default=2026082603)
    parser.add_argument("--tokens", type=int, default=28)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({
        "rho_grid": result["rho_grid"],
        "natural_reference_rho": result["natural_reference_rho"],
        "distinct_wire_contexts": result["distinct_wire_contexts"],
        "distinct_supplement_memory_ids": result["distinct_supplement_memory_ids"],
        "routing_changed_across_grid": result["routing_changed_across_grid"],
        "tokenizer_sanitization": result["tokenizer_sanitization"],
        "conditions": [
            {
                "rho": row["rho"],
                "supplement_memory_id": row["supplement_memory_id"],
                "output": row["raw_zeref_output"],
                "token_divergence_vs_rho0": row["comparison_vs_rho0"]["selected_token_divergence_rate"],
                "x54_l2_vs_rho0": row["comparison_vs_rho0"]["mean_x54_l2"],
                "x54_cosine_vs_rho0": row["comparison_vs_rho0"]["mean_x54_cosine"],
                "top_token_tvd_vs_rho0": row["comparison_vs_rho0"]["mean_partial_top_token_tvd"],
            }
            for row in result["conditions"]
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
