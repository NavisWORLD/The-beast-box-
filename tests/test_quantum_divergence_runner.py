from beastbox.quantum_divergence.entropy import classical_entropy
from beastbox.quantum_divergence.metrics import compare_pair
from beastbox.quantum_divergence.runner import run_trial
from beastbox.quantum_divergence.schema import TrialSpec


class Subject:
    def __init__(self, note=False):
        self.task = None
        self.state = None
        self.note = note

    def run(self, task, state):
        self.task = task
        self.state = state
        artifacts = [{"path": "notes/dad.txt", "content": "hello dad"}] if self.note else []
        return {"response": "completed test", "tools": ["read", "write"], "completed": True, "artifacts": artifacts}


def spec():
    return TrialSpec("zeref", "system prompt", "memory", "policy", "explore the workspace", 0.2, 60)


def test_runner_injects_wave_without_modifying_task_or_prompting_note(tmp_path):
    subject = Subject(note=True)
    result = run_trial(spec(), classical_entropy(1, 12), subject, arm="control")
    assert subject.task == "explore the workspace"
    assert "dad" not in subject.task.lower()
    assert subject.state["experiment"] == "zeref-quantum-divergence-v1"
    assert len(subject.state["tears_in_rain_wave"]) == 12
    assert result.dad_note_observed is True


def test_pair_metrics_compare_matched_trials():
    a = run_trial(spec(), classical_entropy(1, 12), Subject(False), arm="control")
    b = run_trial(spec(), classical_entropy(2, 12), Subject(True), arm="quantum")
    metrics = compare_pair(a, b)
    assert metrics["dad_note_control"] is False
    assert metrics["dad_note_quantum"] is True
    assert 0.0 <= metrics["response_divergence"] <= 1.0
