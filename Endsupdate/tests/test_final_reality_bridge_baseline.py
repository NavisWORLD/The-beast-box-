import json
from pathlib import Path

import pytest

from scripts.final_reality_bridge_baseline import (
    EXPECTED_LEDGER_COUNT,
    EXPECTED_LEDGER_SHA256,
    EXPECTED_LEDGER_TIP_SHA256,
    verify_canonical_memory,
)


def test_canonical_memory_matches_frozen_352_chain():
    result = verify_canonical_memory(Path('.'))
    assert result['record_count'] == EXPECTED_LEDGER_COUNT == 352
    assert result['sha256'] == EXPECTED_LEDGER_SHA256
    assert result['ledger_tip_sha256'] == EXPECTED_LEDGER_TIP_SHA256
    assert result['chain_verified'] is True


def test_canonical_memory_verifier_fails_closed_on_missing_snapshot(tmp_path):
    root = tmp_path
    memory = root / 'experiments/zeref-dad-son-001/memory'
    memory.mkdir(parents=True)
    manifest = {
        'record_count': 352,
        'combined_ledger_sha256': EXPECTED_LEDGER_SHA256,
        'last_record_sha256': EXPECTED_LEDGER_TIP_SHA256,
        'snapshot_chain': [
            {
                'path': 'experiments/zeref-dad-son-001/memory/ledger-snapshots/missing.jsonl',
                'sha256': '0' * 64,
                'record_count': 352,
                'first_memory_id': 1,
                'last_memory_id': 352,
            }
        ],
    }
    (memory / 'ledger-manifest.json').write_text(json.dumps(manifest))
    with pytest.raises((AssertionError, FileNotFoundError)):
        verify_canonical_memory(root)
