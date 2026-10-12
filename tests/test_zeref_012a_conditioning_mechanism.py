"""Bounded, synthetic-unit contract tests. No real model checkpoint or provider call."""
import sys
import json
import tempfile
import unittest
from pathlib import Path

import torch
from rawrphos.architecture.model import RawrphosConfig, RawrphosLM
from rawrphos.training.checkpoint import parameter_hash

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import zeref_012a_conditioning_mechanism as M


class MechanismContracts(unittest.TestCase):
    def test_null_adapter_cannot_change_parent_logits(self):
        torch.manual_seed(3)
        model = RawrphosLM(RawrphosConfig(vocab_size=320, d_model=32, n_heads=4,
                                         n_layers=2, max_seq_len=32))
        model.eval()
        before = parameter_hash(model)
        adapter = M.StateConditionAdapter()
        example = [[.1,.2,.3,.4,.5,.6,.7,.8,.9,.1,.2,.3]]
        ids = torch.tensor([[1,31,40,45]], dtype=torch.long)
        with torch.no_grad():
            self.assertTrue(torch.equal(model(ids)["logits"],
                                        model(ids, control_vector=adapter(example))["logits"]))
        self.assertEqual(parameter_hash(model), before)

    def test_features_arm_classical_and_shuffle_are_explicit(self):
        rows = [{"run_key": "job-"+str(i), "features": [i/20]*12}
                for i in range(10)]
        aligned = M.arm_rows(rows, "aligned_ibm", 9)
        shuffled = M.arm_rows(rows, "shuffled_ibm", 9)
        control = M.arm_rows(rows, "independent_classical", 9)
        self.assertEqual(aligned, [r["features"] for r in rows])
        self.assertNotEqual(shuffled, aligned)
        self.assertEqual(sorted(str(x) for x in shuffled), sorted(str(x) for x in aligned))
        self.assertEqual(control, M.arm_rows(rows, "independent_classical", 9))
        self.assertNotEqual(control, aligned)
        self.assertEqual(len(control[0]), 12)
        self.assertEqual(M.arm_rows(rows, "constant_classical", 9), [[.25]*12]*10)
        self.assertEqual(M.label_from_feature([0,0,0,0,0,0,.6,0,0,0,0,0], .5), 1)

    def test_training_adapter_updates_but_base_stays_frozen(self):
        torch.manual_seed(9)
        base = RawrphosLM(RawrphosConfig(vocab_size=320, d_model=32, n_heads=4,
                                        n_layers=2, max_seq_len=32))
        for p in base.parameters():
            p.requires_grad_(False)
        base.eval()
        before = parameter_hash(base)
        adapter = M.StateConditionAdapter()
        opt = torch.optim.AdamW(adapter.parameters(), lr=.01)
        features = [[.8]*12, [.1]*12]
        ids = torch.tensor([[1,31,40], [1,31,40]], dtype=torch.long)
        target = torch.tensor([1,0])
        for _ in range(3):
            opt.zero_grad()
            logits = base(ids, control_vector=adapter(features))["logits"][:,-1,[42,43]]
            loss = torch.nn.functional.cross_entropy(logits,target)
            loss.backward()
            opt.step()
        self.assertEqual(parameter_hash(base), before)
        self.assertGreater(sum(float(p.abs().sum()) for p in adapter.project[-1].parameters()), 0)

    def test_no_adapter_baseline_evaluation_regression(self):
        torch.manual_seed(10)
        model = RawrphosLM(RawrphosConfig(vocab_size=320, d_model=32, n_heads=4,
                                         n_layers=2, max_seq_len=32))
        ids = torch.tensor([[1,31,40]], dtype=torch.long)
        rows = [{"features": [.1,.1,.1,.1,.1,.1,.3,.1,.1,.1,.1,.1], "run_key":"low"},
                {"features": [.9,.9,.9,.9,.9,.9,.7,.9,.9,.9,.9,.9], "run_key":"high"}]
        report = M.evaluation(model, None, ids, [42,43], rows, "aligned_ibm", .5, 11)
        self.assertEqual(report["rows"], 2)
        self.assertTrue(0 <= report["balanced_accuracy"] <= 1)
        self.assertTrue(report["two_class_nll"] > 0)

    def test_rejects_unlabelled_or_misclassified_sources(self):
        example = {"schema": "rawrphos-recorded-count-conditioning/v1", "role": "STATE_CONDITIONING_ONLY",
                   "source_class": "RECORDED_IBM_HARDWARE", "split":"train", "action_label":None,
                   "reward_label":None, "dialogue_target":None,
                   "independent_physical_channels_claimed":False,
                   "run_key":"r1", "counts_sha256":"a"*64,"features":[.5]*12}
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"sample.jsonl"
            p.write_text(json.dumps(example)+"\n")
            self.assertEqual(len(M.read_rows(p,"train")),1)
            example["source_class"]="RECORDED_AZURE_RIGETTI_QVM_SIMULATOR"
            p.write_text(json.dumps(example)+"\n")
            with self.assertRaises(ValueError):
                M.read_rows(p,"train")
            example["source_class"]="RECORDED_IBM_HARDWARE";example["action_label"]="RIGHT"
            p.write_text(json.dumps(example)+"\n")
            with self.assertRaises(ValueError):
                M.read_rows(p,"train")


if __name__ == "__main__":
    unittest.main()
