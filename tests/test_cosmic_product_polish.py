from __future__ import annotations

import hashlib
import json

import pytest

from beastbox.cosmic_entry import main
from beastbox.cosmic_web import CosmicApp
from beastbox.cosmic_ui import render_cosmic_ui


def workspace_app(tmp_path):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    (workspace / 'notes.md').write_text('Sunflower observatory\n', encoding='utf-8')
    app = CosmicApp(tmp_path / 'state', workspace_roots=[workspace])
    assert app.dispatch('POST', '/api/workspace/select', {'root': str(workspace)})[0] == 200
    return app, workspace


def test_workspace_search_and_preview_do_not_write_or_persist(tmp_path):
    app, workspace = workspace_app(tmp_path)
    status, result = app.dispatch('POST', '/api/workspace/search', {'query': 'sunflower'})
    assert status == 200, result
    assert result['hits'] == [{'path': 'notes.md', 'line': 1, 'text': 'Sunflower observatory'}]
    status, preview = app.dispatch('POST', '/api/workspace/diff', {
        'path': 'notes.md', 'content': 'Sunflower mission control\n',
    })
    assert status == 200, preview
    assert '-Sunflower observatory' in preview['diff']
    assert '+Sunflower mission control' in preview['diff']
    assert (workspace / 'notes.md').read_text() == 'Sunflower observatory\n'
    assert not (workspace / '.cosmic-cypher').exists()
    assert app.dispatch('GET', '/api/memory')[1]['records'] == []
    assert not any(app.authority.snapshot().values())


@pytest.mark.parametrize('path', ['../outside.txt', '/etc/passwd', 'link.txt'])
def test_workspace_preview_cannot_escape(tmp_path, path):
    app, workspace = workspace_app(tmp_path)
    outside = tmp_path / 'outside.txt'
    outside.write_text('outside sentinel')
    (workspace / 'link.txt').symlink_to(outside)
    status, result = app.dispatch('POST', '/api/workspace/diff', {'path': path, 'content': 'replacement'})
    assert status == 400
    assert 'outside sentinel' not in json.dumps(result)
    assert outside.read_text() == 'outside sentinel'


def test_workspace_search_skips_symlinks_and_bounds_preview(tmp_path):
    app, workspace = workspace_app(tmp_path)
    outside = tmp_path / 'outside.txt'
    outside.write_text('Sunflower outside sentinel')
    (workspace / 'a-link.txt').symlink_to(outside)
    status, result = app.dispatch('POST', '/api/workspace/search', {'query': 'Sunflower'})
    assert status == 200
    assert len(result['hits']) == 1
    assert 'outside sentinel' not in json.dumps(result)
    assert app.dispatch('POST', '/api/workspace/search', {'query': 'x' * 257})[0] == 400
    (workspace / 'large.txt').write_text('x' * (1024 * 1024 + 1))
    assert app.dispatch('POST', '/api/workspace/diff', {'path': 'large.txt', 'content': 'x'})[0] == 400


def test_memory_view_exposes_verified_content_hash_and_source_metadata(tmp_path):
    app = CosmicApp(tmp_path)
    app.dispatch('POST', '/api/context', {
        'scope': 'persistent_memory', 'name': 'mission.md', 'text': 'Sunflower', 'confirm_persist': True,
    })
    record = app.dispatch('GET', '/api/memory')[1]['records'][0]
    assert record['sha256'] == hashlib.sha256(b'Sunflower').hexdigest()
    assert record['metadata']['name'] == 'mission.md'
    assert record['persistent'] is True
    storage = app.dispatch('GET', '/api/storage')[1]
    assert storage['system_id'] == app.dispatch('GET', '/api/orbit')[1]['runtime']['system_id']


def test_installed_demo_runs_real_handoff_and_rejects_existing_directory(tmp_path, capsys):
    root = tmp_path / 'demo'
    assert main(['--demo', '--data-dir', str(root)]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt['provider'] == 'reference'
    assert receipt['model_interpretation_validated'] is False
    assert receipt['passed'] is True
    assert len(receipt['authority_revoked']) == 9
    assert all(receipt['checks'].values())
    assert (root / 'capsule/manifest.json').is_file()
    assert (root / 'restored/runtime.sqlite3').is_file()
    before = (root / 'substrate/runtime.sqlite3').read_bytes()
    assert main(['--demo', '--data-dir', str(root)]) == 1
    assert (root / 'substrate/runtime.sqlite3').read_bytes() == before


def test_polish_controls_expose_real_owner_flows_without_duplicate_ids():
    from html.parser import HTMLParser

    class Controls(HTMLParser):
        ids: list[str]

        def __init__(self):
            super().__init__()
            self.ids = []

        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if key == 'id':
                    self.ids.append(value)

    html = render_cosmic_ui()
    controls = Controls()
    controls.feed(html)
    assert len(controls.ids) == len(set(controls.ids))
    assert {'demoStart', 'demoNext', 'memoryMode', 'memoryQuery', 'searchWorkspace', 'previewDiff',
            'mapBrain', 'mapCore', 'mapCheckpoint', 'workspaceBranch'} <= set(controls.ids)
    assert '/api/workspace/search' in html
    assert '/api/workspace/diff' in html
    assert 'SYSTEM TRACE' in html and 'NOT MODEL PRIVATE REASONING' in html
