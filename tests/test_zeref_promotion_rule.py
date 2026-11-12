import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import zeref_promotion_rule as z  # noqa: E402


def ev(c, leaks=0, cnw=True, ok=50):
    return {"candidate": {"ref_nll": c, "action_leaks": leaks, "ok_replies": ok},
            "baseline": {"ref_nll": 5.0}, "chat_not_worse": cnw,
            "gate": {"ref_nll_not_worse": True, "ok_replies_not_fewer": cnw, "no_more_game_action_leaks": leaks == 0}}


class PromotionRule(unittest.TestCase):
    def test_default_is_loose_and_strict_is_kept(self):
        self.assertEqual(z.PROMOTION_RULE, z.LOOSE_2026_11_12)
        self.assertEqual(z.STRICT_2026_10_22, "strict-2026-10-22")
        self.assertIn("Loosen both the training gate and the chat door", z.OWNER_DECISION["words"])

    def test_strict_rule_is_byte_for_byte_the_old_predicate(self):
        bar = 3.6
        for c in (3.55, 3.6, 3.6179, 3.6181, 3.7):
            for cnw in (True, False):
                old = bool(cnw and c <= bar * (1 + 0.005))
                self.assertEqual(z.decide(ev(c, cnw=cnw), bar, z.STRICT_2026_10_22)["promote"], old, (c, cnw))

    def test_loose_chat_not_worse_is_report_only(self):
        d = z.decide(ev(3.61, cnw=False), 3.6)
        self.assertTrue(d["promote"])
        self.assertFalse(d["chat_not_worse_vs_14000"])
        self.assertFalse(d["chat_not_worse_blocking"])
        self.assertIsNotNone(d["chat_gate_detail_report_only"])

    def test_loose_nll_tolerance_is_002_nats(self):
        self.assertTrue(z.decide(ev(3.62), 3.6)["promote"])
        self.assertFalse(z.decide(ev(3.6201), 3.6)["promote"])

    def test_leaks_stay_a_hard_zero(self):
        self.assertFalse(z.decide(ev(3.0, leaks=1), 3.6)["promote"])
        self.assertFalse(z.decide(ev(3.0, leaks=None), 3.6)["promote"])

    def test_non_finite_refused(self):
        with self.assertRaises(ValueError):
            z.decide(ev(float("nan")), 3.6)

    def test_cli_writes_decision_and_extra(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "pin.json").write_text(json.dumps({"promotion": {"candidate_ref_nll": 9.0}}))
            (t / "rep.json").write_text(json.dumps({"recipe": {"chat_before_nll": 3.6}}))
            (t / "ev.json").write_text(json.dumps(ev(3.61, cnw=False)))
            subprocess.run([sys.executable, str(ROOT / "scripts/zeref_promotion_rule.py"), str(t / "pin.json"), str(t / "rep.json"),
                            str(t / "ev.json"), str(t / "out.json"), '{"report_only":true}'], check=True, capture_output=True)
            d = json.loads((t / "out.json").read_text())
            self.assertEqual(d["pin_ref_nll_bar"], 3.6)
            self.assertTrue(d["promote"])
            self.assertTrue(d["report_only"])


if __name__ == "__main__":
    unittest.main()
