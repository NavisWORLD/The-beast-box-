#!/usr/bin/env python3
"""Render measured-source Zeref media and unminted ERC-721 metadata.

The sprite pixels/idle poses come from the existing genome renderer. The GIF is
explicitly a seeded sprite animation; native gameplay has a separate recording.
"""
import base64
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from beastbox.persistent_substrate.ledger import StateEventLedger
from zeref_fresh_heart_live import OUT, stamp

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'apps/beastbox-cloud'
SOURCE = APP / 'experiment-evidence/zeref-heart-sound-20261010'
DEST = APP / 'public/spark/zeref-live-20261010'
ORIGIN = 'https://www.beastboxcosmos.xyz/spark/zeref-live-20261010'


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n')


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size, bold=False):
    name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    for folder in ('/usr/share/fonts/truetype/dejavu', '/usr/share/fonts/dejavu'):
        path = Path(folder) / name
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def main():
    result = json.loads((SOURCE / 'receipt.json').read_text())
    physics, azure, training = result['physics'], result['azure'], result['training']
    if physics['job_status'] != 'DONE' or not training['actual_weight_update']:
        raise ValueError('Actual measured/trained run required')
    DEST.mkdir(parents=True, exist_ok=True)
    frames = json.loads((SOURCE / 'sprite-frames.json').read_text())
    sprites = {x['eyes']: Image.frombytes('RGBA', (64, 64), base64.b64decode(x['rgba_base64'])) for x in frames}
    sprites['open'].save(DEST / 'Zeref_sprite.png')
    animation = []
    for i, item in enumerate(result['animation']['poses']):
        canvas = Image.new('RGBA', (512, 512), '#0b1021'); draw = ImageDraw.Draw(canvas)
        draw.ellipse((72, 70, 440, 438), outline='#294365', width=2)
        draw.ellipse((104, 102, 408, 406), outline='#1e2c47', width=1)
        for n in range(28):
            raw = hashlib.sha256((result['seed'] + ':star:' + str(n)).encode()).digest()
            x, y = 26 + raw[0] * 1.8, 28 + raw[1] * 1.65
            bright = '#789cce' if (i + n) % 16 < 8 else '#38516e'
            draw.rectangle((x, y, x + 2, y + 2), fill=bright)
        pose = item['pose']; eyes = 'closed' if i in (22, 23) else 'open'
        sprite = sprites[eyes].resize((256, 256), Image.Resampling.NEAREST)
        canvas.alpha_composite(sprite, (round(112 + pose['x'] * 2 - 128), round(140 + pose['y'] * 3 - 128)))
        draw.text((28, 447), 'ZEREF', font=font(22, True), fill='#e1edff')
        draw.text((28, 478), 'Seeded sprite animation · ' + result['qbeast_id'], font=font(13), fill='#83a2c4')
        animation.append(canvas.convert('RGB'))
    animation[0].save(DEST / 'Zeref_sprite.gif', save_all=True, append_images=animation[1:], duration=83, loop=0, optimize=False)
    ledger = StateEventLedger(OUT / 'quantum-ledger.jsonl')
    ledger.append('FRESH_QBEAST_CREATED', {'qbeast_id': result['qbeast_id'], 'keeper_name': 'Zeref',
                  'genome_name': result['genome_name'], 'seed': result['seed'], 'genome_sha256': result['genome_sha256'],
                  'hardware_job_id': physics['job_id'], 'sound_behavior_trace_sha256': result['behavior_controls']['sound']['trace_sha256']}, stamp())
    birth_tip = ledger.verify().tip_sha256
    card = Image.new('RGB', (640, 800), '#0b1021'); draw = ImageDraw.Draw(card)
    draw.rounded_rectangle((16, 16, 624, 784), radius=24, fill='#111a2e', outline='#526f95', width=2)
    draw.text((42, 42), 'BEAST BOX  /  REALITY RUN 001', font=font(17), fill='#94bce9')
    draw.text((42, 75), 'ZEREF', font=font(53, True), fill='#eef5ff')
    draw.text((42, 142), result['genome_name'] + ' · ' + result['qbeast_id'], font=font(20), fill='#a6c7f0')
    hero = sprites['open'].resize((384, 384), Image.Resampling.NEAREST)
    draw.ellipse((116, 195, 524, 543), fill='#16223c', outline='#325272', width=2)
    card.paste(hero, (128, 172), hero)
    draw.rounded_rectangle((42, 561, 598, 595), radius=8, fill='#193d39')
    draw.text((55, 568), 'REAL IBM HARDWARE · 20,480 MEASURED SHOTS', font=font(15, True), fill='#a1ecd3')
    draw.text((42, 609), physics['backend_name'] + '  /  ' + physics['job_id'], font=font(17), fill='#d3e4ff')
    draw.text((42, 643), 'Azure QVM 512 shots · RAWRPHØS +64 updates', font=font(16), fill='#a8c1df')
    draw.text((42, 677), 'Birth ledger  ' + birth_tip[:24] + '…', font=font(15), fill='#829dbd')
    draw.text((42, 716), 'NFT METADATA READY · UNMINTED', font=font(17, True), fill='#ffd78a')
    draw.text((42, 751), 'Software creature · measured provenance · 2026-10-10 UTC', font=font(13), fill='#7d99bc')
    card.save(DEST / 'Zeref_NFT_card.png')
    metadata = {'name': 'Zeref — Reality Run 001', 'description':
        'A newly generated Beast Box dragon with keeper name Zeref. Its immutable QBEAST is rooted in recorded IBM hardware counts. '
        'Preserved Zeref waveform features controlled an additional measured five-qubit circuit. Actual Azure Rigetti QVM statistics, '
        '24 deterministic CST pulses, a 64-update isolated RAWRPHOS research fork, and observed classical behavior are retained in a verified off-chain hash ledger. '
        'This metadata has not been minted on a blockchain.',
        'image': ORIGIN + '/Zeref_NFT_card.png', 'animation_url': ORIGIN + '/Zeref_sprite.gif', 'external_url': ORIGIN + '/index.html',
        'attributes': [{'trait_type': 'Keeper name', 'value': 'Zeref'}, {'trait_type': 'Genome name', 'value': result['genome_name']},
          {'trait_type': 'QBEAST', 'value': result['qbeast_id']}, {'trait_type': 'IBM backend', 'value': physics['backend_name']},
          {'trait_type': 'Physical shots', 'value': 20480}, {'trait_type': 'Azure simulated shots', 'value': 512},
          {'trait_type': 'CST software pulses', 'value': 24}, {'trait_type': 'Actual fork optimizer updates', 'value': 64},
          {'trait_type': 'Mint status', 'value': 'UNMINTED'}],
        'properties': {'schema': 'beastbox-zeref-ledger-nft-metadata-v1', 'mint_status': 'UNMINTED', 'chain_id': None,
          'contract_address': None, 'onchain_token_id': None, 'transaction_hash': None,
          'provenance': {'ibm_job_id': physics['job_id'], 'ibm_counts_sha256': physics['counts_digest_sha256'],
            'waveform_origin_seed': json.loads((OUT / 'waveform-origin-seed.json').read_text())['origin_seed_sha256'],
            'azure_job_id': azure['job_id'], 'azure_counts_sha256': azure['counts_sha256'], 'qbeast_seed': result['seed'],
            'genome_sha256': result['genome_sha256'], 'research_checkpoint_sha256': training['child_checkpoint_sha256'],
            'birth_ledger_tip_sha256': birth_tip, 'ledger_url': ORIGIN + '/quantum-ledger.jsonl'},
          'animation_kind': 'seeded_genome_sprite_animation', 'ledger_kind': 'offchain_hash_chained_evidence',
          'biological_life_claimed': False, 'quantum_advantage_claimed': False}}
    write(DEST / 'nft-metadata.json', metadata)
    for name in ('Zeref.qbeast', 'qbeast.json', 'unsigned-session.json'):
        (DEST / name).write_bytes((SOURCE / name).read_bytes())
    (DEST / 'Zeref_heartbeat.wav').write_bytes((OUT / 'zeref-heartbeat-sonification.wav').read_bytes())
    summary = {'schema': 'beastbox-zeref-public-observed-run-v1', 'keeper_name': 'Zeref', 'genome_name': result['genome_name'],
        'qbeast_id': result['qbeast_id'], 'ibm': physics, 'azure': azure, 'heartbeat_sha256': result['heartbeat_sha256'],
        'training': {k: training[k] for k in ('parent_checkpoint_sha256', 'child_checkpoint_sha256', 'actual_optimizer_steps',
              'evaluation_before', 'evaluation_after', 'base_checkpoint_bytes_unchanged', 'conversation', 'sandbox', 'production_checkpoint_promoted')},
        'behavior': {k: {n: v[n] for n in ('actions', 'trace_sha256', 'save_reload_exact')} for k, v in result['behavior_controls'].items()},
        'audio': result['audio'], 'mint_status': 'UNMINTED', 'native_recording_status': 'PENDING_LIVE_RECORDING', 'birth_ledger_tip_sha256': birth_tip}
    write(DEST / 'run-summary.json', summary)
    files = {p.name: file_sha(p) for p in DEST.iterdir() if p.is_file()}
    ledger.append('MEDIA_AND_UNMINTED_METADATA_SEALED', {'file_sha256': files, 'mint_status': 'UNMINTED'}, stamp())
    (DEST / 'quantum-ledger.jsonl').write_bytes((OUT / 'quantum-ledger.jsonl').read_bytes())
    receipt = ledger.verify()
    write(DEST / 'ledger-manifest.json', {'schema': 'beastbox-public-ledger-manifest-v1', 'record_count': receipt.record_count,
        'tip_sha256': receipt.tip_sha256, 'ledger_file_sha256': receipt.sha256, 'birth_tip_sha256': birth_tip,
        'file_sha256': files, 'onchain_mint': False, 'updated_utc': stamp()})
    print(json.dumps({'card': str(DEST / 'Zeref_NFT_card.png'), 'gif_frames': len(animation),
          'ledger_events': receipt.record_count, 'ledger_tip': receipt.tip_sha256, 'mint_status': 'UNMINTED'}))


if __name__ == '__main__':
    main()
