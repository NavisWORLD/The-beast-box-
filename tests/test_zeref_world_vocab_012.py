"""Contract audit for genuine source-grounded (not quantum) Zeref RAWRPHOS world pilot."""
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"research/zeref/world-vocab-012/grounded-cards.json"
TRAIN=ROOT/"scripts/zeref_world_vocab_012.py"
FLOW=ROOT/".github/workflows/zeref-world-vocab-012.yml"

class GroundedWorldVocabularyContract(unittest.TestCase):
    def test_primary_agency_provenance_and_no_split_leaks(self):
        data=json.loads(DATA.read_text())
        self.assertEqual(data["schema"],"zeref-world-knowledge-cards/v1")
        self.assertEqual(data["training_identity"],"bb-deada969")
        cards=data["cards"]
        ids=[r["id"] for r in cards]
        self.assertEqual(len(ids),len(set(ids)))
        train={r["id"] for r in cards if r["split"]=="train"}
        holdout={r["id"] for r in cards if r["split"]=="holdout"}
        self.assertGreaterEqual(len(train),20)
        self.assertGreaterEqual(len(holdout),5)
        self.assertFalse(train&holdout)
        for r in cards:
            self.assertTrue(r["answer"].casefold() in r["evidence"].casefold())
            self.assertTrue(r["source_url"].startswith(("https://science.nasa.gov/",
                                                        "https://www.usgs.gov/",
                                                        "https://www.nist.gov/",
                                                        "https://oceanservice.noaa.gov/")))
            self.assertIn("paraphrase",r["provenance"])
            self.assertNotIn("conversation",r["source_name"].casefold())

    def test_training_is_pinned_unpromoted_and_contains_real_gates(self):
        text=TRAIN.read_text()
        for needle in (
            "EXPECTED_PARENT = \"460a1a3fbbc16919c5030af16d5bd451ef43e96fd28b8c3201ca7efca1250ef2\"",
            "EXPECTED_NATIVE_CYCLE = 38210153369",
            "tok.vocab_size != 4096",
            "load_training_state=True",
            'opt.load_state_dict(parent["state"]["optimizer"])',
            '"production_promoted":False',
            '"canonical_training_parent_eligible":False',
            '"G1_world_heldout_nll_improves"',
            '"G2_native_heldout_nll_within_5pct"',
            '"G3_basic_language_retention_within_10pct"',
            '"G4_unsupported_question_nll_not_worse"',
            '"G5_source_grounded_generated_answers_not_worse"',
            '"G6_frozen_tokenizer_and_checkpoint_integrity"',
            "Not enough evidence.",
            "ZEREF_012_WORLD_KNOWLEDGE_GATE",
            "shutil.rmtree(target)"
        ):
            self.assertIn(needle,text)
        for forbidden in ("QiskitRuntimeService", "SamplerV2(", "AZURE_QUANTUM_TOKEN", "getUserMedia("):
            self.assertNotIn(forbidden,text)

    def test_workflow_is_cpu_only_and_never_promotes_a_model(self):
        text=FLOW.read_text()
        self.assertIn("feature/zeref-world-vocab-012-",text)
        self.assertIn("38210153369",text)
        self.assertIn("zeref-006-canonical-37ca3f8f",text)
        self.assertIn("python -u scripts/zeref_world_vocab_012.py",text)
        self.assertIn("if-no-files-found: warn",text)
        self.assertNotIn("IBM_QUANTUM_TOKEN",text)
        self.assertNotIn("AZURE_QUANTUM_CONNECTION_STRING",text)
        self.assertNotIn("secrets.IBM",text)

if __name__=="__main__":
    unittest.main()
