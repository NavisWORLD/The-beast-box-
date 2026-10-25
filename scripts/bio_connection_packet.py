#!/usr/bin/env python3
"""Real IBM Bio Connection - packet gate and seed mixer (runs inside GitHub Actions only).
verify : strictly re-validates the NUMBERS-ONLY packet the owner's phone produced, recomputes its sha256 (same canonical JSON as the
         browser/server), refuses anything with raw media, writes the feature packet that tags the real IBM run and seeds the Rigetti QVM job.
finish : mixes the measured packet hash with the real IBM outcome hash into a deterministic next seed (no clock, no random) and
         writes the public result states. Heartbeat MEASURED (quality gated on the phone); IBM RECORDED only if a real job result exists;
         Rigetti SIMULATED. Creative seed, not proof; not a medical device."""
import hashlib, json, os, re, sys
from pathlib import Path

SCHEMA = 'beastbox-real-ibm-bio-connection-v1'
SOURCE = 'browser_ppg_fingertip'
TOP = {'schema', 'source', 'heartbeat_label', 'honesty', 'pulse', 'light', 'audio', 'bio_vector_12',
       'raw_audio_published', 'raw_video_published', 'raw_frames_in_packet', 'packet_sha256'}
RANGES = {
    'pulse': {'bpm': (40, 200), 'hrv_rmssd_ms': (0, 300, 'opt'), 'sqi': (0.6, 1), 'beats': (15, 400, 'int'),
              'duration_s': (20, 120), 'fs_hz': (20, 60)},
    'light': {'red_mean': (0, 255), 'green_mean': (0, 255), 'blue_mean': (0, 255), 'red_ac_dc': (0, 1)},
    'audio': {'enabled': 'bool', 'rms_mean': (0, 1), 'zcr': (0, 1), 'centroid_norm': (0, 1)},
}


def _norm(v):
    """Make Python JSON text identical to JS JSON.stringify: integral floats print as ints."""
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return v
    if isinstance(v, float):
        return int(v) if v == int(v) else v
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, dict):
        return {k: _norm(x) for k, x in v.items()}
    return v


def canonical(v):
    return json.dumps(_norm(v), sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def sha(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float('inf')


def validate(p):
    errs = []
    if not isinstance(p, dict) or set(p) != TOP:
        return ['unexpected or missing top-level keys']
    if p['schema'] != SCHEMA: errs.append('schema')
    if p['source'] != SOURCE: errs.append('source')
    if p['heartbeat_label'] != 'MEASURED': errs.append('heartbeat_label')
    if not isinstance(p['honesty'], str) or len(p['honesty']) > 400: errs.append('honesty')
    for f in ('raw_audio_published', 'raw_video_published', 'raw_frames_in_packet'):
        if p[f] is not False: errs.append(f + ' must be false')
    if not re.fullmatch(r'[a-f0-9]{64}', str(p['packet_sha256'])): errs.append('packet_sha256')
    for grp, spec in RANGES.items():
        o = p[grp]
        if not isinstance(o, dict) or set(o) != set(spec):
            errs.append(grp + ' keys'); continue
        for k, r in spec.items():
            v = o[k]
            if r == 'bool':
                if not isinstance(v, bool): errs.append(f'{grp}.{k}')
            elif v is None and len(r) > 2 and r[2] == 'opt':
                pass
            elif not _num(v) or not (r[0] <= v <= r[1]) or (len(r) > 2 and r[2] == 'int' and v != int(v)):
                errs.append(f'{grp}.{k} out of range')
    vec = p['bio_vector_12']
    if not isinstance(vec, list) or len(vec) != 12 or not all(_num(x) and 0.05 <= x <= 0.95 for x in vec):
        errs.append('bio_vector_12')
    if len(json.dumps(p)) > 1800: errs.append('packet too large')
    return errs


def verify():
    raw = os.environ.get('BIO_PACKET_JSON', '')
    sha12 = os.environ.get('BIO_PACKET_SHA12', '')
    if not re.fullmatch(r'[a-f0-9]{12}', sha12) or len(raw) > 4096:
        sys.exit('rejected: bad input')
    p = json.loads(raw)
    errs = validate(p)
    if errs:
        sys.exit('rejected: ' + '; '.join(errs[:4]))
    body = {k: v for k, v in p.items() if k != 'packet_sha256'}
    if sha(canonical(body)) != p['packet_sha256'] or p['packet_sha256'][:12] != sha12:
        sys.exit('rejected: hash mismatch')
    out = Path('_bio_connection'); out.mkdir(exist_ok=True)
    (out / 'features.json').write_text(json.dumps(p, sort_keys=True, indent=2) + '\n')
    tag = 'navisworld-real-ibm-bio-' + sha12
    gh = os.environ.get('GITHUB_OUTPUT')
    if gh:
        with open(gh, 'a') as f:
            f.write(f'tag={tag}\nsha12={sha12}\n')
    print('BIO_PACKET_OK=' + sha12 + ' bpm=' + str(p['pulse']['bpm']) + ' sqi=' + str(p['pulse']['sqi']) + ' (numbers only)')


def states():
    ibm_dir, qvm_dir = Path('_bio_connection_ibm'), Path('_bio_connection_qvm')
    if (ibm_dir / 'chsh_game_result.json').exists(): ibm = 'recorded'
    elif (ibm_dir / 'skipped.json').exists(): ibm = 'skipped_reserve'
    elif (ibm_dir / 'failure.json').exists(): ibm = 'failed'
    else: ibm = 'missing'
    if (qvm_dir / 'result.json').exists(): qvm = 'simulated'
    elif (qvm_dir / 'input.json').exists(): qvm = 'failed'
    else: qvm = 'missing'
    return ibm, qvm


def finish():
    ibm, qvm = states()
    p = json.loads(Path('_bio_connection/features.json').read_text())
    outcomes = ''
    r = Path('_bio_connection_ibm/chsh_game_result.json')
    if r.exists():
        outcomes = str(json.loads(r.read_text()).get('outcomes_sha256', ''))
    seed = sha(canonical({'packet_sha256': p['packet_sha256'], 'ibm_outcomes_sha256': outcomes, 'ibm': ibm}))
    summary = {'schema': 'beastbox-real-ibm-bio-connection-result-v1', 'packet_sha256': p['packet_sha256'],
               'heartbeat': 'MEASURED', 'ibm': ibm, 'ibm_label': 'RECORDED' if ibm == 'recorded' else 'NOT RECORDED',
               'rigetti': qvm, 'rigetti_label': 'SIMULATED', 'next_seed_sha256': seed,
               'seed_from': 'measured packet hash + real IBM outcomes hash (no clock, no random)'}
    Path('_bio_connection/result.json').write_text(json.dumps(summary, sort_keys=True, indent=2) + '\n')
    gh = os.environ.get('GITHUB_OUTPUT')
    if gh:
        with open(gh, 'a') as f:
            f.write(f'ibm={ibm}\nqvm={qvm}\n')
    print('BIO_CONNECTION_RESULT=' + canonical(summary))


if __name__ == '__main__':
    {'verify': verify, 'finish': finish}[sys.argv[1]]()
