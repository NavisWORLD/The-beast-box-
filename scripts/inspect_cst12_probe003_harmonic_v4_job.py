#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def _service():
    from qiskit_ibm_runtime import QiskitRuntimeService
    token = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("IBM_QUANTUM_TOKEN is empty")
    kwargs: dict[str, str] = {"channel": "ibm_quantum_platform", "token": token}
    instance = os.environ.get("IBM_QUANTUM_INSTANCE", "").strip()
    if instance:
        kwargs["instance"] = instance
    return QiskitRuntimeService(**kwargs)


def _safe_repr(value: Any, limit: int = 1000) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[:limit] + "..."


def _layout_info(circuit: Any) -> dict[str, Any]:
    layout = getattr(circuit, "layout", None)
    out = {"layout_type": type(layout).__name__, "layout_repr": _safe_repr(layout, 2000)}
    if layout is None:
        return out
    for name in ("initial_index_layout", "final_index_layout"):
        method = getattr(layout, name, None)
        if callable(method):
            for kwargs in ({"filter_ancillas": True}, {}):
                try:
                    out[name] = list(method(**kwargs))
                    break
                except Exception:
                    continue
    initial = getattr(layout, "initial_layout", None)
    if initial is not None:
        try:
            out["initial_layout_virtual_bits"] = {
                str(v): int(p) for v, p in initial.get_virtual_bits().items()
            }
        except Exception:
            out["initial_layout_repr"] = _safe_repr(initial, 2000)
    return out


def _extract_circuit(pub: Any) -> Any | None:
    if hasattr(pub, "circuit"):
        return pub.circuit
    if isinstance(pub, (tuple, list)) and pub:
        return pub[0]
    if isinstance(pub, dict):
        for key in ("circuit", "quantum_circuit"):
            if key in pub:
                return pub[key]
    return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--job-id", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()

    job = _service().job(args.job_id)
    inputs = getattr(job, "inputs", None)
    report: dict[str, Any] = {
        "job_id": args.job_id,
        "status": str(getattr(job.status(), "name", job.status())),
        "tags": sorted(list(getattr(job, "tags", []) or [])),
        "inputs_type": type(inputs).__name__,
        "inputs_repr": _safe_repr(inputs, 3000),
    }
    if isinstance(inputs, dict):
        report["input_keys"] = sorted(inputs.keys())
        report["input_value_types"] = {str(k): type(v).__name__ for k, v in inputs.items()}
        pubs = inputs.get("pubs")
        if pubs is not None:
            try:
                report["pub_count"] = len(pubs)
            except Exception:
                pass
            sample_indices = [0, 15, 16, 31, 32, 47, 48, 63]
            samples = []
            for i in sample_indices:
                try:
                    pub = pubs[i]
                except Exception:
                    continue
                item: dict[str, Any] = {
                    "index": i,
                    "pub_type": type(pub).__name__,
                    "pub_repr": _safe_repr(pub, 1500),
                }
                circuit = _extract_circuit(pub)
                if circuit is not None:
                    item.update({
                        "circuit_type": type(circuit).__name__,
                        "num_qubits": int(getattr(circuit, "num_qubits", -1)),
                        "num_clbits": int(getattr(circuit, "num_clbits", -1)),
                        "metadata": getattr(circuit, "metadata", None),
                    })
                    item["layout"] = _layout_info(circuit)
                samples.append(item)
            report["pub_samples"] = samples
    try:
        result = list(job.result())
        report["result_count"] = len(result)
        if result:
            report["first_result_type"] = type(result[0]).__name__
            report["first_result_metadata"] = getattr(result[0], "metadata", None)
            try:
                report["first_counts"] = result[0].join_data().get_counts()
            except Exception as exc:
                report["first_counts_error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        report["result_error"] = f"{type(exc).__name__}: {exc}"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({
        "job_id": args.job_id,
        "input_keys": report.get("input_keys"),
        "pub_count": report.get("pub_count"),
        "result_count": report.get("result_count"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
