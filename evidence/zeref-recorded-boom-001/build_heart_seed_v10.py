#!/usr/bin/env python3
"""Heart seed v10, built OFFLINE from already-RECORDED IBM hardware results only.
No provider calls, no randomness. Same chaining rule as v9:
heart_seed_sha256 = sha256(json.dumps(mix, sort_keys=True)).
Usage: build_heart_seed_v10.py <repo_root> <cst tape_all.json> <quantum_measurements_public.jsonl>"""
import json, hashlib, sys, glob, os, re, collections
H = lambda b: hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()
def fsha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()
def leaf(backend, job, counts):
    return H(json.dumps({"backend": backend, "job_id": job, "counts": counts}, sort_keys=True, separators=(',', ':')))
root, tape, jsonl = sys.argv[1:4]
IBM = re.compile(r'^ibm_[a-z]+$')
leaves = {}; jobs = {"zeref_evidence": set(), "cst_closed_loop": set(), "hfkit_public": set()}
dev = collections.defaultdict(set); excluded = collections.Counter()
# 1) Zeref evidence: IBM CHSH result files with a job id + ibm_ backend (whole-file hash as leaf)
for p in sorted(glob.glob(os.path.join(root, 'evidence/zeref-*/ibm-chsh-*.json'))) + sorted(glob.glob(os.path.join(root, 'evidence/rawrphos-closed-loop-*/results.json'))):
    d = json.load(open(p)); b = d.get('backend'); j = d.get('job_id')
    if not (j and b and IBM.match(b)): excluded['zeref_no_provenance'] += 1; continue
    l = H(b + '|' + j + '|' + fsha(p)); leaves[l] = 1; jobs['zeref_evidence'].add(j); dev[b].add(j)
# 2) CST closed-loop tape: 'hardware' section only (the 'simulated' Rigetti section is excluded)
t = json.load(open(tape))
for r in t['hardware']:
    b, j = r.get('backend'), r.get('job_id')
    if not (j and b and IBM.match(b)): excluded['cst_no_provenance'] += 1; continue
    leaves[leaf(b, j, r['counts'])] = 1; jobs['cst_closed_loop'].add(j); dev[b].add(j)
excluded['cst_simulated_records'] += len(t.get('simulated', []))
# 3) hfkit public jsonl: provider_class == measured_quantum_hardware with job id + ibm backend only (streamed)
with open(jsonl) as f:
    for line in f:
        r = json.loads(line); b, j = r.get('backend'), r.get('job_id')
        if r.get('provider_class') != 'measured_quantum_hardware' or not (j and b and IBM.match(b)):
            excluded['hfkit_' + str(r.get('provider_class'))] += 1; continue
        leaves[leaf(b, j, r['counts'])] = 1; jobs['hfkit_public'].add(j); dev[b].add(j)
ordered = sorted(leaves)
records_root = H('\n'.join(ordered))
v9 = json.load(open(os.path.join(root, 'evidence/zeref-bio-spark-001/heart-seed-v9.json')))
assert H(json.dumps(v9['mix'], sort_keys=True)) == v9['heart_seed_sha256'], 'v9 rule mismatch'
alljobs = set().union(*jobs.values())
mix = {
    "heart_seed_v9_sha256": v9['heart_seed_sha256'],
    "recorded_ibm_records_root_sha256": records_root,
    "recorded_ibm_unique_records": len(ordered),
    "recorded_ibm_unique_jobs": len(alljobs),
    "jobs_per_device": {k: len(v) for k, v in sorted(dev.items())},
    "jobs_per_source": {k: len(v) for k, v in sorted(jobs.items())},
    "input_file_sha256": {"cst_tape_all.json": fsha(tape), "quantum_measurements_public.jsonl": fsha(jsonl)},
}
out = {
    "creature_id": v9.get('creature_id'),
    "heart_seed_sha256": H(json.dumps(mix, sort_keys=True)),
    "label": "zeref-recorded-boom-001 (2026-10-31) heart seed v10; RECORDED-derived, not a new quantum measurement; earlier seeds unchanged",
    "source_class": "RECORDED_IBM_HARDWARE (derived offline)",
    "mix": mix,
    "excluded": dict(sorted(excluded.items())),
    "not_for": v9.get('not_for'),
    "note": "No new IBM job. Quantum hardware cannot learn text; this only seeds batch order. Not wired into the live spark, pin, gates or bridge.",
}
print(json.dumps(out, indent=1, sort_keys=True))
