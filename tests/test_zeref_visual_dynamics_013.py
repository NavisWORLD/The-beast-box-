"""No false autonomy/vision claims in the original-ROM visual-dynamics pilot."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/zeref_visual_dynamics_013.py"
FLOW=ROOT/".github/workflows/zeref-visual-dynamics-013.yml"

class VisualDynamicsContract(unittest.TestCase):
 def test_exact_fixed_authentic_source_and_identity(self):
  s=SCRIPT.read_text()
  for text in ("bb-deada969","38216640554",
               "be3a7dc65877e4a024657dd910c33f4b1ebbbe7c4cdb10df74ad1b5d25ae8e1b",
               "ORIGINAL_EMULATOR_NATIVE_PIXEL_OBSERVATIONS",
               "OBSERVATION_CONDITIONED_SCRIPTED_HEURISTIC_NOT_HUMAN_NOT_MODEL",
               "native_ack_digest", "reward_is_not_native_progress"):
   self.assertIn(text,s)
 def test_holdout_and_arms_never_train_rawwrphos_or_claim_progress(self):
  s=SCRIPT.read_text()
  for text in ('r["episode"] in (0,1,2)','r["episode"]==3',
               'train(tr,False)','train(tr,True)',
               "G1_heldout_better_than_screen_persistence_10pct",
               "G2_heldout_action_conditioned_beats_blind_5pct",
               '"game_objective_progress_proven":False',
               '"action_outcome_causality_proven":False',
               '"accepted_auxiliary_research_only":accepted',
               'if accepted:',
               'no_model_approved_or_promoted',
               'external_quantum_jobs_submitted'):
   self.assertIn(text,s)
  for no in ("QiskitRuntimeService","SamplerV2(","AZURE_QUANTUM_CONNECTION_STRING","getUserMedia("):
   self.assertNotIn(no,s)
 def test_workflow_only_reads_fixed_existing_artifact(self):
  s=FLOW.read_text()
  for text in ("feature/zeref-visual-dynamics-013-",
               "38216640554","zeref-006-observed-training-report-38216640554",
               "python scripts/zeref_visual_dynamics_013.py",
               "if-no-files-found: warn"):
   self.assertIn(text,s)
  self.assertNotIn("secrets.IBM",s)
  self.assertNotIn("workflow_dispatch:",s)
if __name__=="__main__":
 unittest.main()
