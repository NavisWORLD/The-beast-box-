"""Cosmos service metadata regression: actual SDK reads contain system fields."""
import copy
import pytest

from beastbox.quantum_buddy.cosmos_repository import CosmosBuddyRepository
from beastbox.quantum_buddy.state import canonical_vector_sha256


class HttpConflict(Exception):
    status_code = 409


class SDKShapedHistory:
    def __init__(self):
        self.documents = {}

    def create_item(self, *, body):
        if body["id"] in self.documents:
            raise HttpConflict()
        self.documents[body["id"]] = {
            **copy.deepcopy(body), "_rid": "sdk-generated",
            "_etag": '"sdk-etag-1"', "_ts": 1700000000, "_self": "cosmos-path",
            "_attachments": "attachments/",
        }
        return copy.deepcopy(self.documents[body["id"]])

    def read_item(self, *, item, partition_key):
        doc = self.documents[item]
        assert doc["userId"] == partition_key
        return copy.deepcopy(doc)


def test_append_history_duplicate_is_idempotent_with_cosmos_system_metadata():
    history = SDKShapedHistory()
    repo = CosmosBuddyRepository(current_container=object(), history_container=history)
    receipt = {
        "userId": "opaque-a",
        "sourceStateSha256": canonical_vector_sha256([0.1] * 12),
        "status": "ACCEPTED", "mode": "matched_classical",
        "sourceClass": "classical",
        "resultSha256": "f" * 64,
        "latencyMs": 1.25,
    }
    receipt_id = repo.append_history(receipt)
    assert repo.append_history(copy.deepcopy(receipt)) == receipt_id
    assert len(history.documents) == 1
