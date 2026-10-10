import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from zeref_fresh_heart_live import check_counts, sha, verify_physics


class SourceIntegrity(unittest.TestCase):
    def test_bool_or_wrong_shots_cannot_be_physical_counts(self):
        for counts in ({'00': True, '11': 4095}, {'00': 4095}, {'000': 4096}):
            with self.assertRaises(ValueError):
                check_counts(counts, 2)

    def test_exact_receipt_and_tamper_rejection(self):
        counts = {key: {'00': 2048, '11': 2048} for key in ('bell_zz', 'bell_xx', 'decoupled_zz', 'decoupled_xx')}
        receipt = {'schema': 'navisworld-ibm-longer-onejob-physics-receipt-v1', 'source_class': 'RECORDED_IBM_HARDWARE',
                   'job_status': 'DONE', 'shot_count': 16384, 'backend_name': 'ibm_fez', 'job_id': 'x' * 20,
                   'measurements': counts, 'counts_digest_sha256': sha(counts),
                   'expectations': {k[:-2] + k[-2:].upper(): 1.0 for k in counts}}
        receipt['beast_genesis_digest_sha256'] = sha({'domain': 'NAVISWORLD::IBM::ETERNAL_DRAGON_120S::QBEAST::V1',
            'job_id': receipt['job_id'], 'backend': receipt['backend_name'], 'counts': counts})
        self.assertEqual(verify_physics(receipt), receipt['expectations'])
        for field, value in (('source_class', 'SIMULATED'), ('job_status', 'QUEUED'), ('shot_count', 20480),
                             ('counts_digest_sha256', '0' * 64), ('beast_genesis_digest_sha256', '0' * 64)):
            bad = copy.deepcopy(receipt)
            bad[field] = value
            with self.assertRaises(ValueError):
                verify_physics(bad)


if __name__ == '__main__':
    unittest.main()
