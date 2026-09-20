"""Verify the downloadable i dare you public ledger, checkpoint and manifest.

Does not require Jev, PHOS, any credential, PyTorch or external dependency.
This verifies file integrity, NOT a successful model swap or training result.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def verify(root):
    prev = '0' * 64
    events = []
    for number, line in enumerate((root / 'events.jsonl').read_bytes().splitlines(), 1):
        event = json.loads(line)
        claimed = event.pop('event_hash')
        if event.get('seq') != number or event.get('previous_hash') != prev:
            raise ValueError(f'ledger order/previous hash mismatch: event {number}')
        if digest(canonical(event)) != claimed:
            raise ValueError(f'ledger event hash mismatch: event {number}')
        event['event_hash'] = claimed
        prev = claimed
        events.append(event)
    if not events:
        raise ValueError('ledger is empty')
    manifest = json.loads((root / 'reproduction_manifest.json').read_text())
    if manifest['event_count'] != len(events) or manifest['last_event_hash'] != prev:
        raise ValueError('manifest and ledger do not agree')
    frozen = digest((root / 'checkpoint_1.json').read_bytes())
    if manifest['checkpoint']['checkpoint_1_sha256'] != frozen:
        raise ValueError('checkpoint bytes changed')
    if manifest['checkpoint']['final_state_sha256'] != digest((root / 'substrate_state.json').read_bytes()):
        raise ValueError('final substrate bytes changed')
    return len(events), frozen, manifest['continuity']['cross_provider_continuity']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    count, checkpoint_sha, cross_provider = verify(args.run_directory)
    print(f'VERIFIED ledger_events={count} checkpoint_sha256={checkpoint_sha} cross_provider={cross_provider}')
