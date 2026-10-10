#!/usr/bin/env python3
"""One quota-guarded IBM waveform/Bell job, one Azure QVM handoff, fresh CST pulses.

This experiment uses Zeref's preserved audio *feature packet*. It does not claim
to possess or reconstruct the original MP3. Tags are stable across retries.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

from beastbox.heartbeat_seed import REQUIRED_TAG, build_gate_program, build_hardware_origin_seed
from beastbox.persistent_substrate.ledger import StateEventLedger
from beastbox.soul.token import SoulToken
from ibm_eternal_dragon_longer_probe import circuits, same_parity
from ibm_open_plan_preflight import quota_receipt
from run_zeref_heartbeat_ibm_seed import build_circuit
from build_zeref_ibm_teacher_heartbeat import build_teacher_heartbeat
from azure_final_ibm_qvm import parse_counts

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '_zeref_live_20261010'
PACKET = ROOT / 'experiments/zeref-origin-heart-001/waveform/zeref-heartbeat-waveform-packet.json'
TAG = 'navisworld-zeref-heart-sound-20261010-onejob-v1'
QPU_CAP = 60
SHOTS = 4096
NAMES = ['bell_zz', 'bell_xx', 'decoupled_zz', 'decoupled_xx']


def stamp():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


def check_counts(counts, bits, shots=SHOTS):
    if (not isinstance(counts, dict) or not counts or
        any(not isinstance(k, str) or len(k) != bits or set(k) - {'0', '1'} or
            type(v) is not int or v < 0 for k, v in counts.items()) or sum(counts.values()) != shots):
        raise ValueError('Invalid physical counts or requested shot total')
    return dict(sorted(counts.items()))


def verify_physics(receipt):
    if (receipt.get('schema') != 'navisworld-ibm-longer-onejob-physics-receipt-v1' or
        receipt.get('source_class') != 'RECORDED_IBM_HARDWARE' or
        receipt.get('job_status') != 'DONE' or receipt.get('shot_count') != 16384 or
        not str(receipt.get('backend_name', '')).startswith('ibm_') or
        len(str(receipt.get('job_id', ''))) != 20):
        raise ValueError('Completed real IBM physics source required')
    counts = receipt.get('measurements', {})
    if set(counts) != set(NAMES) or sha(counts) != receipt.get('counts_digest_sha256'):
        raise ValueError('Physical count map integrity mismatch')
    for name in NAMES:
        check_counts(counts[name], 2)
        key = name[:-2] + name[-2:].upper()
        if receipt['expectations'].get(key) != same_parity(counts[name]):
            raise ValueError('Expectation disagrees with physical counts')
    domain = {'domain': 'NAVISWORLD::IBM::ETERNAL_DRAGON_120S::QBEAST::V1',
              'job_id': receipt['job_id'], 'backend': receipt['backend_name'], 'counts': counts}
    if sha(domain) != receipt.get('beast_genesis_digest_sha256'):
        raise ValueError('Genesis source hash mismatch')
    return receipt['expectations']


def main():
    if (not os.environ.get('IBM_QUANTUM_TOKEN') or
        os.environ.get('BEAST_REAL_QPU_ONE_JOB') != 'YES_ONE_REAL_JOB' or
        not os.environ.get('AZURE_QUANTUM_CONNECTION_STRING') or
        os.environ.get('BEAST_AZURE_QVM_ONE_JOB') != 'YES_ONE_FREE_SIMULATOR'):
        raise RuntimeError('Authorized provider configuration missing')
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    service = QiskitRuntimeService(channel='ibm_quantum_platform', token=os.environ['IBM_QUANTUM_TOKEN'], plans_preference=['open'])
    instance = service.active_instance()
    if not instance:
        raise RuntimeError('IBM Open Plan instance unavailable')
    quota = quota_receipt(service.usage(), str(instance))
    write('quota-before.json', quota)
    prior = service.jobs(limit=100, program_id='sampler', job_tags=[TAG])
    if len(prior) > 1:
        raise RuntimeError('Ambiguous tagged job')
    packet = json.loads(PACKET.read_text())
    program = build_gate_program(packet)
    tags = [TAG, REQUIRED_TAG, 'zeref-origin-heart-001', 'wave-' + packet['packet_sha256'][:12], 'beast-reality-probe']
    write('waveform-gate-program.json', program)
    new_job = not prior
    if new_job:
        if (not quota['headroom_for_one_300_second_job'] or
            quota['already_consumed_seconds'] + QPU_CAP > 300):
            raise RuntimeError('300-second aggregate authorization would be exceeded')
        backend = service.least_busy(simulator=False, operational=True, min_num_qubits=5)
        if backend.configuration().simulator:
            raise RuntimeError('Simulator refused for physical job')
        manager = generate_preset_pass_manager(backend=backend, optimization_level=1, seed_transpiler=261010)
        compiled = [manager.run(qc) for _, qc in circuits()] + [manager.run(build_circuit(program))]
        if len(compiled) != 5 or any(q.depth() > 1000 for q in compiled):
            raise RuntimeError('Compiled circuit bound exceeded')
        write('proposed-circuits.json', {'names': NAMES + ['zeref_waveform_5q'], 'shots_per_pub': SHOTS,
              'physical_shots_total': SHOTS * 5, 'compiled_depths': [int(q.depth()) for q in compiled],
              'backend': str(backend.name), 'max_qpu_seconds': QPU_CAP,
              'compiled_display_sha256': [hashlib.sha256(str(q).encode()).hexdigest() for q in compiled]})
        sampler = SamplerV2(mode=backend)
        sampler.options.max_execution_time = QPU_CAP
        sampler.options.environment.job_tags = tags
        job = sampler.run(compiled, shots=SHOTS)
    else:
        job = prior[0]
    write('submission.json', {'job_id': str(job.job_id()), 'tag': TAG, 'utc': stamp(),
          'new_jobs_submitted_this_attempt': int(new_job), 'max_qpu_seconds': QPU_CAP,
          'aggregate_authorized_seconds': 300, 'shots_requested': 20480, 'credential_recorded': False})
    print('ZEREF_FRESH_PHYSICAL_JOB=' + str(job.job_id()), flush=True)
    result = job.result()
    verified = service.job(job.job_id())
    if str(verified.status()) != 'DONE' or not set(tags) <= set(verified.tags or []):
        raise RuntimeError('Completed hardware status or provider tags not verified')
    if len(result) != 5:
        raise RuntimeError('Physical PUB count mismatch')
    distributions = {name: check_counts({str(k).replace(' ', ''): int(v) for k, v in result[i].join_data().get_counts().items()}, 2)
                     for i, name in enumerate(NAMES)}
    waveform_counts = check_counts({str(k).replace(' ', ''): int(v) for k, v in result[4].join_data().get_counts().items()}, 5)
    backend_name = str(job.backend().name)
    expectations = {name[:-2] + name[-2:].upper(): same_parity(counts) for name, counts in distributions.items()}
    metrics = job.metrics() or {}
    receipt = {'schema': 'navisworld-ibm-longer-onejob-physics-receipt-v1', 'job_id': str(job.job_id()),
               'backend_name': backend_name, 'source_class': 'RECORDED_IBM_HARDWARE', 'job_status': 'DONE',
               'shot_count': 16384, 'measurements': distributions, 'expectations': expectations,
               'qpu_job_limit_seconds': QPU_CAP, 'counts_digest_sha256': sha(distributions),
               'beast_genesis_digest_sha256': sha({'domain': 'NAVISWORLD::IBM::ETERNAL_DRAGON_120S::QBEAST::V1',
                    'job_id': str(job.job_id()), 'backend': backend_name, 'counts': distributions}),
               'hardware_metrics': {'quantum_seconds': metrics.get('usage', {}).get('quantum_seconds'),
                                    'timestamps': metrics.get('timestamps', {})},
               'additional_waveform_pub_shots': 4096, 'physical_job_total_shots': 20480,
               'control_definition': 'No-CX separable control, not dynamical decoupling', 'recorded_utc': stamp()}
    verify_physics(receipt)
    write('physics-receipt.json', receipt)
    seed = build_hardware_origin_seed(packet=packet, backend=backend_name, job_id=str(job.job_id()), counts=waveform_counts, tags=list(verified.tags))
    # Fresh means unique to this experiment. Replay of this same tag is disclosed
    # separately and must never be confused with another hardware execution.
    seed.update(fresh_hardware_requested=True, reused_existing_job=False, current_attempt_recovered_same_experiment_job=not new_job)
    write('waveform-origin-seed.json', seed)
    ledger = StateEventLedger(OUT / 'quantum-ledger.jsonl')
    if ledger.verify().record_count:
        raise RuntimeError('Output ledger already exists; use a fresh observation directory')
    ledger.append('IBM_HARDWARE_COMPLETED', {'physics': receipt, 'waveform_origin_seed': seed}, stamp())
    heartbeat = build_teacher_heartbeat(ibm_seed=seed, starting_ledger_tip_sha256=ledger.verify().tip_sha256)
    write('heartbeat.json', heartbeat)
    for beat in heartbeat['beats']:
        ledger.append('CST_SOFTWARE_PULSE', beat, stamp())
    # Classical measured statistics parameterize an actual cloud simulator job.
    angles = [math.acos(max(-1, min(1, expectations['bell_ZZ'] - expectations['decoupled_ZZ']))),
              math.acos(max(-1, min(1, expectations['bell_XX'] - expectations['decoupled_XX'])))]
    quil = 'DECLARE ro BIT[2]\nH 0\nCNOT 0 1\n' + f'RX({angles[0]:.17g}) 0\nRY({angles[1]:.17g}) 1\nMEASURE 0 ro[0]\nMEASURE 1 ro[1]\n'
    target_name = 'rigetti.sim.qvm'
    job_name = 'beastbox-zeref-heart-' + receipt['job_id'] + '-' + receipt['counts_digest_sha256'][:12]
    source = {'ibm_job_id': receipt['job_id'], 'ibm_counts_sha256': receipt['counts_digest_sha256'],
              'waveform_origin_seed_sha256': seed['origin_seed_sha256'], 'classical_measurement_transfer': True,
              'rotation_angles_rad': angles, 'quil_sha256': hashlib.sha256(quil.encode()).hexdigest()}
    write('azure-input.json', {'quil': quil, 'target': target_name, 'shots': 512, 'job_name': job_name, 'source': source})
    from qdk.azure import Workspace
    workspace = Workspace.from_connection_string(os.environ['AZURE_QUANTUM_CONNECTION_STRING'])
    target = workspace.get_targets(target_name)
    if target.name != target_name:
        raise RuntimeError('Unexpected Azure target')
    matches = [x for x in workspace.list_jobs(name_match=job_name) if x.details.name == job_name]
    if len(matches) > 1:
        raise RuntimeError('Ambiguous Azure job')
    azure_job = matches[0] if matches else target.submit(quil, job_name, shots=512)
    write('azure-submission.json', {'job_id': str(azure_job.id), 'target': target_name, 'submitted_this_attempt': int(not matches)})
    azure_counts = parse_counts(azure_job.get_results(), 512)
    azure = {'schema': 'beastbox-zeref-heart-live-azure-qvm-v1', 'job_id': str(azure_job.id), 'target': target_name,
             'source_class': 'LIVE_AZURE_CLOUD_SIMULATOR_NOT_QPU', 'shots': 512, 'counts': azure_counts,
             'counts_sha256': sha(azure_counts), 'source': source, 'physical_quantum_shots': 0,
             'azure_cosmos_db_writes': 0, 'recorded_utc': stamp()}
    write('azure-result.json', azure)
    ledger.append('AZURE_QVM_COMPLETED', azure, stamp())
    probabilities = [azure_counts.get(bits, 0) / 512 for bits in ('00', '01', '10', '11')]
    token = SoulToken.from_qbt({'normalized_vector': probabilities,
             'source_receipt_sha256': sha(azure), 'hardware_counts_sha256': receipt['counts_digest_sha256'],
             'heartbeat_sha256': heartbeat['heartbeat_sha256']}, source_type='IBM_MEASURED_TO_AZURE_QVM_CLASSICAL', consumers=('beast-core', 'rawrphos-sandbox'))
    write('injection-envelope.json', token.to_dict())
    ledger.append('CLASSICAL_INJECTION_ENVELOPE', token.to_dict(), stamp())
    write('quota-after.json', quota_receipt(service.usage(), str(instance)))
    print('ZEREF_PHYSICAL_AZURE_RESULT=' + json.dumps({'ibm_job': receipt['job_id'], 'backend': backend_name,
          'physical_shots': 20480, 'counts_sha256': receipt['counts_digest_sha256'], 'azure_job': str(azure_job.id),
          'azure_shots': 512, 'heartbeat_pulses': 24, 'ledger_tip': ledger.verify().tip_sha256}, sort_keys=True), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        write('failure.json', {'error_type': type(exc).__name__, 'credential_recorded': False, 'utc': stamp()})
        raise
