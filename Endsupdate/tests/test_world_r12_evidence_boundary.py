from beastbox.world_r12 import select_primary_evidence


def test_favorable_r12_score_cannot_manufacture_evidence_existence() -> None:
    """Composite/R12 rank score cannot bypass the direct-evidence floor."""
    personal = [
        {
            "memory_id": 1,
            "score": 1.0,
            "components": {
                "spatial": 1.0,
                "recency": 1.0,
                "lexical": 0.0,
                "hebbian": 0.0,
                "integrity": 0.0,
                "quality": 1.0,
            },
        }
    ]
    world = [
        {
            "knowledge_id": 1,
            "score": 1.0,
            "components": {
                "spatial": 1.0,
                "recency": 1.0,
                "lexical": 0.0,
                "hebbian": 0.0,
                "integrity": 0.0,
                "quality": 0.0,
            },
        }
    ]

    selected = select_primary_evidence(
        personal=personal,
        world=world,
        confidence_floor=0.56,
    )

    assert selected["namespace"] == "none"
    assert selected["record"] is None
    assert selected["personal_score"] == 1.0
    assert selected["world_score"] == 1.0
    assert selected["personal_evidence_confidence"] == 0.0
    assert selected["world_evidence_confidence"] == 0.0
