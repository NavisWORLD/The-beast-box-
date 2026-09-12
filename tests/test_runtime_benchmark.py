"""Benchmark evidence must describe real runtime behavior and comparable workloads."""

import copy
import importlib.util
import json
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "scripts" / "benchmark_runtime.py"


def load_driver():
    assert DRIVER.is_file(), "offline runtime benchmark driver is missing"
    spec = importlib.util.spec_from_file_location("runtime_benchmark", DRIVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def receipt():
    return {
        "schema": "runtime-benchmark-v1",
        "fixture_sha256": "fixture",
        "measurement": {"repetitions": 2, "workloads": ["small"]},
        "environment": {"python": "test", "platform": "test"},
        "source": {"head": "abc", "stable_during_run": True},
        "correctness": {"passed": True, "checks": {"runtime_valid": True}},
        "behavior_sha256": "same-behavior",
        "summary": {"small": {"e2e_seconds": {"median": 2.0, "samples": [1.0, 3.0]}}},
    }


def test_comparison_reports_signed_raw_delta_without_a_timing_gate():
    driver = load_driver()
    before = receipt()
    after = copy.deepcopy(before)
    after["source"]["head"] = "def"
    after["summary"]["small"]["e2e_seconds"] = {"median": 3.0, "samples": [2.0, 4.0]}
    comparison = driver.compare_results(before, after)
    assert comparison["comparable"] is True
    assert comparison["deltas"]["small"]["e2e_seconds"] == {
        "before_median": 2.0, "after_median": 3.0, "absolute": 1.0, "percent": 50.0,
    }


@pytest.mark.parametrize("mutation,reason", [
    ("fixture", "fixture"),
    ("correctness", "correctness"),
    ("check_detail", "correctness"),
    ("behavior", "behavior"),
    ("configuration", "measurement"),
    ("environment", "environment"),
    ("source_changed", "source"),
])
def test_comparison_refuses_incompatible_or_failed_evidence(mutation, reason):
    driver = load_driver()
    before = receipt()
    after = copy.deepcopy(before)
    if mutation == "fixture":
        after["fixture_sha256"] = "different"
    elif mutation == "correctness":
        after["correctness"]["passed"] = False
    elif mutation == "check_detail":
        after["correctness"]["checks"]["runtime_valid"] = False
    elif mutation == "behavior":
        after["behavior_sha256"] = "different"
    elif mutation == "configuration":
        after["measurement"]["repetitions"] = 1
    elif mutation == "environment":
        after["environment"]["python"] = "different"
    else:
        after["source"]["stable_during_run"] = False
    comparison = driver.compare_results(before, after)
    assert comparison["comparable"] is False
    assert not comparison["deltas"]
    assert any(reason in item for item in comparison["refusal_reasons"])


def test_context_presence_does_not_count_conflicting_or_irrelevant_rows_as_relevant():
    quality = load_driver().context_quality(
        [{"kind": "user_turn", "text": "code marigold"},
         {"kind": "user_turn", "text": "outdated code violet"},
         {"kind": "user_turn", "text": "unrelated granite sample"}],
        expected="marigold", conflicting="violet",
    )
    assert quality["recall_present"] is True
    assert quality["primary_recall_present"] is True
    assert quality["relevant_count"] == 1
    assert quality["conflicting_count"] == 1
    assert quality["irrelevant_count"] == 1
    assert quality["semantic_answer_evaluation"] == "NOT_MEASURED"


@pytest.mark.parametrize("ambient_credentials", [False, True])
def test_driver_uses_selected_checkout_and_reports_real_sqlite_runtime(tmp_path, monkeypatch, ambient_credentials):
    if ambient_credentials:
        monkeypatch.setenv("BEASTBOX_SEAL_PASSPHRASE", "benchmark-test-passphrase")
        # A synthetic matching value makes accidental inheritance observable:
        # portable export must not inspect the parent process's credentials.
        monkeypatch.setenv("OPENAI_API_KEY", "amber sunflower project")
    load_driver()
    selected = tmp_path / "selected"
    selected.mkdir()
    shutil.copytree(ROOT / "beastbox", selected / "beastbox", ignore=shutil.ignore_patterns("__pycache__"))
    for command in (["git", "init", "-q"], ["git", "add", "beastbox"],
                    ["git", "-c", "user.name=Benchmark Test", "-c", "user.email=benchmark@example.invalid",
                     "commit", "-qm", "isolated source fixture"]):
        subprocess.run(command, cwd=selected, check=True, capture_output=True)
    if not ambient_credentials:
        # An unchecked stale cache is authoritative to normal Python imports.
        # Measurements must use the selected source, regardless of local caches.
        provider_source = selected / "beastbox" / "providers.py"
        original = provider_source.read_bytes()
        try:
            provider_source.write_text("raise RuntimeError('stale benchmark bytecode')\n")
            py_compile.compile(str(provider_source), doraise=True,
                               invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
        finally:
            provider_source.write_bytes(original)
    output = tmp_path / "result.json"
    run = subprocess.run(
        [sys.executable, str(DRIVER), "--source-root", str(selected), "--output", str(output),
         "--repetitions", "1", "--workloads", "small"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert run.returncode == 0, run.stderr + run.stdout
    result = json.loads(output.read_text())
    assert result["correctness"]["passed"] is True
    assert result["source"]["root"] == str(selected.resolve())
    assert result["source"]["stable_during_run"] is True
    sample = result["repetitions"][0]
    assert all(Path(origin).is_relative_to(selected) for origin in sample["module_origins"].values())
    small = sample["workloads"]["small"]
    assert small["metrics"]["provider_calls"] == 3
    assert small["metrics"]["sql_statements"] > 0
    assert small["metrics"]["retrieval_sql_statements"] > 0
    assert small["metrics"]["prompt_chars"] > small["metrics"]["output_chars"] > 0
    assert len(small["turns"]) == 3
    assert small["turns"][-1]["quality"]["recall_present"] is True
    assert "ttft_seconds" not in small["metrics"]
    assert sample["acceptance"]["checks"]["provider_failure_rollback"] is True
    assert sample["acceptance"]["checks"]["portable_import_restart"] is True
    assert sample["acceptance"]["checks"]["tool_authority_denied"] is True
