"""Owner-only shadow bridge: fake Cosmos, no Azure/Rigetti/network access."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from beastbox.quantum_buddy.state import BuddyCurrentState

SOURCE = Path(__file__).resolve().parents[1] / "owner_bridge.py"
spec = importlib.util.spec_from_file_location("owner_bridge_buddy_shadow", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

TOKEN = "synthetic-ci-owner-bridge-" + "x" * 40
AUTH = "Bearer " + TOKEN


class FakeRepo:
    def __init__(self, *, consent=True):
        self.current = BuddyCurrentState.new(
            user_id="owner-opaque-a", dyn12=[0.2, -0.2] * 6,
            state_version=3, state_conditioning_consent=consent,
            quantum_refresh_consent=consent,
        )
        self.receipts = []
        self.etag = '"fake-etag-1"'

    def read_current(self, user_id):
        if user_id != self.current.user_id:
            raise ValueError("cross-user data must never leave repository")
        return self.current, self.etag

    def create_current(self, state):
        self.current = state
        return state

    def update_person_state(self, user_id, *, dyn12, etag,
                            state_conditioning_consent, quantum_refresh_consent):
        if etag != self.etag or user_id != self.current.user_id:
            raise ValueError("stale or cross-user request")
        self.current = BuddyCurrentState.new(
            user_id=user_id, dyn12=dyn12,
            state_version=self.current.state_version + 1,
            state_conditioning_consent=state_conditioning_consent,
            quantum_refresh_consent=quantum_refresh_consent,
        )
        self.etag = '"fake-etag-2"'
        return self.current

    def append_history(self, receipt):
        self.receipts.append(dict(receipt))
        return "receipt:synthetic"


class BuddyBridgeTests(unittest.TestCase):
    def make_bridge(self, *, enabled="no", shadow="no", cosmos_write="no"):
        context = tempfile.TemporaryDirectory()
        self.addCleanup(context.cleanup)
        root = Path(context.name)
        env = {
            "BEASTBOX_QUANTUM_BUDDY_ENABLED": enabled,
            "BEASTBOX_QUANTUM_BUDDY_SHADOW_ENABLED": shadow,
            "BEASTBOX_QUANTUM_BUDDY_COSMOS_WRITES_ENABLED": cosmos_write,
        }
        with patch.dict(os.environ, env):
            bridge = module.OwnerBridge(root, TOKEN)
        return bridge

    def test_status_is_owner_only_disabled_by_default_and_never_leaks_endpoint(self):
        bridge = self.make_bridge()
        self.assertEqual(bridge.dispatch("GET", "/api/quantum-buddy", "")[0], 401)
        status, info = bridge.dispatch("GET", "/api/quantum-buddy", AUTH)
        self.assertEqual(status, 200, info)
        self.assertIs(info["enabled"], False)
        self.assertIs(info["shadow_enabled"], False)
        self.assertIs(info["hardware_enabled"], False)
        self.assertNotIn("endpoint", json.dumps(info).lower())
        self.assertEqual(bridge.dispatch(
            "POST", "/api/quantum-buddy/state", AUTH,
            json.dumps({"action": "read", "userId": "owner-opaque-a"}).encode(),
        )[0], 503)

    def test_shadow_requires_separate_feature_flag_and_preserves_chat(self):
        bridge = self.make_bridge(enabled="yes", shadow="no")
        code, _ = bridge.dispatch(
            "POST", "/api/quantum-buddy/shadow", AUTH,
            json.dumps({
                "userId": "owner-opaque-a", "prompt": "hello",
                "mode": "matched_classical", "max_tokens": 2, "seed": 67,
            }).encode(),
        )
        self.assertEqual(code, 503)
        code, ordinary = bridge.dispatch(
            "POST", "/api/chat", AUTH,
            json.dumps({"text": "hello"}).encode(),
        )
        self.assertEqual(code, 200, ordinary)

    def test_bounded_shadow_runs_source_blind_without_changing_ordinary_chat(self):
        bridge = self.make_bridge(enabled="yes", shadow="yes", cosmos_write="yes")
        repo = FakeRepo()
        bridge.quantum_buddy_repo_factory = lambda: repo
        model_calls = []

        def fake_infer(prompt, person, metric, max_tokens, seed):
            model_calls.append((prompt, person, metric, max_tokens, seed))
            return {
                "checkpoint_sha256": "a" * 64,
                "model_weights_changed": False,
                "quantum_advantage_proven": False,
                "logit_l2": 0.123,
                "response_ordinary": "hello",
                "response_buddy": "hello",
            }

        bridge.quantum_buddy_shadow_infer = fake_infer
        request = {
            "userId": "owner-opaque-a", "prompt": "hello",
            "mode": "matched_classical", "max_tokens": 2, "seed": 67,
        }
        self.assertEqual(bridge.dispatch(
            "POST", "/api/quantum-buddy/shadow", "", json.dumps(request).encode(),
        )[0], 401)
        code, result = bridge.dispatch(
            "POST", "/api/quantum-buddy/shadow", AUTH, json.dumps(request).encode(),
        )
        self.assertEqual(code, 200, result)
        self.assertEqual(result["source_class"], "classical")
        self.assertFalse(result["fresh_hardware_used"])
        self.assertEqual(len(model_calls), 1)
        self.assertEqual(len(model_calls[0][1]), 12)
        self.assertEqual(len(model_calls[0][2]), 12)
        self.assertEqual(len(repo.receipts), 1)
        self.assertNotIn("response_buddy", repo.receipts[0])
        self.assertEqual(bridge.dispatch(
            "POST", "/api/chat", AUTH, json.dumps({"text": "hello"}).encode(),
        )[0], 200)

        for changed in (
            {**request, "mode": "hardware_rigetti"},
            {**request, "extra": "authority"},
            {**request, "max_tokens": 100000},
        ):
            bad, _ = bridge.dispatch(
                "POST", "/api/quantum-buddy/shadow", AUTH,
                json.dumps(changed).encode(),
            )
            self.assertIn(bad, (400, 403))

    def test_shadow_failure_keeps_normal_chat_and_redacts_errors(self):
        bridge = self.make_bridge(enabled="yes", shadow="yes")
        repo = FakeRepo()
        bridge.quantum_buddy_repo_factory = lambda: repo

        def fail(*args):
            raise RuntimeError("synthetic-private-token-MUST-NOT-LEAK")

        bridge.quantum_buddy_shadow_infer = fail
        body = json.dumps({
            "userId": "owner-opaque-a", "prompt": "hello",
            "mode": "matched_classical", "max_tokens": 2, "seed": 67,
        }).encode()
        status, err = bridge.dispatch("POST", "/api/quantum-buddy/shadow", AUTH, body)
        self.assertEqual(status, 503)
        self.assertNotIn("MUST-NOT-LEAK", json.dumps(err))
        self.assertEqual(bridge.dispatch(
            "POST", "/api/chat", AUTH, json.dumps({"text": "hello"}).encode(),
        )[0], 200)

    def test_consent_and_explicit_cosmos_write_gate(self):
        bridge = self.make_bridge(enabled="yes", shadow="yes")
        repo = FakeRepo(consent=False)
        bridge.quantum_buddy_repo_factory = lambda: repo
        request = {
            "userId": "owner-opaque-a", "prompt": "hello",
            "mode": "matched_classical", "max_tokens": 2, "seed": 67,
        }
        self.assertEqual(bridge.dispatch(
            "POST", "/api/quantum-buddy/shadow", AUTH, json.dumps(request).encode(),
        )[0], 403)
        creation = {
            "action": "create", "userId": "owner-opaque-a",
            "dyn12": [0.1] * 12,
            "stateConditioningConsent": True,
            "quantumRefreshConsent": False,
        }
        self.assertEqual(bridge.dispatch(
            "POST", "/api/quantum-buddy/state", AUTH, json.dumps(creation).encode(),
        )[0], 403)

    def test_shadow_without_separate_cosmos_write_flag_is_ephemeral(self):
        """Opt-in comparison alone never enables a new Cosmos mutation."""
        bridge = self.make_bridge(enabled="yes", shadow="yes", cosmos_write="no")
        repo = FakeRepo()
        bridge.quantum_buddy_repo_factory = lambda: repo
        bridge.quantum_buddy_shadow_infer = lambda *args: {
            "checkpoint_sha256": "a" * 64,
            "model_weights_changed": False,
            "quantum_advantage_proven": False,
            "logit_l2": 0.25,
            "response_ordinary": "ordinary",
            "response_buddy": "conditioned",
        }
        request = {
            "userId": "owner-opaque-a", "prompt": "hello",
            "mode": "matched_classical", "max_tokens": 2, "seed": 67,
        }
        code, result = bridge.dispatch(
            "POST", "/api/quantum-buddy/shadow", AUTH, json.dumps(request).encode(),
        )
        self.assertEqual(code, 200, result)
        self.assertFalse(result["persisted"])
        self.assertIsNone(result["history_receipt_id"])
        self.assertEqual(repo.receipts, [])
        self.assertEqual(bridge.dispatch(
            "POST", "/api/chat", AUTH, json.dumps({"text": "hello"}).encode(),
        )[0], 200)


    def test_revoke_state_consent_erases_active_vector_and_blocks_shadow(self):
        bridge = self.make_bridge(enabled="yes", shadow="yes", cosmos_write="yes")
        repo = FakeRepo()
        bridge.quantum_buddy_repo_factory = lambda: repo
        command = {
            "action": "revoke", "userId": "owner-opaque-a",
            "etag": repo.etag, "scope": "state",
        }
        code, result = bridge.dispatch(
            "POST", "/api/quantum-buddy/state", AUTH,
            json.dumps(command).encode(),
        )
        self.assertEqual(code, 200, result)
        self.assertFalse(repo.current.state_conditioning_consent)
        self.assertFalse(repo.current.quantum_refresh_consent)
        self.assertFalse(repo.current.qstate_valid)
        self.assertEqual(repo.current.dyn12, tuple([0.0] * 12))
        self.assertEqual(repo.current.state_version, 4)
        shadow, _ = bridge.dispatch(
            "POST", "/api/quantum-buddy/shadow", AUTH,
            json.dumps({
                "userId": "owner-opaque-a", "prompt": "hello",
                "mode": "sim_entangled", "max_tokens": 2, "seed": 67,
            }).encode(),
        )
        self.assertEqual(shadow, 403)
        self.assertEqual(repo.receipts, [])

    def test_revoke_only_quantum_refresh_preserves_opted_in_person_state(self):
        bridge = self.make_bridge(enabled="yes", shadow="yes", cosmos_write="yes")
        repo = FakeRepo()
        bridge.quantum_buddy_repo_factory = lambda: repo
        old_state = repo.current.dyn12
        code, result = bridge.dispatch(
            "POST", "/api/quantum-buddy/state", AUTH,
            json.dumps({
                "action": "revoke", "userId": "owner-opaque-a",
                "etag": repo.etag, "scope": "quantum",
            }).encode(),
        )
        self.assertEqual(code, 200, result)
        self.assertTrue(repo.current.state_conditioning_consent)
        self.assertFalse(repo.current.quantum_refresh_consent)
        self.assertEqual(repo.current.dyn12, old_state)
        self.assertFalse(repo.current.qstate_valid)
        code, _ = bridge.dispatch(
            "POST", "/api/quantum-buddy/state", AUTH,
            json.dumps({
                "action": "revoke", "userId": "owner-opaque-a",
                "etag": "stale-etag", "scope": "both",
            }).encode(),
        )
        self.assertNotEqual(code, 200)
        bad, _ = bridge.dispatch(
            "POST", "/api/quantum-buddy/state", AUTH,
            json.dumps({
                "action": "revoke", "userId": "owner-opaque-a",
                "etag": repo.etag, "scope": "unknown",
            }).encode(),
        )
        self.assertEqual(bad, 400)


    def test_consent_revocation_remains_available_when_buddy_inference_is_off(self):
        bridge = self.make_bridge(enabled="no", shadow="no", cosmos_write="yes")
        repo = FakeRepo()
        bridge.quantum_buddy_repo_factory = lambda: repo
        code, result = bridge.dispatch(
            "POST", "/api/quantum-buddy/state", AUTH,
            json.dumps({
                "action": "revoke", "userId": "owner-opaque-a",
                "etag": repo.etag, "scope": "both",
            }).encode(),
        )
        self.assertEqual(code, 200, result)
        self.assertFalse(repo.current.state_conditioning_consent)
        self.assertFalse(repo.current.quantum_refresh_consent)
        self.assertEqual(repo.current.dyn12, tuple([0.0] * 12))
        self.assertFalse(repo.current.qstate_valid)
        status, _ = bridge.dispatch(
            "POST", "/api/quantum-buddy/shadow", AUTH,
            json.dumps({
                "userId": "owner-opaque-a", "prompt": "hello",
                "mode": "off", "max_tokens": 2, "seed": 67,
            }).encode(),
        )
        self.assertEqual(status, 503)

    def test_inflight_shadow_revocation_rejects_stale_result(self):
        """A shadow result must not escape after consent changes during inference."""
        bridge = self.make_bridge(enabled="yes", shadow="yes", cosmos_write="yes")
        repo = FakeRepo()
        bridge.quantum_buddy_repo_factory = lambda: repo

        def revoke_during_inference(*_args):
            repo.current = BuddyCurrentState.new(
                user_id="owner-opaque-a", dyn12=[0.0] * 12,
                state_version=repo.current.state_version + 1,
                state_conditioning_consent=False,
                quantum_refresh_consent=False,
            )
            repo.etag = '"revoked-etag"'
            return {
                "checkpoint_sha256": "a" * 64,
                "model_weights_changed": False,
                "fresh_hardware_used": False,
                "quantum_advantage_proven": False,
                "logit_l2": 0.15,
                "response_ordinary": "must-not-leak",
                "response_buddy": "must-not-leak",
            }

        bridge.quantum_buddy_shadow_infer = revoke_during_inference
        status, payload = bridge.dispatch(
            "POST", "/api/quantum-buddy/shadow", AUTH,
            json.dumps({
                "userId": "owner-opaque-a", "prompt": "hello",
                "mode": "sim_entangled", "max_tokens": 2, "seed": 67,
            }).encode(),
        )
        self.assertIn(status, (403, 409))
        self.assertNotIn("must-not-leak", json.dumps(payload))
        self.assertEqual(repo.receipts, [])
        self.assertEqual(bridge.dispatch(
            "POST", "/api/chat", AUTH, json.dumps({"text": "hello"}).encode(),
        )[0], 200)
