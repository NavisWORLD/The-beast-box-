import json
import tempfile
import unittest
from pathlib import Path
import torch
from rawrphos.architecture.model import RawrphosConfig, RawrphosLM
from rawrphos.tokenizer.tokenizer import RawrphosTokenizer
from rawrphos.training.checkpoint import parameter_hash, rng_state, save_checkpoint
from scripts.zeref_round_recovery import save_snapshot, load_snapshot, prepare_bundle

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(2)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "zeref-006"
        self.root.mkdir()
        self.tok = RawrphosTokenizer.train(["Hello Zeref, this is a checkpoint test."] * 10, 300)
        self.model = RawrphosLM(RawrphosConfig(vocab_size=self.tok.vocab_size, d_model=32, n_heads=2, n_layers=3, max_seq_len=64))
        self.opt = torch.optim.AdamW(self.model.parameters(), lr=0.00005)
        self.gen = torch.Generator().manual_seed(67)
        self.parent = {"checkpoint_sha256": "a" * 64, "training_steps": 36464}

    def tearDown(self):
        self.tmp.cleanup()

    def snapshot(self, attempted=32, applied=29):
        return save_snapshot(self.root, self.model, self.tok, self.parent, self.opt, self.gen,
                             candidate=0, attempted=attempted, applied=applied)

    def test_real_checkpoint_preserves_weights_optimizer_rng_and_actual_steps(self):
        h = parameter_hash(self.model)
        rng = torch.get_rng_state().clone()
        self.snapshot()
        self.assertTrue(torch.equal(rng, torch.get_rng_state()), "snapshot must not consume training RNG")
        c, progress = load_snapshot(self.root)
        self.assertEqual(parameter_hash(c["model"]), h)
        self.assertEqual(c["metadata"]["training_steps"], 36493)
        self.assertEqual(progress["attempted_updates"], 32)
        self.assertEqual(progress["applied_optimizer_steps"], 29)
        self.assertEqual(c["state"]["optimizer"], self.opt.state_dict())
        self.assertTrue(torch.equal(c["state"]["data_rng"], self.gen.get_state()))
        self.assertFalse(c["metadata"]["production_promoted"])

    def test_failed_snapshot_does_not_replace_last_complete_pointer(self):
        self.snapshot()
        with torch.no_grad():
            next(self.model.parameters()).flatten()[0] = float("nan")
        with self.assertRaises(FloatingPointError):
            self.snapshot(64, 60)
        c, progress = load_snapshot(self.root)
        self.assertEqual(progress["attempted_updates"], 32)
        self.assertEqual(c["metadata"]["training_steps"], 36493)

    def test_corrupt_checkpoint_is_refused(self):
        self.snapshot()
        progress = json.loads((self.root / "recovery-progress.json").read_text())
        (self.root / progress["checkpoint"] / "model.safetensors").write_bytes(b"corrupt")
        with self.assertRaises(ValueError):
            load_snapshot(self.root)

    def test_progress_cannot_claim_more_applied_steps_than_attempts(self):
        self.snapshot()
        p = self.root / "recovery-progress.json"
        progress = json.loads(p.read_text())
        progress["applied_optimizer_steps"] = 33
        p.write_text(json.dumps(progress))
        with self.assertRaises(ValueError):
            load_snapshot(self.root)

    def test_snapshots_do_not_change_training_weights_or_data_order(self):
        import sys
        from unittest.mock import patch
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        import zeref_continuation_006 as trainer
        parent = self.root / "parent"
        state = {"optimizer":self.opt.state_dict(), "rng":rng_state(), "data_rng":self.gen.get_state()}
        save_checkpoint(parent,self.model,self.tok,{"training_steps":36464},state)
        row = trainer.tokens(self.tok,"User: play. Assistant: ","ACTION: RIGHT")
        settings = {"ROOT": self.root, "HEBBIAN":False, "TRINITY":False,"COND54":False,
                    "UPDATES":4,"EVAL_EVERY":2,"TIME_BUDGET_S":0,"GROW_LAYERS":0,
                    "WIP_IN":"","EMA_DECAY":0,"PRETRAIN_POOL":[],"BATCH":2}
        with patch.multiple(trainer, **settings):
            a,oa,ga,_ = trainer.train_variant(parent,self.tok,[("RIGHT",row)],67)
            b,ob,gb,_ = trainer.train_variant(parent,self.tok,[("RIGHT",row)],67,recovery_candidate=0)
        self.assertEqual(parameter_hash(a),parameter_hash(b))
        self.assertTrue(torch.equal(ga.get_state(),gb.get_state()))
        self.assertEqual(oa.state_dict()["param_groups"],ob.state_dict()["param_groups"])

    def test_bundle_has_only_latest_snapshot_and_no_private_corpus(self):
        self.snapshot()
        self.snapshot(64, 60)
        parent = self.root / "previous" / "accepted-checkpoint"
        state = {"optimizer": self.opt.state_dict(), "rng": rng_state(), "data_rng": self.gen.get_state()}
        save_checkpoint(parent, self.model, self.tok, {"training_steps":36464}, state)
        (parent.parent / "approval.json").write_text("{}")
        (self.root / "chat-mix.jsonl").write_text("private teaching text")
        (self.root / "teacher-pairs.jsonl").write_text("private lesson")
        (self.root / "inputs").mkdir()
        (self.root / "inputs" / "native-evidence-manifest.json").write_text("{}")
        dest = Path(self.tmp.name) / "bundle"
        prepare_bundle(self.root, parent, dest)
        c, progress = load_snapshot(dest / "zeref-006")
        self.assertEqual(progress["applied_optimizer_steps"], 60)
        self.assertFalse(list(dest.rglob("chat-mix.jsonl")))
        self.assertFalse(list(dest.rglob("teacher-pairs.jsonl")))
        self.assertEqual(len(list(dest.rglob("recovery-checkpoint/model.safetensors"))), 1)

if __name__ == "__main__":
    unittest.main()
