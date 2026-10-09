import importlib.util
import sys
from types import SimpleNamespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "azure_quantum_readonly_preflight",
    ROOT / "scripts" / "azure_quantum_readonly_preflight.py",
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class Target:
    def __init__(self, name):
        self.name = name


def test_counts_without_exposing_secrets():
    report = mod.receipt_for([Target("rigetti.sim.qvm"), Target("ionq.simulator")])
    assert report["rigetti_qvm_target_present"]
    assert report["simulator_targets_present"]
    assert report["jobs_submitted"] == 0
    assert report["cloud_database_writes"] == 0
    assert report["cosmos_db_verified"] is False
    assert "connection" not in str(report).lower()


def test_unsupported_names_hidden():
    report = mod.receipt_for([Target("rigetti.sim.qvm"), Target("connection=secret;token=fake")])
    assert report["target_count"] == 1


def test_empty_target_list_does_not_claim_successful_provider_execution():
    report = mod.receipt_for([])
    assert report["target_count"] == 0
    assert report["rigetti_qvm_target_present"] is False


def test_run_uses_explicit_connection_auth_and_preserves_sanitized_receipt(monkeypatch):
    fake_connection = "PUBLIC_OFFLINE_AUTH_FIXTURE"
    authenticated = []

    class Workspace:
        @staticmethod
        def from_connection_string(connection):
            authenticated.append(connection)
            return SimpleNamespace(get_targets=lambda: [Target("rigetti.sim.qvm")])

    monkeypatch.setenv("AZURE_QUANTUM_CONNECTION_STRING", fake_connection)
    monkeypatch.setitem(sys.modules, "qdk.azure", SimpleNamespace(Workspace=Workspace))
    report = mod.run()
    assert authenticated == [fake_connection]
    assert report["rigetti_qvm_target_present"] is True
    assert report["jobs_submitted"] == report["cloud_database_writes"] == 0
    assert fake_connection not in str(report)
