"""CPU contract tests: provider replies below are mocks, never live evidence."""
import json
import sys
import traceback
from types import SimpleNamespace

import pytest

from beastbox import optional_resources as resources
from beastbox.events import normalize_event


@pytest.fixture(autouse=True)
def clean_resource_env(monkeypatch):
    for key in resources.RESOURCE_ENV:
        monkeypatch.delenv(key, raising=False)


def ibm_mock(monkeypatch, counts=None, **receipt_changes):
    from beastbox import quantum
    monkeypatch.setenv("IBM_QUANTUM_TOKEN", "private-token-sentinel")
    monkeypatch.setenv("IBM_QUANTUM_BACKEND", "ibm_mock_backend")
    receipt = dict(job_id="mock-native-job", backend="ibm_mock_backend", shots=128,
                   circuit_sha256="a" * 64)
    receipt.update(receipt_changes)
    monkeypatch.setattr(quantum, "submit_real", lambda *a, **kw: SimpleNamespace(**receipt))
    monkeypatch.setattr(quantum, "retrieve_counts", lambda job_id: {"01": 96, "10": 32} if counts is None else counts)


def azure_mock(monkeypatch, results=None, actual_target="ionq.simulator"):
    monkeypatch.setenv("AZURE_QUANTUM_RESOURCE_ID", "private-workspace-sentinel")
    monkeypatch.setenv("AZURE_QUANTUM_LOCATION", "westus")
    monkeypatch.setenv("AZURE_QUANTUM_TARGET", "ionq.simulator")
    job = SimpleNamespace(id="mock-azure-job", details=SimpleNamespace(target=actual_target),
                          get_results=lambda **kw: {"histogram": {"0": .25, "3": .75}} if results is None else results)
    target = SimpleNamespace(name=actual_target, submit=lambda *a, **kw: job)
    workspace = SimpleNamespace(get_targets=lambda **kw: target)
    monkeypatch.setitem(sys.modules, "qdk", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "qdk.azure", SimpleNamespace(Workspace=lambda **kw: workspace))
    return target


def test_doctor_never_returns_values_or_authenticates(monkeypatch):
    monkeypatch.setenv("IBM_QUANTUM_TOKEN", "private-token-sentinel")
    status = resources.resource_status()
    assert status["ibm"]["IBM_QUANTUM_TOKEN"] == "configured"
    assert status["azure"]["AZURE_QUANTUM_RESOURCE_ID"] == "missing"
    assert set(value for provider in status.values() for value in provider.values()) <= {"configured", "missing"}
    assert "private-token-sentinel" not in json.dumps(status)


@pytest.mark.parametrize("provider", ["ibm", "azure"])
def test_submission_requires_literal_true_before_any_import(provider):
    for flag in [False, 1, "yes", None]:
        with pytest.raises(resources.ResourceUnavailable, match="allow_live=True"):
            resources.quantum_event(provider, allow_live=flag)


@pytest.mark.parametrize("shots", [0, -1, 1025, True, 1.5, "128"])
def test_shots_are_bounded(shots):
    with pytest.raises(ValueError, match="shots"):
        resources.quantum_event("ibm", shots=shots, allow_live=True)


def test_unknown_provider_and_missing_config_fail_closed():
    with pytest.raises(ValueError, match="provider"):
        resources.quantum_event("fake", allow_live=True)
    with pytest.raises(resources.ResourceUnavailable, match="configuration"):
        resources.quantum_event("ibm", allow_live=True)


def test_ibm_mock_preserves_observed_counts_native_job_backend_and_mode(monkeypatch):
    ibm_mock(monkeypatch)
    event = resources.quantum_event("ibm", allow_live=True)
    metadata = json.loads(event["text"])
    assert metadata["result_kind"] == "observed-counts"
    assert metadata["counts"] == {"01": 96, "10": 32}
    assert metadata["native_job_id"] == "mock-native-job"
    assert metadata["backend"] == "ibm_mock_backend"
    assert metadata["mode"] == "REAL_IBM"
    assert metadata["source"] == "ibm-quantum"
    assert event["features"] == [-1., .5, -.5, -1.]
    assert normalize_event(event)["source"] == "software-event"
    assert "private-token-sentinel" not in repr(event)


@pytest.mark.parametrize("counts", [{}, {"00": -1}, {"00": 128.5}, {"00": True}, {"99": 128}, {"00": 127}])
def test_ibm_malformed_counts_rejected(monkeypatch, counts):
    ibm_mock(monkeypatch, counts=counts)
    with pytest.raises(resources.ResourceUnavailable):
        resources.quantum_event("ibm", allow_live=True)


def test_sdk_exception_is_redacted_including_traceback(monkeypatch):
    ibm_mock(monkeypatch)
    from beastbox import quantum
    def fail(*args, **kwargs):
        raise RuntimeError("private-token-sentinel")
    monkeypatch.setattr(quantum, "submit_real", fail)
    with pytest.raises(resources.ResourceUnavailable) as raised:
        resources.quantum_event("ibm", allow_live=True)
    assert "private-token-sentinel" not in "".join(traceback.format_exception(raised.value))


def test_native_metadata_cannot_echo_credentials(monkeypatch):
    ibm_mock(monkeypatch, job_id="private-token-sentinel")
    with pytest.raises(resources.ResourceUnavailable):
        resources.quantum_event("ibm", allow_live=True)


def test_azure_mock_retains_probabilities_without_manufacturing_counts(monkeypatch):
    azure_mock(monkeypatch)
    event = resources.quantum_event("azure", shots=1, allow_live=True)
    metadata = json.loads(event["text"])
    assert metadata["probabilities"] == {"00": .25, "11": .75}
    assert metadata["result_kind"] == "probabilities"
    assert metadata["mode"] == "AZURE_IONQ_SIMULATOR"
    assert metadata["native_job_id"] == "mock-azure-job"
    assert metadata["backend"] == "ionq.simulator"
    assert "counts" not in metadata
    assert "private-workspace-sentinel" not in repr(event)
    normalize_event(event)


@pytest.mark.parametrize("result", [{}, {"histogram": {}}, {"histogram": {"0": float("nan")}},
                                     {"histogram": {"0": -1}}, {"histogram": {"0": 128}},
                                     {"histogram": {"4": 1}}, {"histogram": {"0": .8}}])
def test_azure_invalid_distributions_fail_without_fallback(monkeypatch, result):
    azure_mock(monkeypatch, results=result)
    with pytest.raises(resources.ResourceUnavailable):
        resources.quantum_event("azure", allow_live=True)


def test_azure_refuses_unrequested_target(monkeypatch):
    azure_mock(monkeypatch, actual_target="ionq.qpu.aria-1")
    with pytest.raises(resources.ResourceUnavailable, match="target"):
        resources.quantum_event("azure", allow_live=True)


def test_missing_azure_sdk_fails_clearly(monkeypatch):
    azure_mock(monkeypatch)
    monkeypatch.setitem(sys.modules, "qdk.azure", None)
    with pytest.raises(resources.ResourceUnavailable, match="SDK"):
        resources.quantum_event("azure", allow_live=True)


def test_azure_submission_preserves_explicit_shot_limit(monkeypatch):
    target = azure_mock(monkeypatch)
    original = target.submit
    calls = []
    def submit(circuit, *, name, shots):
        calls.append((circuit, name, shots))
        return original()
    target.submit = submit
    resources.quantum_event("azure", shots=7, allow_live=True)
    assert len(calls) == 1
    assert calls[0][0]["qubits"] == 2
    assert calls[0][2] == 7


def test_azure_sdk_failure_traceback_is_sanitized(monkeypatch):
    target = azure_mock(monkeypatch)
    def submit(*args, **kwargs):
        raise RuntimeError("private-workspace-sentinel")
    target.submit = submit
    with pytest.raises(resources.ResourceUnavailable) as raised:
        resources.quantum_event("azure", allow_live=True)
    assert "private-workspace-sentinel" not in "".join(traceback.format_exception(raised.value))
