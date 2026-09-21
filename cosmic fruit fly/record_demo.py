"""Build independently checked, timestamped visual replay events from executed code.

Do not treat the rendered video as screen capture, physiology or fly behavior.
The source harness and historical evidence files are not modified.
"""
from __future__ import annotations

import hashlib
import json
import bisect
import importlib.util
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
EVIDENCE = HERE / 'evidence' / 'synthetic_2026-09-19'
RECORD = HERE / 'demo_recording'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    RECORD.mkdir(exist_ok=True)
    hashes = json.loads((EVIDENCE / 'SHA256SUMS.json').read_text(encoding='utf8'))
    for name, value in hashes.items():
        assert sha(EVIDENCE / name) == value, f'evidence corruption: {name}'
    summary = json.loads((EVIDENCE / 'summary.json').read_text(encoding='utf8'))
    assert sha(HERE / 'harness.py') == summary['harness_sha256']
    assert sha(HERE.parent / 'beastbox' / 'dyn12.py') == summary['canonical_dyn12_sha256']

    spec = importlib.util.spec_from_file_location('fruit_harness_for_replay', HERE / 'harness.py')
    h = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = h
    spec.loader.exec_module(h)
    graph = h.load_graph(EVIDENCE / 'synthetic_connections.csv', EVIDENCE / 'synthetic_connections.metadata.json')
    saved = [json.loads(line) for line in (EVIDENCE / 'trials.jsonl').read_text().splitlines()]
    assert len(saved) == 72
    lookup = {(r['arm'], r['seed']): r for r in saved}

    # Run all 72 arms from the unmodified source and confirm ALL episode-level
    # actions, rewards and state norms match historical evidence, not just means.
    full = h.experiment(graph)
    exact = 0
    for r in full['runs']:
        orig = lookup[(r['arm'], r['seed'])]
        for k in r:
            if k != 'elapsed_ms':
                assert r[k] == orig[k], f'replay divergence in {r["arm"]}, seed {r["seed"]}, key {k}'
        exact += 1
    for arm, stats in full['summary'].items():
        for k in stats:
            if k != 'elapsed_ms_mean':
                assert stats[k] == summary['summary'][arm][k]

    captured = {}
    arm_order = ('connectome', 'topology_control', 'lesion', 'memory_off', 'baseline')
    selected = {0, 1, 5, 15, 79, 80, 81, 82, 90, 119}
    original_dyn = h.dynamics
    original_state = h.canonical_dyn12
    plan = h.episode_plan(0, 80, 40)
    bounds = [0]
    for trial in plan:
        bounds.append(bounds[-1] + trial['delay'] + 1)

    try:
        for arm in arm_order:
            arm_events = []
            pending = [None]
            def neural_hook(g, kind, neural, cue, ctx, plastic, lesion_set):
                nxt, ops = original_dyn(g, kind, neural, cue, ctx, plastic, lesion_set)
                pending[0] = {'neural': [round(x, 7) for x in nxt],
                              'stimulus': round(cue, 7), 'context_signal': round(ctx, 7),
                              'plasticity_l1_at_tick': round(sum(abs(x) for x in plastic), 7),
                              'lesion_indices': sorted(lesion_set), 'edge_ops': ops}
                return nxt, ops
            def state_hook(state, drive, step):
                nxt = original_state(state, drive, step)
                episode = bisect.bisect_right(bounds, step) - 1
                assert 0 <= episode < len(plan)
                if episode in selected:
                    assert pending[0] is not None
                    event = dict(pending[0])
                    event.update({'step': step, 'episode': episode, 'tick': step - bounds[episode],
                                  'state': [round(x, 7) for x in nxt],
                                  'pool': [round(x, 7) for x in drive],
                                  'phase': plan[episode]['phase'],
                                  'cue_original': plan[episode]['cue'],
                                  'context_original': plan[episode]['context']})
                    arm_events.append(event)
                pending[0] = None
                return nxt
            h.dynamics = neural_hook
            h.canonical_dyn12 = state_hook
            result = h.run_arm(graph, arm, 0)
            orig = lookup[(arm, 0)]
            assert result['trace'] == orig['trace'], f'captured replay divergent: {arm}'
            assert len(arm_events) == sum(plan[i]['delay'] + 1 for i in selected)
            for event in arm_events:
                row = result['trace'][event['episode']]
                event.update({'action': row['action'], 'target': row['target'], 'reward': row['reward'],
                              'outcome_state_norm': row['state_norm']})
            captured[arm] = {'events': arm_events, 'result': {k: v for k, v in result.items() if k not in ('trace', 'elapsed_ms')},
                             'trace_sha256': hashlib.sha256(json.dumps(result['trace'], sort_keys=True).encode()).hexdigest()}
    finally:
        h.dynamics = original_dyn
        h.canonical_dyn12 = original_state
    out = {
        'classification': 'SYNTHETIC FIXTURE — NOT BIOLOGICAL CONNECTOME',
        'replay_type': 'rendered visualization of re-executed software state; NOT screen or camera recording',
        'original_source_hash': summary['harness_sha256'],
        'original_evidence_checksums_verified': True,
        'exact_replays_verified': exact,
        'graph': {'nodes': len(graph.ids), 'edges': len(graph.edges), 'sha256': summary['input_sha256'],
                  'edge_list': [list(e) for e in graph.edges]},
        'settings': summary['settings'],
        'summary': summary['summary'],
        'arms': captured,
    }
    (RECORD / 'replay.json').write_text(json.dumps(out, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf8')
    manifest = {'replay.json': sha(RECORD/'replay.json'), 'recorder.py': sha(pathlib.Path(__file__)),
                'source_harness.py': summary['harness_sha256'], 'archived_trials.jsonl': sha(EVIDENCE/'trials.jsonl')}
    (RECORD / 'capture_manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n',encoding='utf8')
    print(json.dumps({'verified_replays': exact, 'captured_arms': arm_order,
                      'captured_tick_counts': {k: len(v['events']) for k, v in captured.items()},
                      'replay_sha256': manifest['replay.json']}, indent=2))


if __name__ == '__main__':
    run()
