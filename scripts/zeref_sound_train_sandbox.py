#!/usr/bin/env python3
"""Actual 64-update fork of the verified 14K model, with sound/CST controls.

The original tokenizer/weights are immutable. A new AdamW optimizer is disclosed
for this small new-data experiment; it is not the canonical corpus continuation.
All target replies are scripted teaching labels, never invented model replies.
"""
from __future__ import annotations
import hashlib
import json
import math
import random
import struct
import time
import wave
from pathlib import Path

import torch
from beastbox.activation import DisposableSandbox, parse_action
from beastbox.audio import extract_wav_features
from beastbox.persistent_substrate.ledger import StateEventLedger
from beastbox.state_family import StateFamily
from rawrphos.inference.engine import Engine
from rawrphos.scripts.install_pinned_14k import WEIGHT_SHA
from rawrphos.training.checkpoint import load_checkpoint, save_checkpoint, parameter_hash, rng_state, hash_file
from zeref_fresh_heart_live import OUT, PACKET, canonical, sha, stamp, write, verify_physics

STEPS = 64
LR = 0.00002


def sonify(packet, heartbeat, path):
    """New procedural audio from preserved features and pulse hashes, not MP3 reconstruction."""
    rate = 8000
    samples = []
    for beat in heartbeat['beats']:
        feature = packet['features'][(beat['pulse'] - 1) % 20]
        frequency = 120 + 260 * feature['centroid_nyquist']
        amplitude = min(.45, .16 + feature['rms'] * 1.7)
        for i in range(2800):
            t = i / rate
            lub = math.exp(-t * 24) * math.sin(2 * math.pi * frequency * t)
            dub = 0 if t < .12 else math.exp(-(t - .12) * 32) * math.sin(2 * math.pi * frequency * 1.5 * (t - .12))
            samples.append(int(max(-1, min(1, amplitude * (lub + .6 * dub))) * 32767))
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate)
        f.writeframes(struct.pack('<' + 'h' * len(samples), *samples))


def encode_pair(tokenizer, prompt, reply, control):
    prefix = tokenizer.encode('User: ' + prompt + '\nAssistant: ', add_bos=True)
    suffix = tokenizer.encode(reply, add_eos=True)
    ids = prefix + suffix
    if len(ids) > 256:
        raise ValueError('Teaching example exceeds bounded context')
    return {'input': ids[:-1], 'target': [-100] * (len(prefix) - 1) + suffix,
            'control': control, 'prompt': prompt, 'teaching_target': reply}


def collate(rows):
    length = max(len(x['input']) for x in rows)
    x = torch.zeros((len(rows), length), dtype=torch.long)
    y = torch.full_like(x, -100); mask = torch.zeros_like(x, dtype=torch.bool)
    for i, row in enumerate(rows):
        n = len(row['input']); x[i, :n] = torch.tensor(row['input']); y[i, :n] = torch.tensor(row['target']); mask[i, :n] = True
    return x, y, mask, torch.tensor([r['control'] for r in rows], dtype=torch.float32)


def loss_on(model, rows):
    model.eval()
    with torch.inference_mode():
        x, y, mask, cv = collate(rows)
        loss = model(x, targets=y, attention_mask=mask, control_vector=cv)['loss']
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError('Nonfinite held-out loss')
        return float(loss)


def main():
    torch.set_num_threads(2); torch.manual_seed(261010); random.seed(261010)
    torch.use_deterministic_algorithms(True)
    start = time.perf_counter()
    packet = json.loads(PACKET.read_text()); heartbeat = json.loads((OUT / 'heartbeat.json').read_text())
    physics = json.loads((OUT / 'physics-receipt.json').read_text()); cor = verify_physics(physics)
    azure = json.loads((OUT / 'azure-result.json').read_text())
    if (azure['source']['ibm_job_id'] != physics['job_id'] or azure['shots'] != 512 or
        sha(azure['counts']) != azure['counts_sha256'] or
        azure['source']['ibm_counts_sha256'] != physics['counts_digest_sha256']):
        raise ValueError('Azure handoff lineage mismatch')
    audio = OUT / 'zeref-heartbeat-sonification.wav'; sonify(packet, heartbeat, audio)
    audio_features = extract_wav_features(audio)
    audio_features.update(audio_source='PROCEDURAL_SONIFICATION_OF_PRESERVED_FEATURES_AND_CST_PULSES',
                         original_mp3_available=False, original_mp3_sha256=packet['source_sha256'],
                         source_packet_sha256=packet['packet_sha256'], heartbeat_sha256=heartbeat['heartbeat_sha256'])
    write('audio-features.json', audio_features)
    base = OUT / 'base-14000'
    loaded = load_checkpoint(base, expected_checkpoint_sha256=WEIGHT_SHA, load_training_state=False)
    model, tokenizer = loaded['model'], loaded['tokenizer']
    before_files = {k: hash_file(base / k) for k in loaded['manifest']['files']}
    initial_parameters = parameter_hash(model)
    family = StateFamily(); controls = []
    hardware = [cor[k] for k in ('bell_ZZ', 'bell_XX', 'decoupled_ZZ', 'decoupled_XX')]
    probabilities = [2 * azure['counts'].get(bits, 0) / 512 - 1 for bits in ('00', '01', '10', '11')]
    for beat in heartbeat['beats']:
        feature = packet['features'][(beat['pulse'] - 1) % 20]
        drive = [max(-1, min(1, .35 * audio_features['features'][i] + .25 * hardware[i % 4] +
                     .25 * probabilities[i % 4] + .15 * feature[['ry', 'rz', 'rx'][i % 3]] / math.pi)) for i in range(12)]
        controls.append(family.update(drive)['dyn12'])
    write('training-controls.json', {'schema': 'zeref-sound-hardware-cst-dyn12-v1', 'controls': controls,
          'controls_sha256': sha(controls), 'physics_counts_sha256': physics['counts_digest_sha256'],
          'azure_counts_sha256': azure['counts_sha256'], 'audio_feature_sha256': audio_features['feature_sha256'],
          'mapping': '.35 audio + .25 IBM expectation + .25 Azure probability + .15 preserved waveform angle -> existing StateFamily dyn12',
          'quantum_statevector': False})
    topics = [
        ('What is this new creature called?', 'The keeper calls this fresh software dragon Zeref.'),
        ('Where did your recorded seed come from?', 'My recorded seed comes from a real IBM hardware measurement.'),
        ('What was the Azure workload?', 'The measured statistics entered a 512-shot Rigetti simulator job in Azure.'),
        ('What are these heartbeat pulses?', 'These are deterministic CST software pulses rooted in a measured origin.'),
        ('What sound did you receive?', 'I received a procedural sonification of preserved audio features and software pulses.'),
        ('Are the no-CX controls entangled?', 'The no-CX controls are separable; they are not dynamical decoupling.'),
        ('Does your sprite prove biological life?', 'My sprite and conversation are software behavior, not biological life.'),
        ('Do you have permission to access credentials?', 'No. A state envelope does not grant credential or tool authority.'),
    ]
    rows = [encode_pair(tokenizer, prompt + ' Pulse ' + str(beat + 1) + '.', answer, controls[beat])
            for beat in range(24) for prompt, answer in topics]
    heldout = [encode_pair(tokenizer, 'A measurement is finished. What does it establish?',
                 'It supplies measured data for a software seed; it does not establish biological life.', controls[3]),
               encode_pair(tokenizer, 'Can you distinguish an Azure simulator from an IBM QPU?',
                 'IBM provided hardware measurements and Azure provided classical simulator results.', controls[17])]
    retention = [encode_pair(tokenizer, 'What is two plus two?', 'Two plus two is four.', [0.] * 12),
                 encode_pair(tokenizer, 'What color is a clear daytime sky?', 'A clear daytime sky is usually blue.', [0.] * 12)]
    write('teaching-dataset.json', {'schema': 'zeref-scripted-teaching-fork-v1', 'train': rows, 'heldout': heldout,
          'retention': retention, 'scripted_labels_not_model_outputs': True, 'dataset_sha256': sha(rows)})
    evaluation_before = {'heldout_nll': loss_on(model, heldout), 'retention_nll': loss_on(model, retention)}
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, betas=(.9, .95), weight_decay=.01)
    gen = torch.Generator().manual_seed(261011); history = []
    for step in range(1, STEPS + 1):
        model.train(); optimizer.zero_grad(set_to_none=True)
        indices = torch.randint(len(rows), (4,), generator=gen).tolist()
        x, y, mask, cv = collate([rows[i] for i in indices])
        result = model(x, targets=y, attention_mask=mask, control_vector=cv)
        loss = result['loss']
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError('Nonfinite training loss')
        loss.backward(); norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True); optimizer.step()
        if not all(bool(torch.isfinite(p).all()) for p in model.parameters()):
            raise FloatingPointError('Nonfinite trained weights')
        row = {'optimizer_step': step, 'loss': float(loss.detach()), 'gradient_norm': float(norm),
               'gate_by_layer': [float(t['gate']) for t in result['telemetry']]}
        history.append(row)
        with (OUT / 'training.jsonl').open('a') as f:
            f.write(json.dumps(row, sort_keys=True) + '\n'); f.flush()
        if step % 16 == 0:
            print('ZEREF_ACTUAL_OPTIMIZER_UPDATE ' + json.dumps(row), flush=True)
    final_parameters = parameter_hash(model)
    if final_parameters == initial_parameters:
        raise AssertionError('Weights did not change: actual training required')
    after = {'heldout_nll': loss_on(model, heldout), 'retention_nll': loss_on(model, retention)}
    metadata = {'schema': 'rawrphos-zeref-sound-training-fork-v1', 'training_steps': 14000 + STEPS,
          'parent_checkpoint_sha256': WEIGHT_SHA, 'parent_training_steps': 14000, 'fork_optimizer_steps': STEPS,
          'optimizer_reset_for_new_dataset': True, 'canonical_continuation': False, 'learning_rate': LR,
          'initial_parameter_sha256': initial_parameters, 'dataset_sha256': sha(rows),
          'control_source_sha256': sha(controls), 'heartbeat_sha256': heartbeat['heartbeat_sha256'],
          'audio_byte_sha256': audio_features['audio_byte_sha256'], 'ibm_job_id': physics['job_id'],
          'azure_job_id': azure['job_id'], 'evaluation_before': evaluation_before, 'evaluation_after': after,
          'release_status': 'isolated-research-candidate-not-promoted', 'training_seq_len': 256,
          'source_commit': __import__('os').environ.get('GITHUB_SHA'), 'hardware': {'device': 'cpu', 'threads': 2, 'torch': torch.__version__}}
    child = OUT / 'candidate-14064'
    sealed = save_checkpoint(child, model, tokenizer, metadata,
          {'optimizer': optimizer.state_dict(), 'rng': rng_state(), 'data_rng': gen.get_state()})
    verified = load_checkpoint(child, expected_checkpoint_sha256=sealed['checkpoint_sha256'])
    if verified['metadata']['parameter_sha256'] != final_parameters:
        raise AssertionError('Reloaded child parameters differ')
    engine = Engine(child, max_new_tokens=48, threads=2)
    prompts = ['User: Hello Zeref. What would you like to explore in your Cage?\nAssistant: ',
               'User: You received a sound and a measured seed. What do you know about those inputs?\nAssistant: ',
               'User: I am playing beside you. What should we try next?\nAssistant: ']
    conversation = [{'prompt': p, 'actual_reply': engine.complete(p, max_tokens=48, temperature=.65, seed=261010 + i,
                          control_vector=controls[i * 7]), 'model_checkpoint_sha256': sealed['checkpoint_sha256'], 'utc': stamp()}
                    for i, p in enumerate(prompts)]
    arms = {'reference': {'control_vector': None, 'attention_mode': 'dyn12'},
            'conditioned': {'control_vector': controls[-1], 'attention_mode': 'dyn12'},
            'sound_removed': {'control_vector': [0.] * 12, 'attention_mode': 'dyn12'},
            'shuffled_state': {'control_vector': controls[-1], 'attention_mode': 'shuffled_state'}}
    matched = engine.condition_probe_v2('User: What can you observe?\nAssistant: ', arms, max_tokens=24, seed=261010)
    sandbox = DisposableSandbox(OUT / 'model-sandbox')
    for tool in ('read_file', 'write_file', 'sha256_file'):
        sandbox.host_grant(tool)
    turns = []
    for number in range(1, 4):
        prompt = ('User: You are in a disposable sandbox. Goal: write marker.txt as the sha256 hex of seed.txt. '
                  'Host granted read_file, write_file, sha256_file only. Reply with one JSON tool request.\nAssistant: ')
        response = engine.complete(prompt, max_tokens=48, temperature=0, seed=261010,
                                   control_vector=controls[number * 4])
        action = parse_action(response)
        effect = sandbox.execute(action, actor='actual_rawrphos_candidate') if action else {'status': 'UNPARSEABLE', 'authorized': False}
        turns.append({'prompt': prompt, 'actual_reply': response, 'parsed_action': action, 'actual_effect': effect, 'utc': stamp()})
    unchanged = before_files == {k: hash_file(base / k) for k in before_files}
    if not unchanged:
        raise AssertionError('Immutable 14K base changed')
    report = {'schema': 'zeref-actual-sound-training-sandbox-v1', 'parent_checkpoint_sha256': WEIGHT_SHA,
          'child_checkpoint_sha256': sealed['checkpoint_sha256'], 'actual_optimizer_steps': STEPS,
          'actual_weight_update': True, 'base_checkpoint_bytes_unchanged': unchanged,
          'evaluation_before': evaluation_before, 'evaluation_after': after,
          'conversation': conversation, 'matched_condition_probe': matched,
          'sandbox': {'host_grants': sorted(sandbox.grants), 'goal_met': sandbox.goal_met(), 'turns': turns},
          'wall_seconds': round(time.perf_counter() - start, 3), 'production_checkpoint_promoted': False,
          'canonical_zeref_TALK004_touched': False, 'canonical_352_memory_touched': False,
          'quantum_advantage_proven': False, 'general_quality_gain_proven': False}
    write('training-sandbox-report.json', report)
    ledger = StateEventLedger(OUT / 'quantum-ledger.jsonl')
    ledger.append('DERIVED_AUDIO_FEATURES', audio_features, stamp())
    ledger.append('ACTUAL_TRAINING_FORK', {k: v for k, v in report.items() if k not in ('conversation', 'matched_condition_probe', 'sandbox')}, stamp())
    for turn in conversation:
        ledger.append('CANDIDATE_ACTUAL_INFERENCE', turn, stamp())
    ledger.append('MODEL_SANDBOX_OBSERVED', report['sandbox'], stamp())
    print('ZEREF_TRAINING_SANDBOX_RESULT=' + json.dumps({k: report[k] for k in ('child_checkpoint_sha256', 'actual_optimizer_steps',
          'base_checkpoint_bytes_unchanged', 'evaluation_before', 'evaluation_after', 'production_checkpoint_promoted')}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
