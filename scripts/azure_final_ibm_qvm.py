#!/usr/bin/env python3
"""One 512-shot Rigetti QVM job driven by a verified completed IBM receipt.

The transfer is classical; this does not send a quantum state between clouds.
Reruns recover the existing exact-name job. No QPU, database or model call here.
"""
import hashlib
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path('_azure_final_ibm_qvm')
JOB_NAME = 'beastbox-final-ibm-db4m3bslf4us73c2ui9g-qvm-v1'
TARGET = 'rigetti.sim.qvm'
SHOTS = 512
SOURCE_JOB = 'db4m3bslf4us73c2ui9g'
SOURCE_DIGEST = 'cf0a4973c0dbc074fc11a6bc7ce8439ecd61248c1a5c96a63571725c61e8b25b'

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def program_from_receipt(receipt):
    if (receipt.get('schema') != 'navisworld-ibm-longer-onejob-physics-receipt-v1' or
        receipt.get('source_class') != 'RECORDED_IBM_HARDWARE' or
        receipt.get('job_status') != 'DONE' or receipt.get('job_id') != SOURCE_JOB or
        receipt.get('backend_name') != 'ibm_fez' or receipt.get('shot_count') != 16384 or
        receipt.get('counts_digest_sha256') != SOURCE_DIGEST or
        digest(receipt.get('measurements')) != SOURCE_DIGEST):
        raise ValueError('Unapproved or corrupted IBM source')
    correlations = {}
    for basis in ('bell_zz', 'bell_xx', 'decoupled_zz', 'decoupled_xx'):
        counts = receipt['measurements'][basis]
        if (set(counts) != {'00','01','10','11'} or
            any(type(v) is not int or v < 0 for v in counts.values()) or sum(counts.values()) != 4096):
            raise ValueError('Invalid IBM shot counts')
        name = basis[:-2] + basis[-2:].upper()
        parity = (counts['00'] + counts['11'] - counts['01'] - counts['10']) / 4096
        if receipt.get('expectations', {}).get(name) != parity:
            raise ValueError('IBM parity mismatch')
        correlations[name] = parity
    # Explicit classical heuristic: measured entangled/control gaps set rotations.
    angles = [math.acos(max(-1, min(1, correlations['bell_ZZ']-correlations['decoupled_ZZ']))),
              math.acos(max(-1, min(1, correlations['bell_XX']-correlations['decoupled_XX'])))]
    program = ('DECLARE ro BIT[2]\nH 0\nCNOT 0 1\n'
               f'RX({angles[0]:.17g}) 0\nRY({angles[1]:.17g}) 1\n'
               'MEASURE 0 ro[0]\nMEASURE 1 ro[1]\n')
    source = {'ibm_job_id': SOURCE_JOB, 'ibm_counts_sha256': SOURCE_DIGEST,
              'classical_measurement_transfer': True, **correlations,
              'rotation_angles_rad': angles, 'quil_sha256': hashlib.sha256(program.encode()).hexdigest()}
    return program, source

def parse_counts(result, shots=SHOTS):
    values = result.get('ro') if isinstance(result, dict) else None
    counts = {key: 0 for key in ('00','01','10','11')}
    if isinstance(values, list):
        for row in values:
            if not isinstance(row, (list,tuple)) or len(row) != 2 or any(type(b) is not int or b not in (0,1) for b in row):
                raise ValueError('Invalid QVM measurement row')
            counts[''.join(map(str,row))] += 1
    elif isinstance(values, dict):
        for key, value in values.items():
            if key not in counts or type(value) is not int or value < 0:
                raise ValueError('Invalid QVM count')
            counts[key] = value
    else:
        raise ValueError('Unrecognized QVM result')
    if sum(counts.values()) != shots:
        raise ValueError('QVM shot count mismatch')
    return counts

def record(name, value):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT/name).write_text(json.dumps(value, sort_keys=True, indent=2)+'\n')

def main():
    secret = os.environ.get('AZURE_QUANTUM_CONNECTION_STRING', '').strip()
    if not secret or os.environ.get('BEAST_AZURE_QVM_ONE_JOB') != 'YES_ONE_FREE_SIMULATOR':
        raise RuntimeError('Missing authorized execution configuration')
    receipt = json.loads((ROOT/'apps/beastbox-cloud/experiment-input/ibm-final-live-20261009-receipt.json').read_text())
    program, source = program_from_receipt(receipt)
    from qdk.azure import Workspace
    workspace = Workspace.from_connection_string(secret)
    target = workspace.get_targets(TARGET)
    if getattr(target, 'name', None) != TARGET:
        raise RuntimeError('Simulator target changed')
    found = [job for job in workspace.list_jobs(name_match=JOB_NAME) if job.details.name == JOB_NAME]
    if len(found) > 1:
        raise RuntimeError('Ambiguous prior job; no new submission')
    record('input.json', {'job_name':JOB_NAME, 'target':TARGET, 'shots':SHOTS, 'source':source, 'quil':program})
    submitted = 0
    if found:
        job = found[0]
    else:
        job = target.submit(program, JOB_NAME, shots=SHOTS)
        submitted = 1
    record('submission.json', {'job_id':str(job.id), 'target':TARGET, 'new_jobs_submitted':submitted})
    print('AZURE_FINAL_QVM_SUBMITTED_OR_REUSED='+str(job.id), flush=True)
    raw = job.get_results()
    record('raw-result.json', {'job_id':str(job.id), 'provider_result':raw})
    counts = parse_counts(raw)
    output = {'schema':'beastbox-final-ibm-azure-qvm-result-v1',
              'source_class':'LIVE_AZURE_CLOUD_SIMULATOR_NOT_QPU',
              'job_id':str(job.id), 'job_name':JOB_NAME, 'target':TARGET,
              'shots':SHOTS, 'counts':counts, 'counts_sha256':digest(counts),
              'source':source, 'new_jobs_submitted':submitted, 'physical_quantum_shots':0,
              'cosmos_db_writes':0, 'model_inference_calls':0}
    record('result.json', output)
    print('SANITIZED_FINAL_AZURE_RECEIPT='+canonical(output), flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        record('failure.json', {'type':type(error).__name__, 'credential_recorded':False})
        print('AZURE_FINAL_QVM_FAILED='+type(error).__name__, flush=True)
        raise SystemExit(1)
