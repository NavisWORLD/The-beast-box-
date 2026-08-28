from pathlib import Path


def test_retired_talk006_workflow_stays_out_of_active_tree():
    assert not Path('.github/workflows/zeref-talk006-alien-v2-train.yml').exists()
    text = Path('.github/workflows/cosmos-final-organism-ignition.yml').read_text(encoding="utf-8")
    assert "COSMOS FINAL ORGANISM - IGNITE ZEREF" in text
    assert "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425" in text
