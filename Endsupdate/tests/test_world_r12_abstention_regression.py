from __future__ import annotations

from beastbox.world_r12 import select_primary_evidence


def test_high_geometry_low_grounding_candidate_must_abstain() -> None:
    """Regression for Actions run 33125920283 / job 98703927258.

    The original mixed conversation routed both deliberately unknown prompts to
    the world namespace.  The failure class is a candidate whose composite R12
    ranking score clears the confidence floor even though direct evidence
    support is weak.  Geometry/recency/integrity may rank candidates; they must
    not by themselves turn a weak lexical match into evidence that exists.
    """
    world = [
        {
            "knowledge_id": 999,
            "score": 0.60,
            "components": {
                "spatial": 0.70,
                "lexical": 0.05,
                "hebbian": 0.0,
                "recency": 1.0,
                "integrity": 1.0,
                "quality": 0.95,
            },
        }
    ]

    selected = select_primary_evidence(
        personal=[],
        world=world,
        confidence_floor=0.56,
        namespace_margin=0.03,
    )

    assert selected["namespace"] == "none"
    assert selected["record"] is None
