"""Real Chromium owner-flow checks. Fake device handles test privacy, not hardware."""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import tempfile
import threading

from playwright.sync_api import expect, sync_playwright

from beastbox.cosmic_web import CosmicApp, CosmicHTTPServer, _CosmicHandler


def main() -> None:
    output = Path('build/cosmic-browser')
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / 'workspace'
        workspace.mkdir()
        (workspace / 'note.txt').write_text('original workspace content', encoding='utf-8')
        subprocess.run(['git', 'init', '-q', str(workspace)], check=True)
        app = CosmicApp(root / 'state', workspace_roots=[workspace])
        server = CosmicHTTPServer(('127.0.0.1', 0), _CosmicHandler)
        server.cosmic_app = app
        server.session_token = 'browser-regression-session'
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
                errors: list[str] = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('dialog', lambda dialog: dialog.accept())
                page.goto(f'http://127.0.0.1:{server.server_port}')
                expect(page.locator('#runtimePill')).to_have_text('SUBSTRATE VERIFIED')
                page.screenshot(path=str(output / 'orbit-desktop.png'), full_page=True)

                def nav(name: str) -> None:
                    page.locator('#nav').get_by_role('button', name=name, exact=True).click()

                def grant(name: str) -> None:
                    nav('AUTHORITY')
                    page.locator('.authority-row').filter(has_text=name.upper()+' · DENIED').get_by_role('button', name='GRANT', exact=True).click()
                    expect(page.locator('.authority-row').filter(has_text=name.upper()+' · GRANTED')).to_be_visible()

                nav('BRAIN')
                page.get_by_label('Message', exact=True).fill('ordinary durable test message')
                page.get_by_role('button', name='SEND', exact=True).click()
                expect(page.locator('.msg.assistant')).to_contain_text('reference / COSMOS reference')
                nav('FILES')
                page.locator('#fileInput').set_input_files({'name': 'context.txt', 'mimeType': 'text/plain', 'buffer': b'ephemeral-cosmic-test-content'})
                expect(page.locator('#fileOut')).to_contain_text('BROWSER_LOCAL_INSPECTION')
                page.get_by_role('button', name='ADD CONTEXT', exact=True).click()
                expect(page.locator('#contextOut')).to_contain_text('TURN_ATTACHMENT')
                nav('BRAIN')
                page.locator('#chatContexts input').check()
                page.get_by_label('Message', exact=True).fill('Read my attachment')
                page.get_by_role('button', name='SEND', exact=True).click()
                expect(page.locator('.msg.assistant').last).to_contain_text('ephemeral-cosmic-test-content')
                expect(page.locator('#chatContexts input')).to_have_count(0)
                assert b'ephemeral-cosmic-test-content' not in (root / 'state/runtime.sqlite3').read_bytes()
                nav('MEMORY VAULT')
                expect(page.locator('#memoryOut')).to_contain_text('ordinary durable test message')
                expect(page.locator('#memoryOut')).not_to_contain_text('ephemeral-cosmic-test-content')
                page.locator('#memoryMode').select_option('raw')
                expect(page.locator('#memoryRaw')).to_contain_text('sha256')
                expect(page.locator('#memoryOut')).to_be_hidden()
                page.locator('#memoryMode').select_option('visual')
                page.locator('#memoryQuery').fill('ordinary durable')
                # Ordinary input and the reference provider's echo are both durable.
                expect(page.locator('.memory-record')).to_have_count(2)
                expect(page.locator('.memory-record')).to_contain_text(['ordinary durable', 'ordinary durable'])
                expect(page.locator('#memoryOut')).not_to_contain_text('Read my attachment')
                page.locator('#memoryQuery').fill('')
                nav('SYNAPSE TRACE')
                expect(page.locator('#traceOut')).to_contain_text('checkpoint')

                nav('WORKSPACE')
                page.get_by_role('button', name='SELECT WORKSPACE', exact=True).click()
                expect(page.locator('#workspaceTree')).to_contain_text('note.txt')
                expect(page.locator('#writeWorkspace')).to_be_disabled()
                page.locator('#workspaceTree').get_by_role('button', name='note.txt', exact=True).click()
                expect(page.locator('#workspaceContent')).to_have_value('original workspace content')
                page.locator('#workspaceQuery').fill('original workspace')
                page.get_by_role('button', name='SEARCH', exact=True).click()
                expect(page.locator('#searchOut')).to_contain_text('note.txt:1')
                page.locator('#workspaceContent').fill('preview only')
                page.get_by_role('button', name='PREVIEW DIFF', exact=True).click()
                expect(page.locator('#diffOut')).to_contain_text('+preview only')
                assert (workspace / 'note.txt').read_text() == 'original workspace content'
                grant('filesystem')
                grant('repo_write')
                grant('tools')
                nav('WORKSPACE')
                page.locator('#workspaceContent').fill('owner-authorized change')
                page.get_by_role('button', name='WRITE FILE WITH BACKUP', exact=True).click()
                expect(page.locator('#notice')).to_contain_text('File written.')
                assert (workspace / 'note.txt').read_text() == 'owner-authorized change'
                page.get_by_role('button', name='RUN AUTHORIZED COMMAND', exact=True).click()
                expect(page.locator('#toolOut')).to_contain_text('returncode')
                page.screenshot(path=str(output / 'workspace-desktop.png'), full_page=True)

                # Same identity retains grants; a new identity must revoke them.
                nav('BRAIN BAY')
                page.get_by_role('button', name='CLOCK IN BRAIN', exact=True).click()
                expect(page.locator('#notice')).to_contain_text('Same brain saved')
                assert app.authority.allowed('repo_write')
                nav('BRAIN BAY')
                page.locator('#providerModel').fill('Browser Brain B')
                page.get_by_role('button', name='CLOCK IN BRAIN', exact=True).click()
                expect(page.locator('#handoff')).to_be_visible()
                assert not any(app.authority.snapshot().values())
                nav('WORKSPACE')
                expect(page.locator('#writeWorkspace')).to_be_disabled()

                nav('SETTINGS / STORAGE')
                page.locator('#exportDestination').fill(str(root / 'bundle'))
                page.get_by_role('button', name='EXPORT SNAPSHOT', exact=True).click()
                expect(page.locator('#snapshotHash')).to_have_value(__import__('re').compile('[a-f0-9]{64}'))
                page.get_by_role('button', name='VERIFY SNAPSHOT', exact=True).click()
                expect(page.locator('#notice')).to_contain_text('verification passed')
                page.locator('#importDestination').fill(str(root / 'restored'))
                page.get_by_role('button', name='IMPORT SNAPSHOT', exact=True).click()
                expect(page.locator('#notice')).to_contain_text('Snapshot restored')
                assert (root / 'restored/runtime.sqlite3').is_file()
                page.screenshot(path=str(output / 'storage-desktop.png'), full_page=True)

                # Exercise handle revocation with synthetic browser streams only.
                page.evaluate("""() => {
                    window.testTracks = [];
                    navigator.mediaDevices.getUserMedia = async () => {
                        const canvas = document.createElement('canvas');
                        const stream = canvas.captureStream();
                        window.testTracks.push(...stream.getTracks());
                        return stream;
                    };
                }""")
                nav('VISION')
                page.get_by_role('button', name='ENABLE CAMERA', exact=True).click()
                expect(page.locator('#cameraStatus')).to_have_text('CAMERA LIVE')
                nav('BRAIN BAY')
                page.locator('#providerModel').fill('Browser Brain C')
                page.get_by_role('button', name='CLOCK IN BRAIN', exact=True).click()
                expect(page.locator('#devicePill')).to_have_text('DEVICES OFF')
                assert page.evaluate("window.testTracks.every(track => track.readyState === 'ended')")

                # Guided reference demonstration: no model/server fixture responses.
                nav('ORBIT')
                page.locator('#demoStart').click()
                page.locator('#sendChat').click()
                expect(page.locator('#demoTitle')).to_have_text('See what was stored.')
                page.locator('#demoNext').click()
                expect(page.locator('#demoTitle')).to_have_text('Clock in another reference brain.')
                page.locator('#demoNext').click()
                page.locator('#saveProvider').click()
                expect(page.locator('#demoTitle')).to_have_text('Ask the new brain about your story.')
                page.locator('#demoNext').click()
                page.locator('#sendChat').click()
                expect(page.locator('#demoTitle')).to_have_text('Inspect the actual delivery.')
                page.locator('#demoNext').click()
                expect(page.locator('#demoTitle')).to_have_text('Export your continuity.')
                page.locator('#demoNext').click()
                page.locator('#exportDestination').fill(str(root / 'guided-capsule'))
                page.locator('#exportSnapshot').click()
                expect(page.locator('#demoProgress')).to_have_text('REFERENCE DEMO / COMPLETED')
                assert not any(app.authority.snapshot().values())
                assert (root / 'guided-capsule/manifest.json').is_file()
                page.locator('#demoClose').click()

                # Genuine captures from the executed UI and retained reference data.
                page.reload()
                expect(page.locator('#runtimePill')).to_have_text('SUBSTRATE VERIFIED')
                for name, image_name, ready in [
                    ('ORBIT', 'orbit-desktop.png', '#mapCore'),
                    ('BRAIN BAY', 'brain-bay-desktop.png', '#bayCurrent'),
                    ('MEMORY VAULT', 'memory-vault-desktop.png', '.memory-record'),
                    ('SYNAPSE TRACE', 'synapse-trace-desktop.png', '.trace-node'),
                    ('WORKSPACE', 'workspace-desktop.png', '#workspaceBranch'),
                    ('AUTHORITY', 'authority-desktop.png', '.authority-row'),
                    ('SETTINGS / STORAGE', 'storage-desktop.png', '#storageFacts dd'),
                    ('FILES', 'files-desktop.png', '#scopeHelp'),
                ]:
                    nav(name)
                    expect(page.locator(ready).first).to_be_visible()
                    page.screenshot(path=str(output / image_name), full_page=True)

                for name in ['ORBIT', 'BRAIN', 'BRAIN BAY', 'VISION', 'LISTEN', 'VOICE', 'REALITY', 'MEMORY VAULT', 'SYNAPSE TRACE', 'FILES', 'WORKSPACE', 'Q-BAY', 'CONNECTIONS', 'AUTHORITY', 'SETTINGS / STORAGE']:
                    nav(name)
                page.set_viewport_size({'width': 390, 'height': 844})
                nav('ORBIT')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(output / 'orbit-mobile.png'), full_page=True)
                nav('WORKSPACE')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(output / 'workspace-mobile.png'), full_page=True)
                for name in ['BRAIN BAY', 'MEMORY VAULT', 'SYNAPSE TRACE', 'FILES', 'AUTHORITY', 'SETTINGS / STORAGE']:
                    nav(name)
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), name
                assert not errors, errors
                browser.close()
            (output / 'result.json').write_text(json.dumps({'passed': True, 'flows': ['chat', 'temporary context', 'memory', 'trace', 'workspace confinement and writes', 'same/different brain authority', 'portable export/verify/import', 'synthetic camera revocation', 'all navigation', '390px layout'], 'physical_devices_validated': False}, indent=2)+'\n')
            source_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
            provenance = {
                'source_commit': source_sha, 'workflow_run': os.environ.get('GITHUB_RUN_ID'),
                'captured_at': datetime.now(timezone.utc).isoformat(),
                'ui_sha256': hashlib.sha256(Path('beastbox/cosmic_ui.py').read_bytes()).hexdigest(),
                'capture': 'Real Chromium, real CosmicApp, deterministic reference provider, temporary workspace',
                'physical_devices_validated': False,
                'images': {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in sorted(output.glob('*.png'))},
            }
            (output / 'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    main()
