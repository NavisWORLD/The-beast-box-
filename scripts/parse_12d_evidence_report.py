#!/usr/bin/env python3
"""Parse 12D gate evidence logs into a strictly separated
IMPLEMENTED / OBSERVED / MEASURED / NULL report.

Reads candidate training logs and 8+1 promotion gate logs (regex
key=value floats/ints/flags + embedded JSON telemetry) plus an optional
JSON receipt from scripts/gate_12d_paired_control.py, and routes
delta_NLL_12D and JSD_12D into MEASURED only when a real measured value
meets its threshold; anything below threshold or missing goes to NULL
with a reason. A "ready" stub receipt contributes nothing — it routes
everything to NULL with missing_or_unmeasured_in_logs, never MEASURED.

Thresholds (the 9th gate, PR #1043): min_delta_nll 0.05, min_jsd 0.02.
Defaults: evidence/post_1043_12d_evidence_report.json/.md — this evidence
is about the 006 training gate after the FILM switch (#1043 / PR 2), NOT
about #1047 (the ONNX export PR).

Usage (first 006 run after the film switches flip):
  python3 scripts/parse_12d_evidence_report.py \\
      --logs logs/train_006.log logs/promote_gate.log \\
      --receipt evidence/12d_gate_receipt.json \\
      --commit-sha <sha> --run-id <id> --pr <number> \\
      --json-out evidence/post_1043_12d_evidence_report.json \\
      --md-out evidence/post_1043_12d_evidence_report.md
--pr defaults to UNVERIFIED; pass the real PR number at runtime. Never
hardcode a PR number that does not exist yet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Verified IMPLEMENTED facts (PR #1043, branch emeth/mouth-film-12d,
# head 6c7792e2; models/rawrphos/architecture/model.py, read first-hand).
# These describe what the code DOES, not what any run measured; the
# MEASURED section below is the only place a run's numbers may appear.
# ---------------------------------------------------------------------------
IMPLEMENTED_CLAIMS = [
    {
        "claim": "multi-tap FiLM conditioning, layers 3,7,...,43",
        "detail": "film_taps=(3,7,11,15,19,23,27,31,35,39,43), film_alpha=0.12",
        "source": "models/rawrphos/architecture/model.py:275-276 (#1043 branch emeth/mouth-film-12d, head 6c7792e2)",
    },
    {
        "claim": "zero-init FiLM gamma/beta (identical logits at upgrade)",
        "detail": "film_gamma/film_beta are nn.Linear(54, d_model, bias=False) ModuleLists, weights zero-initialized",
        "source": "models/rawrphos/architecture/model.py:278-280 (#1043 branch emeth/mouth-film-12d, head 6c7792e2)",
    },
    {
        "claim": "FiLM applied at taps in forward",
        "detail": "if c54_norm is not None and c.film and i in self.film_taps: x = x*(1+alpha*g_hat) + (alpha*x_rms*b_hat)",
        "source": "models/rawrphos/architecture/model.py:378-383 (#1043 branch emeth/mouth-film-12d, head 6c7792e2)",
    },
    {
        "claim": "CF-JS margin loss + 9th gate (delta_NLL >= 0.05, mean JSD >= 0.02)",
        "detail": "gate thresholds are CLI flags in scripts/gate_12d_paired_control.py, defaults 0.05 / 0.02",
        "source": "scripts/gate_12d_paired_control.py (PR 2); scripts/zeref_continuation_006.py (trainer, #1043 branch)",
    },
    {
        "claim": "model.forward returns a dict; logits are out['logits']",
        "detail": "class RawrphosLM (model.py:242); forward returns {'logits': ...} (model.py:339 on main)",
        "source": "models/rawrphos/architecture/model.py:242 (#1043 branch); model.py:339 (main)",
    },
]

# Metric keys the parser recognizes, in priority order per metric.
# The first key present wins within one source; across sources the merge
# order is: regex scan -> embedded JSON -> receipt JSON (later wins).
METRIC_KEYS = {
    "delta_nll_12d": ["delta_nll_12d", "delta_nll", "delta_nll_true"],
    "jsd_12d": ["jsd_12d", "jsd", "mean_jsd", "jsd_mean"],
}
SUPPORTING_KEYS = [
    "nll_true", "nll_zero", "nll_shuf", "cfjs_loss", "film_rel_amp",
    "film_alpha", "nll_base", "nll_cond",
]
ALL_KEYS = [k for keys in METRIC_KEYS.values() for k in keys] + SUPPORTING_KEYS

KV_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<val>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)")
JSON_RE = re.compile(r"\{[^{}]*\}")

REASON_MISSING = "missing_or_unmeasured_in_logs"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _coerce_number(value):
    """Return float(value) for int/float/str numbers, else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def scan_log_text(text: str) -> dict:
    """Scan one log's text: regex key=value first, then embedded JSON.

    Embedded JSON wins over regex when both carry the same key (JSON is
    structured telemetry; regex is the human-readable echo of it).
    Returns {key: float}.
    """
    found: dict[str, float] = {}
    for match in KV_RE.finditer(text):
        key, raw = match.group("key"), match.group("val")
        if key in ALL_KEYS:
            try:
                found[key] = float(raw)
            except ValueError:
                pass
    for match in JSON_RE.finditer(text):
        try:
            obj = json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        for key in ALL_KEYS:
            if key in obj:
                num = _coerce_number(obj[key])
                if num is not None:
                    found[key] = num
    return found


def merge_metric_values(scanned: dict, receipt: dict | None) -> dict:
    """Resolve one value per metric key. Merge order: log regex/JSON first,
    receipt JSON last — structured receipt values win over log scans.
    Returns {canonical_metric: float}.
    """
    resolved: dict[str, float] = {}
    for metric, keys in METRIC_KEYS.items():
        for key in keys:
            if key in scanned:
                resolved[metric] = scanned[key]
                break
    if receipt:
        for metric, keys in METRIC_KEYS.items():
            for key in keys:
                if key in receipt:
                    num = _coerce_number(receipt[key])
                    if num is not None:
                        resolved[metric] = num
                        break
    return resolved


def load_receipt(path: Path | None) -> tuple[dict | None, bool, str | None]:
    """Load the optional gate receipt. Returns (data, is_stub, note).

    A stub is the "ready" placeholder from gate_12d_paired_control.main()
    before the real verifier lands: status == "ready" and no measured
    delta_nll/jsd keys. A stub contributes NOTHING to MEASURED.
    """
    if path is None:
        return None, False, None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None, False, "receipt is not a JSON object"
    status = data.get("status")
    has_metrics = any(
        key in data for keys in METRIC_KEYS.values() for key in keys
    )
    if status == "ready" and not has_metrics:
        return None, True, (
            "receipt is the 'ready' stub from gate_12d_paired_control.main() "
            "(no measured delta_nll/jsd); contributes nothing"
        )
    return data, False, None


def parse_logs(
    log_paths: list[Path],
    receipt_path: Path | None = None,
    commit_sha: str = "UNVERIFIED",
    run_id: str = "UNVERIFIED",
    pr: str = "UNVERIFIED",
    min_delta_nll: float = 0.05,
    min_jsd: float = 0.02,
) -> dict:
    """Build the separated report. No metric reaches MEASURED unless a real
    measured value meets its threshold."""
    thresholds = {"delta_nll_12d": min_delta_nll, "jsd_12d": min_jsd}
    scanned: dict[str, float] = {}
    observed_logs = []
    for path in log_paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        per_log = scan_log_text(text)
        scanned.update(per_log)
        observed_logs.append({
            "path": str(path),
            "sha256": _sha256_file(path),
            "lines": text.count("\n") + (1 if text and not text.endswith("\n") else 0),
            "keys_found": sorted(per_log),
        })
    receipt, is_stub, stub_note = load_receipt(receipt_path)
    receipt_sha = _sha256_file(receipt_path) if receipt_path is not None else None
    resolved = merge_metric_values(scanned, receipt)

    measured: dict[str, dict] = {}
    null: dict[str, dict] = {}
    for metric, threshold in thresholds.items():
        value = resolved.get(metric)
        if value is None:
            null[metric] = {
                "value": None,
                "threshold": threshold,
                "reason": REASON_MISSING,
            }
        elif value >= threshold:
            measured[metric] = {"value": value, "threshold": threshold}
        else:
            null[metric] = {
                "value": value,
                "threshold": threshold,
                "reason": "below_threshold",
            }
    if is_stub:
        null.setdefault("_receipt", {
            "value": None, "threshold": None, "reason": REASON_MISSING,
        })
        null["_receipt"]["note"] = stub_note

    supporting = {
        key: scanned[key] for key in SUPPORTING_KEYS if key in scanned
    }
    if receipt:
        for key in SUPPORTING_KEYS:
            if key in receipt:
                num = _coerce_number(receipt[key])
                if num is not None:
                    supporting[key] = num

    report = {
        "schema": "zeref-12d-evidence-report-v1",
        "implemented": IMPLEMENTED_CLAIMS,
        "observed": {
            "commit_sha": commit_sha,
            "run_id": run_id,
            "pr": pr,
            "logs": observed_logs,
            "receipt_path": str(receipt_path) if receipt_path else None,
            "receipt_sha256": receipt_sha,
            "receipt_is_stub": is_stub,
            "receipt_note": stub_note,
            "supporting_values": supporting,
        },
        "measured": measured,
        "null": null,
        "thresholds": thresholds,
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["report_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return report


def render_markdown(report: dict) -> str:
    """Render the report as Markdown with the four sections separated."""
    lines = ["# 12D gate evidence report", ""]
    lines.append(f"report_sha256: `{report['report_sha256']}`")
    obs = report["observed"]
    lines.append(f"commit: `{obs['commit_sha']}` | run: `{obs['run_id']}` | PR: `{obs['pr']}`")
    lines.append("")
    lines.append("## IMPLEMENTED (code, not a run)")
    for claim in report["implemented"]:
        lines.append(f"- **{claim['claim']}** — {claim['detail']} ({claim['source']})")
    lines.append("")
    lines.append("## OBSERVED (logs actually read)")
    for log in obs["logs"]:
        keys = ", ".join(log["keys_found"]) if log["keys_found"] else "no recognized keys"
        lines.append(f"- `{log['path']}` sha256 `{log['sha256'][:16]}...` ({log['lines']} lines; {keys})")
    if obs["receipt_path"]:
        stub = " (STUB — contributes nothing)" if obs["receipt_is_stub"] else ""
        lines.append(f"- receipt `{obs['receipt_path']}` sha256 `{obs['receipt_sha256'][:16]}...`{stub}")
    if obs["supporting_values"]:
        lines.append("- supporting: " + ", ".join(
            f"{k}={v}" for k, v in sorted(obs["supporting_values"].items())))
    lines.append("")
    lines.append("## MEASURED (real value met threshold)")
    if report["measured"]:
        for metric, entry in sorted(report["measured"].items()):
            lines.append(f"- **{metric}** = {entry['value']} (threshold {entry['threshold']})")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## NULL (below threshold, or missing/unmeasured)")
    if report["null"]:
        for metric, entry in sorted(report["null"].items()):
            value = entry["value"]
            lines.append(
                f"- **{metric}** = {value} (threshold {entry['threshold']}) — {entry['reason']}"
                + (f"; {entry['note']}" if entry.get("note") else "")
            )
    else:
        lines.append("- (none)")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Parse 12D gate evidence logs into a separated "
                    "IMPLEMENTED / OBSERVED / MEASURED / NULL report.")
    parser.add_argument("--logs", nargs="+", required=True,
                        help="one or more training / gate log files")
    parser.add_argument("--receipt", default=None,
                        help="optional JSON receipt from scripts/gate_12d_paired_control.py")
    parser.add_argument("--commit-sha", default="UNVERIFIED")
    parser.add_argument("--run-id", default="UNVERIFIED")
    parser.add_argument("--pr", default="UNVERIFIED",
                        help="real PR number at runtime; never hardcode one that does not exist")
    parser.add_argument("--min-delta-nll", type=float, default=0.05)
    parser.add_argument("--min-jsd", type=float, default=0.02)
    parser.add_argument("--json-out", default="evidence/post_1043_12d_evidence_report.json")
    parser.add_argument("--md-out", default="evidence/post_1043_12d_evidence_report.md")
    args = parser.parse_args(argv)

    log_paths = [Path(p) for p in args.logs]
    for path in log_paths:
        if not path.is_file():
            print(f"log not found: {path}", file=sys.stderr)
            return 2
    receipt_path = Path(args.receipt) if args.receipt else None
    if receipt_path is not None and not receipt_path.is_file():
        print(f"receipt not found: {receipt_path}", file=sys.stderr)
        return 2

    report = parse_logs(
        log_paths, receipt_path, args.commit_sha, args.run_id, args.pr,
        args.min_delta_nll, args.min_jsd)
    json_path = Path(args.json_out)
    md_path = Path(args.md_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))
    print(f"wrote {json_path} and {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
