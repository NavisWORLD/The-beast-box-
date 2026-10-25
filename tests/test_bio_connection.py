import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import bio_connection_packet as b


def packet():
    body = {'schema': b.SCHEMA, 'source': b.SOURCE, 'heartbeat_label': 'MEASURED', 'honesty': 'Heartbeat MEASURED. Numbers only.',
            'pulse': {'bpm': 72.0, 'hrv_rmssd_ms': 25.5, 'sqi': 0.9766, 'beats': 38, 'duration_s': 32.0, 'fs_hz': 30},
            'light': {'red_mean': 201.5, 'green_mean': 41.25, 'blue_mean': 30, 'red_ac_dc': 0.0123},
            'audio': {'enabled': False, 'rms_mean': 0, 'zcr': 0, 'centroid_norm': 0},
            'bio_vector_12': [0.2, 0.17, 0.95, 0.246, 0.79, 0.16, 0.12, 0.05, 0.05, 0.05, 0.8, 0.5],
            'raw_audio_published': False, 'raw_video_published': False, 'raw_frames_in_packet': False}
    return {**body, 'packet_sha256': b.sha(b.canonical(body))}


class BioConnection(unittest.TestCase):
    def test_canonical_matches_js_for_integral_floats(self):
        self.assertEqual(b.canonical({'a': 72.0, 'b': 0.5, 'c': [1.0, 0.0001]}), '{"a":72,"b":0.5,"c":[1,0.0001]}')

    def test_valid_packet(self):
        self.assertEqual(b.validate(packet()), [])

    def test_rejects_raw_and_extras(self):
        for k, v in [('raw_video_published', True), ('raw_audio_published', True), ('raw_frames_in_packet', True), ('samples', [1, 2]),
                     ('heartbeat_label', 'SIMULATED')]:
            p = packet(); p[k] = v
            self.assertTrue(b.validate(p), k)
        p = packet(); p['pulse']['sqi'] = 0.3
        self.assertTrue(b.validate(p))
        p = packet(); p['bio_vector_12'] = [0.5] * 11
        self.assertTrue(b.validate(p))

    def run_cli(self, mode, env, cwd):
        return subprocess.run([sys.executable, str(ROOT / 'scripts' / 'bio_connection_packet.py'), mode], cwd=cwd,
                              env={**os.environ, **env}, capture_output=True, text=True)

    def test_verify_cli_writes_feature_packet_for_qvm(self):
        p = packet()
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'gh_out'
            r = self.run_cli('verify', {'BIO_PACKET_JSON': json.dumps(p), 'BIO_PACKET_SHA12': p['packet_sha256'][:12], 'GITHUB_OUTPUT': str(out)}, d)
            self.assertEqual(r.returncode, 0, r.stderr)
            f = json.loads((Path(d) / '_bio_connection' / 'features.json').read_text())
            self.assertIs(f['raw_audio_published'], False)
            self.assertEqual(len(f['bio_vector_12']), 12)
            self.assertIn('tag=navisworld-real-ibm-bio-' + p['packet_sha256'][:12], out.read_text())

    def test_verify_cli_rejects_tamper_and_bad_sha(self):
        p = packet()
        with tempfile.TemporaryDirectory() as d:
            t = json.loads(json.dumps(p)); t['pulse']['bpm'] = 80
            self.assertNotEqual(self.run_cli('verify', {'BIO_PACKET_JSON': json.dumps(t), 'BIO_PACKET_SHA12': p['packet_sha256'][:12]}, d).returncode, 0)
            self.assertNotEqual(self.run_cli('verify', {'BIO_PACKET_JSON': json.dumps(p), 'BIO_PACKET_SHA12': '0' * 12}, d).returncode, 0)
            self.assertNotEqual(self.run_cli('verify', {'BIO_PACKET_JSON': json.dumps(p), 'BIO_PACKET_SHA12': '$(rm -rf /)'}, d).returncode, 0)

    def test_finish_states_and_seed_are_deterministic_and_honest(self):
        p = packet()
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d); (dd / '_bio_connection').mkdir(); (dd / '_bio_connection' / 'features.json').write_text(json.dumps(p))
            (dd / '_bio_connection_ibm').mkdir(); (dd / '_bio_connection_ibm' / 'skipped.json').write_text('{}')
            r = self.run_cli('finish', {}, d); self.assertEqual(r.returncode, 0, r.stderr)
            s1 = json.loads((dd / '_bio_connection' / 'result.json').read_text())
            self.assertEqual((s1['ibm'], s1['ibm_label'], s1['rigetti_label']), ('skipped_reserve', 'NOT RECORDED', 'SIMULATED'))
            (dd / '_bio_connection_ibm' / 'skipped.json').unlink()
            (dd / '_bio_connection_ibm' / 'chsh_game_result.json').write_text(json.dumps({'outcomes_sha256': 'ab' * 32}))
            self.run_cli('finish', {}, d)
            s2 = json.loads((dd / '_bio_connection' / 'result.json').read_text())
            self.assertEqual((s2['ibm'], s2['ibm_label']), ('recorded', 'RECORDED'))
            self.assertNotEqual(s1['next_seed_sha256'], s2['next_seed_sha256'])
            self.run_cli('finish', {}, d)
            self.assertEqual(json.loads((dd / '_bio_connection' / 'result.json').read_text()), s2)


if __name__ == '__main__':
    unittest.main()
