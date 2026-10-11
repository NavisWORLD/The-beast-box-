"""Fail-closed owner receipt contract for native Zeref 004."""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("zeref_native_004_ibm",ROOT/"scripts"/"zeref_native_004_ibm.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TestZerefNative004(unittest.TestCase):
 def test_pinned_original_source_and_budget(self):
  src=module.validate_source()
  self.assertEqual(src["qbeast_id"],"bb-deada969")
  self.assertEqual(src["source_ibm_job_id"],"db4q484vf2bc73cuuuag")
  self.assertEqual(src["source_shots"],20480)
  self.assertEqual(module.CAP_SECONDS,10)
  self.assertEqual(module.SHOTS,512)
  self.assertTrue(module.TAG.startswith("navisworld-zeref-perception-004-"))
 def test_no_credential_or_training_claims_in_script(self):
  source=(ROOT/"scripts"/"zeref_native_004_ibm.py").read_text()
  self.assertIn('plans_preference=["open"]',source)
  self.assertIn('quota["already_consumed_seconds"]+CAP_SECONDS>300',source)
  self.assertIn('service.jobs(limit=100,program_id="sampler",job_tags=[TAG])',source)
  self.assertIn('"model_training_performed_by_this_job":False',source)
  self.assertIn('sampler.options.max_execution_time=CAP_SECONDS',source)
  self.assertNotIn("AZURE_QUANTUM_CONNECTION_STRING",source)
 def test_real_training_zeref_is_separate_and_production_frozen(self):
  source=(ROOT/"scripts"/"train_rawrphos_from_observed_native_play.py").read_text()
  self.assertIn('"bb-deada969"',source) if '"bb-deada969"' in source else self.assertIn("'bb-deada969'",source)
  self.assertIn("'production_promoted':False",source.replace('"production_promoted":False',"'production_promoted':False"))
  self.assertIn("TRAIN",source.upper())
  js=(ROOT/"apps"/"beastbox-cloud"/"tests"/"rawrphos-native-observed-play.cjs").read_text()
  self.assertIn("NAVISWORLD_NATIVE_TRAINING_BEAST",js)
  self.assertIn("bb-deada969",js)

if __name__=="__main__":unittest.main()
