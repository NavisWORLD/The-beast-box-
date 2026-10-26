import importlib.util, json, sys, hashlib
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bio_connection_packet as bp
spec = importlib.util.spec_from_file_location("bio_packet_fetch", ROOT / "scripts/bio_packet_fetch.py")
bf = importlib.util.module_from_spec(spec); spec.loader.exec_module(bf)


def packet():
    body = {"schema": bp.SCHEMA, "source": bp.SOURCE, "heartbeat_label": "MEASURED", "honesty": "numbers only",
            "pulse": {"bpm": 72.0, "hrv_rmssd_ms": 40.0, "sqi": 0.9, "beats": 40, "duration_s": 35.0, "fs_hz": 30.0},
            "light": {"red_mean": 200.0, "green_mean": 40.0, "blue_mean": 30.0, "red_ac_dc": 0.01},
            "audio": {"enabled": False, "rms_mean": 0, "zcr": 0, "centroid_norm": 0}, "bio_vector_12": [0.5] * 12,
            "raw_audio_published": False, "raw_video_published": False, "raw_frames_in_packet": False}
    return {**body, "packet_sha256": bp.sha(bp.canonical(body))}


def test_valid_recent_packet_passes_and_command_has_no_secret(tmp_path):
    p = packet()
    got, age = bf.check({"packet": p, "saved_at_ms": 1_000_000}, 3600, now=1_000 + 60)
    assert got == p and age == 60
    cmd = bf.dispatch_command(p, "/tmp/x.json")
    assert "packet_sha12=" + p["packet_sha256"][:12] in cmd and "AccountKey" not in cmd and "ghp_" not in cmd


@pytest.mark.parametrize("env", [None, {}, {"packet": {"x": 1}}])
def test_nothing_or_garbage_is_no_valid_pulse(env):
    with pytest.raises(SystemExit):
        bf.check(env, 3600)


def test_tampered_or_old_or_low_quality_packet_is_refused():
    p = packet()
    with pytest.raises(SystemExit):
        bf.check({"packet": {**p, "pulse": {**p["pulse"], "bpm": 99.0}}, "saved_at_ms": 1_000_000}, 3600, now=1_001)
    with pytest.raises(SystemExit):
        bf.check({"packet": p, "saved_at_ms": 1_000_000}, 3600, now=1_000 + 9999)
    low = {**p, "pulse": {**p["pulse"], "sqi": 0.3}}
    with pytest.raises(SystemExit):
        bf.check({"packet": low, "saved_at_ms": 1_000_000}, 3600, now=1_001)


def test_sas_url_becomes_blob_url_without_changing_the_query():
    sas = "https://acct.blob.core.windows.net/beast-cosmos?sv=2021-08-06&sr=c&sp=rl&sig=SECRETSIG"
    assert bf.sas_blob_url(sas) == "https://acct.blob.core.windows.net/beast-cosmos/owner/bio-packets/latest.json?sv=2021-08-06&sr=c&sp=rl&sig=SECRETSIG"
    assert bf.sas_blob_url(sas.replace("beast-cosmos?", "beast-cosmos/?")).endswith("/beast-cosmos/owner/bio-packets/latest.json?sv=2021-08-06&sr=c&sp=rl&sig=SECRETSIG")


@pytest.mark.parametrize("bad", ["", "http://a.blob.core.windows.net/c?sig=x", "https://a.blob.core.windows.net/c", "https://a.blob.core.windows.net/?sig=x", "https://a.blob.core.windows.net/c/d?sig=x"])
def test_bad_sas_url_is_refused_without_echoing_it(bad):
    with pytest.raises(SystemExit) as e:
        bf.sas_blob_url(bad)
    assert "sig=x" not in str(e.value)


class _Resp:
    def __init__(self, data): self.data = data
    def read(self): return self.data
    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_fetch_sas_reads_envelope_and_missing_blob_is_none(monkeypatch):
    p = packet()
    seen = {}
    def ok(req, timeout=0):
        seen["url"] = req.full_url
        return _Resp(json.dumps({"packet": p, "saved_at_ms": 5}).encode())
    monkeypatch.setattr(bf.urllib.request, "urlopen", ok)
    env = bf.fetch_sas("https://acct.blob.core.windows.net/c?sv=1&sig=S")
    assert env["packet"] == p and seen["url"].startswith("https://acct.blob.core.windows.net/c/owner/bio-packets/latest.json?")
    def missing(req, timeout=0):
        raise bf.urllib.error.HTTPError(req.full_url, 404, "nf", {}, None)
    monkeypatch.setattr(bf.urllib.request, "urlopen", missing)
    assert bf.fetch_sas("https://acct.blob.core.windows.net/c?sv=1&sig=S") is None


def test_fetch_sas_forbidden_fails_closed_and_never_prints_the_url(monkeypatch):
    def deny(req, timeout=0):
        raise bf.urllib.error.HTTPError(req.full_url, 403, "no", {}, None)
    monkeypatch.setattr(bf.urllib.request, "urlopen", deny)
    with pytest.raises(SystemExit) as e:
        bf.fetch_sas("https://acct.blob.core.windows.net/c?sv=1&sig=TOPSECRET")
    assert "403" in str(e.value) and "TOPSECRET" not in str(e.value)


def test_main_prefers_connection_string_then_sas_and_requires_one(monkeypatch, tmp_path):
    for k in ("AZURE_STORAGE_CONNECTION_STRING", "AZURE_STORAGE_CONTAINER_SAS_URL"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(SystemExit):
        bf.main(["--out", str(tmp_path / "o.json")])
    p = packet()
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER_SAS_URL", "https://acct.blob.core.windows.net/c?sv=1&sig=S")
    monkeypatch.setattr(bf, "fetch_sas", lambda u: {"packet": p, "saved_at_ms": bf.time.time() * 1000})
    bf.main(["--out", str(tmp_path / "o.json")])
    assert json.loads((tmp_path / "o.json").read_text())["packet_sha256"] == p["packet_sha256"]
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "AccountName=a;AccountKey=Zm9v")
    called = {}
    monkeypatch.setattr(bf, "fetch", lambda cs, c=None: called.setdefault("cs", {"packet": p, "saved_at_ms": bf.time.time() * 1000}))
    bf.main(["--out", str(tmp_path / "o2.json")])
    assert "cs" in called


def test_check_script_reports_valid_and_no_valid_without_secrets(monkeypatch):
    spec2 = importlib.util.spec_from_file_location("bio_packet_check", ROOT / "scripts/bio_packet_check.py")
    bc = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(bc)
    p = packet()
    sas = "https://acct.blob.core.windows.net/c?sv=1&sig=TOPSECRET"
    monkeypatch.setattr(bc.bf, "fetch_sas", lambda u: {"packet": p, "saved_at_ms": bc.bf.time.time() * 1000})
    r = bc.result(env_vars={"AZURE_STORAGE_CONTAINER_SAS_URL": sas})
    assert r["valid"] and r["sha12"] == p["packet_sha256"][:12] and r["bpm"] == 72.0
    monkeypatch.setattr(bc.bf, "fetch_sas", lambda u: None)
    r = bc.result(env_vars={"AZURE_STORAGE_CONTAINER_SAS_URL": sas})
    assert r["valid"] is False and "no valid pulse" in r["reason"] and "TOPSECRET" not in json.dumps(r)
    r = bc.result(env_vars={})
    assert r["valid"] is False
    monkeypatch.setattr(bc.bf, "fetch_sas", lambda u: {"packet": p, "saved_at_ms": 1})
    assert bc.result(env_vars={"AZURE_STORAGE_CONTAINER_SAS_URL": sas})["valid"] is False  # too old
