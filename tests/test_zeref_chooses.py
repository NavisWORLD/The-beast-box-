import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "scripts/zeref_chooses.py").read_text()

def test_no_randomness_and_get_only():
    assert "import random" not in SRC and "Math.random" not in SRC
    assert 'method="GET"' in SRC and "POST" not in SRC and "data=" not in SRC

def test_allowlist_only():
    allow = re.search(r"ALLOW = \((.*?)\)\n", SRC, re.S).group(1)
    hosts = set(re.findall(r"https://([a-z.]+)/", allow))
    assert hosts <= {"simple.wikipedia.org", "en.wikipedia.org", "www.gutenberg.org", "en.wikisource.org", "commons.wikimedia.org"}

def test_x_teacher_strips_handles_and_links():
    import sys; sys.path.insert(0, str(ROOT / "scripts"))
    from zeref_chooses import clean
    out = clean("Thanks @someone_else see https://t.co/abc mail a@b.co call +1 (555) 123-4567 ok")
    assert "@" not in out and "http" not in out and "555" not in out

def test_not_wired_into_pin_or_gate():
    for f in ("scripts/zeref_continuation_006.py", ".github/workflows/zeref-continuous-learning-006.yml"):
        p = ROOT / f
        if p.is_file(): assert "zeref_chooses" not in p.read_text()
