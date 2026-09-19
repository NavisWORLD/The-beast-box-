from __future__ import annotations

import json

import pytest

from beastbox.cosmic_web import CosmicApp
from beastbox.cypher.workspace import Workspace


def test_context_is_delivered_once_without_persisting_source_or_echo(tmp_path):
    app = CosmicApp(tmp_path)
    secret = 'temporary-sunflower-987654321'
    status, record = app.dispatch('POST', '/api/context', {
        'scope': 'temporary_attachment', 'name': 'note.txt', 'text': secret,
    })
    assert status == 200
    assert app.dispatch('GET', '/api/context')[1]['contexts'][0]['lifetime'] == 'TURN_ATTACHMENT'
    status, result = app.dispatch('POST', '/api/chat', {'text': 'Read the attachment', 'context_ids': [record['id']]})
    assert status == 200, result
    assert secret in result['result']['response']
    assert app.dispatch('GET', '/api/context')[1]['contexts'] == []
    assert secret not in json.dumps(app.dispatch('GET', '/api/memory')[1])
    assert secret.encode() not in (tmp_path / 'runtime.sqlite3').read_bytes()
    assert app.dispatch('POST', '/api/chat', {'text': 'again', 'context_ids': [record['id']]})[0] == 400


def test_session_context_is_explicit_removable_and_not_restored(tmp_path):
    app = CosmicApp(tmp_path)
    _, record = app.dispatch('POST', '/api/context', {
        'scope': 'conversation_context', 'name': 'n', 'text': 'staged-only-content',
    })
    assert 'staged-only-content' not in app.dispatch('POST', '/api/chat', {'text': 'hello'})[1]['result']['response']
    assert CosmicApp(tmp_path).dispatch('GET', '/api/context')[1]['contexts'] == []
    assert app.dispatch('POST', '/api/context/remove', {'id': record['id']})[0] == 200
    assert app.dispatch('GET', '/api/context')[1]['contexts'] == []


@pytest.mark.parametrize('argv', [
    ['/tmp/git', 'status'], ['git', 'diff', '--no-index', '/etc/passwd', '/etc/hosts'],
    ['git', 'show', '--output=/tmp/escape'], ['pytest'], ['git', 'push'],
])
def test_browser_runner_cannot_escape_readonly_policy(tmp_path, argv):
    app = CosmicApp(tmp_path / 'data', workspace_roots=[tmp_path])
    app.dispatch('POST', '/api/workspace/select', {'root': str(tmp_path)})
    app.dispatch('POST', '/api/authority', {'action': 'grant', 'name': 'tools'})
    assert app.dispatch('POST', '/api/workspace/run', {'argv': argv})[0] in {400, 403}


def test_workspace_backup_symlink_cannot_escape(tmp_path):
    root = tmp_path / 'workspace'
    root.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (root / '.cosmic-cypher').symlink_to(outside, target_is_directory=True)
    (root / 'note.txt').write_text('before')
    with pytest.raises(ValueError):
        Workspace(root).write('note.txt', 'after')
    assert not list(outside.iterdir())
    assert (root / 'note.txt').read_text() == 'before'


def test_provider_invalid_kind_is_rejected_without_exception(tmp_path):
    assert CosmicApp(tmp_path).dispatch('POST', '/api/provider', {'kind': []})[0] == 400


def test_repo_status_does_not_execute_workspace_fsmonitor(tmp_path):
    import subprocess
    root = tmp_path / 'repo'
    root.mkdir()
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    hook = root / 'monitor.sh'
    hook.write_text('#!/bin/sh\ntouch "$PWD/monitor-ran"\n')
    hook.chmod(0o700)
    subprocess.run(['git', '-C', str(root), 'config', 'core.fsmonitor', str(hook)], check=True)
    app = CosmicApp(tmp_path / 'state', workspace_roots=[root])
    app.dispatch('POST', '/api/workspace/select', {'root': str(root)})
    assert app.dispatch('GET', '/api/workspace/status')[0] == 200
    assert not (root / 'monitor-ran').exists()


def test_browser_repository_never_discovers_parent_or_external_gitdir(tmp_path):
    import subprocess
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    child = tmp_path / 'child'
    child.mkdir()
    app = CosmicApp(tmp_path / 'state', workspace_roots=[child])
    app.dispatch('POST', '/api/workspace/select', {'root': str(child)})
    assert app.dispatch('GET', '/api/workspace/status')[1]['is_git_repo'] is False
    (child / '.git').write_text('gitdir: ../.git\n')
    assert app.dispatch('GET', '/api/workspace/status')[0] == 400


def test_readonly_git_rejects_clean_filters_even_without_tool_grant(tmp_path):
    import os
    import subprocess
    root = tmp_path / 'repo'
    root.mkdir()
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    (root / 'note.txt').write_text('initial\n')
    (root / '.gitattributes').write_text('note.txt filter=tripwire\n')
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'filter.tripwire.clean', 'touch "$PWD/filter-ran"; cat'], check=True)
    (root / 'note.txt').write_text('changed\n')
    os.utime(root / 'note.txt', (2000000000, 2000000000))
    app = CosmicApp(tmp_path / 'state', workspace_roots=[root])
    app.dispatch('POST', '/api/workspace/select', {'root': str(root)})
    assert app.dispatch('GET', '/api/workspace/status')[0] in {400, 403}
    assert not (root / 'filter-ran').exists()
