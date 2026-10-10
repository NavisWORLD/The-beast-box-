"""Seal a new public media/recording revision in the existing off-chain ledger."""
import hashlib
import json
from pathlib import Path
from beastbox.persistent_substrate.ledger import StateEventLedger
from zeref_fresh_heart_live import OUT, stamp

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'apps/beastbox-cloud/public/spark/zeref-live-20261010'


def refresh(reason):
    excluded = {'quantum-ledger.jsonl', 'ledger-manifest.json'}
    files = {str(p.relative_to(PUBLIC)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(PUBLIC.rglob('*')) if p.is_file() and p.name not in excluded}
    ledger = StateEventLedger(OUT / 'quantum-ledger.jsonl')
    ledger.append('PUBLIC_ASSET_REVISION_SEALED', {'reason': reason, 'file_sha256': files}, stamp())
    receipt = ledger.verify()
    metadata = json.loads((PUBLIC / 'nft-metadata.json').read_text())
    (PUBLIC / 'quantum-ledger.jsonl').write_bytes((OUT / 'quantum-ledger.jsonl').read_bytes())
    manifest = {'schema': 'beastbox-public-ledger-manifest-v1', 'record_count': receipt.record_count,
                'tip_sha256': receipt.tip_sha256, 'ledger_file_sha256': receipt.sha256,
                'birth_tip_sha256': metadata['properties']['provenance']['birth_ledger_tip_sha256'],
                'file_sha256': files, 'onchain_mint': False, 'updated_utc': stamp()}
    (PUBLIC / 'ledger-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'events': receipt.record_count, 'tip_sha256': receipt.tip_sha256, 'asset_files': len(files)}))


if __name__ == '__main__':
    refresh('Initial measured Zeref public card, source replay and once-only simulator marker')
