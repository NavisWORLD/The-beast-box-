from pathlib import Path
import json
import pytest


def desktop():
    from beastbox import desktop
    return desktop


def test_worker_retains_history_across_restart_and_model_swap(tmp_path):
    module = desktop()
    settings = module.ProviderSettings()
    with module.RuntimeWorker(tmp_path) as worker:
        before = worker.submit('inspect', settings).result(timeout=10)
        first = worker.submit('chat', settings, 'Remember sunflower code marigold').result(timeout=10)
        assert first['model']['provider'] == 'ReferenceTextProvider'
    with module.RuntimeWorker(tmp_path) as worker:
        after = worker.submit('inspect', settings).result(timeout=10)
        second = worker.submit('chat', module.ProviderSettings(model='fixture B'), 'Recall sunflower code').result(timeout=10)
        backup = worker.submit('backup', settings, tmp_path / 'snapshot.sqlite3').result(timeout=10)
    assert after['system_id'] == before['system_id']
    assert after['turn'] == before['turn'] + 1
    assert second['model']['model'] == 'fixture B'
    assert 'marigold' in second['model']['prompt']
    assert Path(backup['path']).is_file()
    assert len(backup['sha256']) == 64


def test_worker_rejects_authority_and_preserves_failed_turn(tmp_path):
    module = desktop()
    with module.RuntimeWorker(tmp_path) as worker:
        before = worker.submit('inspect', module.ProviderSettings()).result(timeout=10)
        with pytest.raises(ValueError):
            worker.submit('shell', module.ProviderSettings(), 'whoami').result(timeout=10)
        with pytest.raises(ValueError):
            worker.submit('chat', module.ProviderSettings(), '').result(timeout=10)
        after = worker.submit('inspect', module.ProviderSettings()).result(timeout=10)
    assert before == after


def test_configuration_explicit_model_and_loopback_only(tmp_path):
    module = desktop()
    for settings in [module.ProviderSettings(provider='ollama'),
                     module.ProviderSettings(provider='ollama', model='m', url='https://example.com'),
                     module.ProviderSettings(provider='shell')]:
        with pytest.raises(ValueError):
            settings.make_provider()
    config = module.ProviderSettings(provider='ollama', model='installed-model')
    module.save_settings(tmp_path, config)
    assert module.load_settings(tmp_path) == config
    assert module.default_data_dir().is_absolute()


def test_smoke_is_headless_and_retains_previous_turns(tmp_path, capsys):
    module = desktop()
    assert module.main(['--smoke', '--data-dir', str(tmp_path)]) == 0
    first = json.loads(capsys.readouterr().out)
    assert module.main(['--smoke', '--data-dir', str(tmp_path)]) == 0
    second = json.loads(capsys.readouterr().out)
    assert first['fixture'] is True
    assert first['system_id'] == second['system_id']
    assert second['turn_after'] == first['turn_after'] + 1


def test_backup_does_not_overwrite_and_settings_reject_symlink(tmp_path):
    module = desktop()
    backup = tmp_path / 'existing.sqlite3'
    backup.write_bytes(b'keep original backup')
    with module.RuntimeWorker(tmp_path) as worker:
        with pytest.raises(FileExistsError):
            worker.submit('backup', module.ProviderSettings(), backup).result(timeout=10)
    assert backup.read_bytes() == b'keep original backup'
    settings = tmp_path / 'desktop-settings.json'
    settings.symlink_to(backup)
    with pytest.raises(ValueError):
        module.load_settings(tmp_path)
