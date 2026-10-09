import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('final_qvm', ROOT / 'scripts/azure_final_ibm_qvm.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class FinalIBMTransferTests(unittest.TestCase):
    def receipt(self):
        return json.loads((ROOT / 'apps/beastbox-cloud/experiment-input/ibm-final-live-20261009-receipt.json').read_text())

    def test_physical_source_changes_the_simulator_program(self):
        program, source = module.program_from_receipt(self.receipt())
        self.assertIn('RX(', program)
        self.assertIn('RY(', program)
        self.assertEqual(program.count('MEASURE'), 2)
        self.assertEqual(source['ibm_job_id'], 'db4m3bslf4us73c2ui9g')
        self.assertEqual(source['classical_measurement_transfer'], True)
        self.assertEqual(source['bell_ZZ'], 0.8720703125)
        self.assertEqual(source['decoupled_XX'], 0.04150390625)

    def test_forged_or_incomplete_source_is_refused(self):
        for field, value in [('job_status','QUEUED'), ('job_id','other'), ('source_class','SIMULATOR'),
                             ('counts_digest_sha256','0'*64), ('shot_count',16383)]:
            bad = self.receipt(); bad[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                module.program_from_receipt(bad)
        bad = self.receipt(); bad['measurements']['bell_xx']['00'] += 1
        with self.assertRaises(ValueError): module.program_from_receipt(bad)

    def test_provider_count_parser_checks_shots_and_bits(self):
        self.assertEqual(module.parse_counts({'ro': [[0,0],[1,1]]}, 2), {'00':1,'01':0,'10':0,'11':1})
        for result in [{'ro': [[0,2]]}, {'ro': {'00': 511}}, {'ro': {'00': 512.5}}, {}]:
            with self.assertRaises(ValueError): module.parse_counts(result, 512)

if __name__ == '__main__': unittest.main()
