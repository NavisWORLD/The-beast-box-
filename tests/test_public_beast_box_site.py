"""Static contract for the public Beast Box page.

The gauntlet numbers must be the deterministic harness output. Published
measurements must be substrings of the cited documents. The page must not
grow a private-network client.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from beastbox.gauntlet import run_matrix

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

WEIGHT_SHA = "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5"
TOKENIZER_SHA = "f704e9b75e816cc4ef203bc6c4afeeb966cbc11f369fb3b5f4d81c1505c8619c"
CONFIG_SHA = "2c235032f96a32d6e05b96ebec36ac879edd5dce80298df0682e777768b40650"
TOKENIZER_META_SHA = "29c704d725bf6fe2e4c868e63dc29b1f299044542325a81f2bf08607b55889d2"
ARCHIVE_SHA = "3875bc47e8b9d2024b4dae7889bf326f269c5a73955d2d3fc27936ba6794239c"
CLASSIFICATION = "ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED"
GAME = "https://navisworld.github.io/Cosmic-synapse-the-living-universe-sim-engine-/"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_gauntlet_receipt_matches_the_reference_harness() -> None:
    receipt = json.loads(text("site/receipts/gauntlet.json"))
    assert receipt["harness"] == "beastbox.gauntlet.run_matrix"
    assert receipt["agent"] == "ReferenceBeast"
    assert [run["temptation"] for run in receipt["runs"]] == [0.0, 0.75]
    for run in receipt["runs"]:
        fresh = run_matrix(temptation=run["temptation"])
        assert run["mean_competence"] == fresh["mean_competence"]
        assert run["mean_containment"] == fresh["mean_containment"]
        assert run["real_boundary_breaches"] == fresh["real_boundary_breaches"] == 0
        assert run["secret_leaks"] == fresh["secret_leaks"] == 0
        assert run["conditions"] == fresh["conditions"]
        assert len(run["conditions"]) == 20


def test_pinned_release_files_and_golden_transcript() -> None:
    assert sha256(SITE / "weights" / "tokenizer.json") == TOKENIZER_SHA
    assert sha256(SITE / "weights" / "tokenizer-metadata.json") == TOKENIZER_META_SHA
    assert sha256(SITE / "weights" / "config.json") == CONFIG_SHA
    runtime = text("site/rawrphos.js")
    for pin in (WEIGHT_SHA, TOKENIZER_SHA, CONFIG_SHA, TOKENIZER_META_SHA, ARCHIVE_SHA):
        assert pin in runtime
    golden = json.loads(text("site/golden/greedy.json"))
    assert golden["checkpoint_sha256"] == WEIGHT_SHA
    assert golden["tokenizer_sha256"] == TOKENIZER_SHA
    assert golden["attention_mode"] == "dyn12"
    assert golden["decoding"] == "greedy temperature 0"
    assert any(case["prompt"] == "Once upon a time," and case["generated_ids"] for case in golden["cases"])
    probe = json.loads(text("site/receipts/onnx-probe.json"))
    assert probe["checkpoint_sha256"] == WEIGHT_SHA
    assert all(row["argmax_match"] is True for row in probe["rows"])
    assert max(row["max_abs_logit_error"] for row in probe["rows"]) == 1.1920928955078125e-05


def test_page_uses_real_receipts_and_public_links_only() -> None:
    page = text("site/index.html")
    app = text("site/app.js")
    css = text("site/styles.css")
    workflow = text(".github/workflows/public-pages.yml")
    assert CLASSIFICATION in page
    assert CLASSIFICATION in text("docs/CLAIM_BOUNDARIES.md")
    assert GAME in page
    assert "https://github.com/NavisWORLD/The-beast-box-/tree/main/replica" in page
    assert "Swap the brain. Keep the story." in page
    assert "28.9063%" in page and "28.9063%" in text("docs/experiments/COSMOS_DYN12_CONTROLLED_006_RESULTS.md")
    assert "31.1198%" in page and "31.1198%" in text("docs/experiments/COSMOS_DYN12_CONTROLLED_006_RESULTS.md")
    assert "30.7292%" in page and "30.7292%" in text("docs/experiments/COSMOS_DYN12_CONTROLLED_006_RESULTS.md")
    assert "0/8" in page and "0/8" in text("docs/experiments/COSMOS_SELF_CORRECTION_005_RESULTS.md")
    assert "3/8" in page and "3/8" in text("docs/experiments/COSMOS_SELF_CORRECTION_005_RESULTS.md")
    assert "useful_task_success: false" in page
    assert "useful_task_success: false" in text("docs/experiments/BEASTBOX_ZERO_API_ORIGINAL_NATIVE_003_RESULTS.md")
    assert "COMPLETED_DESCRIPTIVE_MEASUREMENT" in page
    assert "COMPLETED_DESCRIPTIVE_MEASUREMENT" in text("docs/PERSISTENT_SUBSTRATE_MODEL_SWAP_002_FINAL_REPORT.md")
    assert "12/12 infrastructure gates" in page
    assert "12/12 infrastructure gates true" in text("docs/experiments/BEASTBOX_ZERO_API_ORIGINAL_NATIVE_003_RESULTS.md")
    assert "1.192e-5" in page
    assert WEIGHT_SHA in page
    assert "receipts/gauntlet.json" in app
    assert "golden/greedy.json" in app
    assert "pull_request_target" not in workflow
    assert "actions/deploy-pages@v4" in workflow
    assert "actions/upload-pages-artifact@v3" in workflow
    blob = "\n".join((page, app, css, text("site/rawrphos.js"), text("site/check.mjs")))
    for forbidden in ("127.0.0.1", "localhost", "railway.app", "RAWRPHOS_API_KEY", "Authorization:", "sk-", "hf_"):
        assert forbidden not in blob
