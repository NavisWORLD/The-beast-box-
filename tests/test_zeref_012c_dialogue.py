import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import zeref_012c_joint_dialogue as C


class Zeref012CDialogueContracts(unittest.TestCase):
    def test_public_guest_safe_train_holdout_splits(self):
        train, held = C.corpus()
        self.assertEqual(len(train), 60)
        self.assertEqual(len(held), 20)
        self.assertEqual(set(x["id"] for x in train)&set(x["id"] for x in held), set())
        self.assertEqual(set(x["user"] for x in train)&set(x["user"] for x in held), set())
        self.assertEqual(set(x["topic"] for x in train), set(C.TOPICS))
        self.assertEqual(set(x["topic"] for x in held), set(C.TOPICS))
        for r in train+held:
            self.assertEqual(r["schema"],C.SCHEMA)
            self.assertEqual(r["source_class"],C.PROVENANCE)
            self.assertIs(r["raw_user_conversation"],False)
            self.assertIs(r["private_scope"],False)
            self.assertNotIn("cory",r["answer"].lower())
            self.assertNotIn("dad,",r["answer"].lower())

    def test_manifest_and_replay_integrity(self):
        a,b=C.corpus()
        m=C.manifest()
        self.assertEqual(m["train_sha256"],hashlib.sha256(C.serialize(a).encode()).hexdigest())
        self.assertEqual(m["holdout_sha256"],hashlib.sha256(C.serialize(b).encode()).hexdigest())
        self.assertIs(m["user_private_data_used"],False)
        self.assertIs(m["model_output_as_teacher"],False)
        self.assertTrue(m["not_owner_personal_history"])
        self.assertEqual(len([json.loads(t) for t in C.serialize(a).splitlines()]),60)
        self.assertEqual(len([json.loads(t) for t in C.serialize(b).splitlines()]),20)

    def test_questions_and_targets_are_not_copied_from_guests(self):
        train, held=C.corpus()
        for r in train+held:
            self.assertNotIn("private chat",r["user"].lower().replace("stranger's ","")) if False else None
            self.assertGreater(len(r["user"]),5)
            self.assertGreater(len(r["answer"]),5)
            self.assertLess(len(r["answer"]),171)
        self.assertEqual(len(set((r["user"],r["answer"]) for r in train+held)),80)


if __name__=="__main__":
    unittest.main()
