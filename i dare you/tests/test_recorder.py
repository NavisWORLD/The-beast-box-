import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('recorder', Path(__file__).parents[1] / 'recorder.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def test_ledger_detects_tampering(tmp_path):
    log = r.Ledger(tmp_path / 'events.jsonl')
    log.emit('A0', 'test', {'actual': True})
    assert r.verify_ledger(log.path)[0]['payload']['actual']
    data = log.path.read_text().replace('true', 'false')
    log.path.write_text(data)
    with pytest.raises(ValueError, match='corrupted'):
        r.verify_ledger(log.path)


def test_checkpoint_controls_and_fail_closed(tmp_path, monkeypatch):
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    dest = tmp_path / 'run'
    r.run(dest)
    ledger = r.verify_ledger(dest / 'events.jsonl')
    assert ledger[-1]['payload']['cross_provider_continuity'] == 'NOT_MEASURED'
    assert not (dest / 'training_metrics.jsonl').read_bytes()
    assert json.loads((dest / 'continuity_checkpoints.json').read_text())['verified']
    assert json.loads((dest / 'reproduction_manifest.json').read_text())['controls']['empty_memory']['memory_count'] == 0
    assert json.loads((dest / 'reproduction_manifest.json').read_text())['controls']['shuffled_memory']['memory_context_matches_full'] is False
    assert not (dest / 'private_jev' / 'jev_events.jsonl').exists()
    with pytest.raises(FileExistsError):
        r.run(dest)


def test_jev_never_requires_key_for_offline(tmp_path, monkeypatch):
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    r.run(tmp_path / 'dry', enable_jev=True)
    events = r.verify_ledger(tmp_path / 'dry' / 'events.jsonl')
    assert any(e['event_type'] == 'phase_blocked' and e['phase'] == 'A0' for e in events)


def test_local_only_phos_adapter():
    with pytest.raises(ValueError, match='loopback'):
        r.phos_generate('hi', 'https://example.com')
