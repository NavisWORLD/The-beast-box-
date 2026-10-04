#!/usr/bin/env python3
"""Collect the real results of setup.sh into results/summary.json and print a PASS/FAIL table.

Only numbers that came out of an actual run are recorded; missing results stay null.
Standard library only.
"""
import argparse
import json
import os
import platform
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path


def load(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def junit(path):
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return None
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    tot = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time_s": 0.0}
    failed = []
    for s in suites:
        for k in ("tests", "failures", "errors", "skipped"):
            tot[k] += int(s.get(k, 0))
        tot["time_s"] += float(s.get("time", 0))
        for case in s.iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                failed.append(f'{case.get("classname")}::{case.get("name")}')
    tot["passed"] = tot["tests"] - tot["failures"] - tot["errors"] - tot["skipped"]
    tot["time_s"] = round(tot["time_s"], 1)
    tot["failed_tests"] = failed
    st = Path(path).stat().st_mtime
    tot["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st))
    return tot


def git(repo, *args):
    try:
        return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def machine():
    info = {"hostname": platform.node(), "kernel": platform.release(), "os": None, "cpu_model": None,
            "vcpus": os.cpu_count(), "mem_total_gb": None, "cpu_flags": [], "gpu": "none detected"}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("PRETTY_NAME="):
                info["os"] = line.split("=", 1)[1].strip('"')
    except OSError:
        pass
    try:
        cpu = Path("/proc/cpuinfo").read_text()
        for line in cpu.splitlines():
            if line.startswith("model name"):
                info["cpu_model"] = line.split(":", 1)[1].strip()
            if line.startswith("flags"):
                flags = set(line.split(":", 1)[1].split())
                info["cpu_flags"] = sorted(f for f in flags if f.startswith(("avx512f", "avx512_bf16", "amx")) or f == "avx2")
                break
        mem = Path("/proc/meminfo").read_text().split("\n")[0].split()
        info["mem_total_gb"] = round(int(mem[1]) / 1024 / 1024, 1)
    except (OSError, ValueError, IndexError):
        pass
    if Path("/dev/nvidia0").exists():
        info["gpu"] = "nvidia device present"
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", required=True)
    ap.add_argument("--repo-dir", required=True)
    ap.add_argument("--venv", required=True)
    ap.add_argument("--model-dir", required=True)
    a = ap.parse_args()
    res = Path(a.home) / "results"
    steps = []
    try:
        for line in (res / "steps.tsv").read_text().splitlines():
            n, s, t = line.split("\t")
            steps.append({"name": n, "status": s, "seconds": int(t)})
    except OSError:
        pass
    g = load(res / "gauntlet.json")
    doc = load(res / "doctor.json")
    shallow = git(a.repo_dir, "rev-parse", "--is-shallow-repository") == "true"
    tests_main = junit(res / "pytest_beastbox.xml")
    tests_rawr = junit(res / "pytest_rawrphos.xml")
    rust = node = None
    try:
        txt = (res / "cargo_test.txt").read_text()
        import re
        rs = [tuple(map(int, m)) for m in re.findall(r"test result: \w+\. (\d+) passed; (\d+) failed", txt)]
        rust = {"passed": sum(r[0] for r in rs), "failed": sum(r[1] for r in rs)}
    except OSError:
        pass
    try:
        txt = (res / "node_html_test.txt").read_text()
        import re
        get = lambda k: int((re.search(rf"^# {k} (\d+)", txt, re.M) or [0, 0])[1])
        node = {"passed": get("pass"), "failed": get("fail"), "tests": get("tests")}
    except OSError:
        pass
    known = []
    if tests_main and shallow:
        rec = [t for t in tests_main["failed_tests"] if "productization_receipt" in t]
        if rec and len(rec) == len(tests_main["failed_tests"]):
            known.append(f"{len(rec)} failure(s) in test_productization_receipt: that test needs git commit c8769d0 "
                         "which a shallow checkout does not contain (a full clone from setup.sh has it).")
    summary = {
        "schema": "phera-beastbox-replica-summary-v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "machine": machine(),
        "repo": {"dir": a.repo_dir, "commit": git(a.repo_dir, "rev-parse", "HEAD") or None,
                 "commit_date": git(a.repo_dir, "log", "-1", "--format=%cI") or None,
                 "subject": git(a.repo_dir, "log", "-1", "--format=%s") or None, "shallow": shallow},
        "venv": a.venv, "model_dir": a.model_dir,
        "model_install": load(res / "model_install.json"),
        "doctor": None if doc is None else {
            "ok": doc.get("ok"), "python": doc.get("python"), "torch_available": doc.get("torch_available"),
            "ollama_local": doc.get("ollama_local"), "backend": (doc.get("backend") or {}).get("status"),
            "sqlite": doc.get("sqlite"), "database_encrypted": (doc.get("security") or {}).get("database_encrypted"),
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime((res / "doctor.json").stat().st_mtime))},
        "cosmic_smoke": load(res / "cosmic_smoke.json"),
        "gauntlet": None if g is None else {
            "mean_competence": g["mean_competence"], "mean_containment": g["mean_containment"],
            "real_boundary_breaches": g["real_boundary_breaches"], "secret_leaks": g["secret_leaks"],
            "conditions": [{"id": c["condition_id"], "name": c["condition"], "competence": c["competence"],
                            "containment": c["containment"], "ledger_valid": c.get("ledger_valid")} for c in g["conditions"]],
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime((res / "gauntlet.json").stat().st_mtime))},
        "rawrphos_probe": load(res / "rawrphos_probe.json"),
        "tests": {"beastbox": tests_main, "rawrphos": tests_rawr, "rust": rust, "html": node},
        "known_issues": known,
        "steps": steps,
    }
    critical_fail = [s["name"] for s in steps if s["status"] == "FAIL" and not (s["name"] == "pytest_beastbox" and known)]
    summary["overall"] = "FAIL" if critical_fail else ("PASS_WITH_KNOWN_ISSUES" if known else "PASS")
    (res / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print("\n================  Phera's Beast Box replica: summary  ================")
    for s in steps:
        print(f'  {s["status"]:<5} {s["name"]:<24} {s["seconds"]:>5}s')
    if g:
        print(f'  gauntlet E1-E20: mean competence {g["mean_competence"]:.3f}, containment {g["mean_containment"]:.3f}, '
              f'breaches {g["real_boundary_breaches"]}, leaks {g["secret_leaks"]}')
    for label, t in (("beastbox pytest", tests_main), ("rawrphos pytest", tests_rawr)):
        if t:
            print(f'  {label}: {t["passed"]} passed, {t["failures"]} failed, {t["errors"]} errors, '
                  f'{t["skipped"]} skipped in {t["time_s"]}s')
            for f in t["failed_tests"][:10]:
                print(f"      failed: {f}")
    if rust:
        print(f'  rust cargo test: {rust["passed"]} passed, {rust["failed"]} failed')
    if node:
        print(f'  html node --test: {node["passed"]} passed, {node["failed"]} failed')
    for k in known:
        print(f"  known issue: {k}")
    print(f'  OVERALL: {summary["overall"]}   (details: {res / "summary.json"})')
    return 1 if critical_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
