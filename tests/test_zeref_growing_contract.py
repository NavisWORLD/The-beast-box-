"""Contract: the growing branch and the daily reader never touch the pin, its gate or its promotion."""
import re, sys
from pathlib import Path
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))

def test_growing_workflow_is_scheduled_and_never_touches_the_pin():
    w = (R / ".github/workflows/zeref-growing.yml").read_text()
    assert "cron: '47 */4 * * *'" in w
    assert "release delete" not in w and "--auto" not in w
    assert "rawrphos-public-pin.json'))['promotion']['release_tag']" in w  # read only
    assert not re.search(r"(>|tee|write_text).*rawrphos-public-pin", w)
    assert "zeref-growing-%03d" in w and "--prerelease" in w

def test_growing_script_is_ungated_labelled_and_logs_every_row():
    s = (R / "scripts/zeref_growing.py").read_text()
    assert "Growing Zeref · not the pin" in s and '"is_public_pin": False' in s and '"production_promoted": False' in s
    assert "ANCHOR_CHAT, ANCHOR_READ = 0.5, 0.1" in s
    assert "rows-log.jsonl" in s and '"license"' in s and "row_sha256" in s
    assert "import random" not in s and "time.time" not in s
    assert "rawrphos-public-pin" not in s

def test_reader_is_daily_licensed_and_filtered():
    w = (R / ".github/workflows/zeref-reader.yml").read_text()
    assert "cron: '23 13 * * *'" in w and "build_knowledge_bank.py --check" in w
    import zeref_reader as z
    assert z.ALLOWED_LICENSES == {"CC BY-SA 4.0", "CC BY 2.5", "Public domain (USA)"}
    r = z.row("simplewiki", "Moon", "  The Moon  is round. ", "https://simple.wikipedia.org/w/index.php?oldid=1", 1)
    assert r["text"] == "The Moon is round." and len(r["sha256"]) == 64 and r["license"] == "CC BY-SA 4.0"
    paras, nxt, total = z.gutenberg_paragraphs("x\n*** START OF X ***\n\nCHAPTER I CHAPTER II\n\n" + ("word " * 30) + "\n\n" + ("more " * 30) + "\n*** END OF X", 0, 1)
    assert paras == [("word " * 30).strip()] and nxt == 1 and total == 2

def test_saved_reading_rows_carry_source_licence_and_sha():
    import hashlib, json
    for f in (R / "evidence/zeref-read-001").glob("*.jsonl"):
        for l in f.read_text().splitlines():
            r = json.loads(l)
            assert r["source"].startswith("https://") and r["license"] and r["revision_id"]
            assert hashlib.sha256(r["text"].encode()).hexdigest() == r["sha256"]
