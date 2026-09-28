"""Public SciFact transient source retry never weakens frozen scientific inputs."""
from __future__ import annotations

import hashlib
import urllib.error

import pytest

from scripts import semantic_real_eval as evaluation


def _pin(monkeypatch, data):
    monkeypatch.setattr(evaluation, "DATASET_MD5", hashlib.md5(data).hexdigest())
    monkeypatch.setattr(evaluation, "DATASET_SHA256", hashlib.sha256(data).hexdigest())


def test_explicit_cache_requires_the_exact_two_verified_digests(tmp_path, monkeypatch):
    archive = tmp_path / "scifact.zip"
    archive.write_bytes(b"test-only synthetic archive")
    monkeypatch.setenv("BEASTBOX_SCIFACT_VERIFIED_CACHE", str(archive))
    monkeypatch.setattr(evaluation.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("network called")))
    _pin(monkeypatch, archive.read_bytes())
    assert evaluation.load_verified_scifact_archive() == archive.read_bytes()
    archive.write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        evaluation.load_verified_scifact_archive()


def test_symlink_cache_fails_before_io(tmp_path, monkeypatch):
    original = tmp_path / "archive"
    original.write_bytes(b"arbitrary")
    link = tmp_path / "symlink"
    link.symlink_to(original)
    monkeypatch.setenv("BEASTBOX_SCIFACT_VERIFIED_CACHE", str(link))
    with pytest.raises(RuntimeError, match="symlink"):
        evaluation.load_verified_scifact_archive()


def test_retries_only_transient_502_and_preserves_exact_data(monkeypatch):
    monkeypatch.delenv("BEASTBOX_SCIFACT_VERIFIED_CACHE", raising=False)
    data = b"synthetic identical archive"
    _pin(monkeypatch, data)
    calls = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, length):
            assert length == 12 * 1024 * 1024 + 1
            return data
    def urlopen(request, timeout):
        calls.append(timeout)
        if len(calls) < 3:
            raise urllib.error.HTTPError(request.full_url, 502, "transient", None, None)
        return Response()
    monkeypatch.setattr(evaluation.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(evaluation.time, "sleep", lambda n: None)
    assert evaluation.load_verified_scifact_archive() == data
    assert calls == [45, 45, 45]


def test_permanent_404_fails_without_retry_or_substitution(monkeypatch):
    monkeypatch.delenv("BEASTBOX_SCIFACT_VERIFIED_CACHE", raising=False)
    attempts = []
    def urlopen(request, timeout):
        attempts.append(1)
        raise urllib.error.HTTPError(request.full_url, 404, "absent", None, None)
    monkeypatch.setattr(evaluation.urllib.request, "urlopen", urlopen)
    with pytest.raises(RuntimeError, match="rejected"):
        evaluation.load_verified_scifact_archive()
    assert len(attempts) == 1


def test_three_failed_502_preserved_not_reported_as_benchmark(monkeypatch):
    monkeypatch.delenv("BEASTBOX_SCIFACT_VERIFIED_CACHE", raising=False)
    attempts = []
    def urlopen(request, timeout):
        attempts.append(1)
        raise urllib.error.HTTPError(request.full_url, 502, "unavailable", None, None)
    monkeypatch.setattr(evaluation.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(evaluation.time, "sleep", lambda n: None)
    with pytest.raises(RuntimeError, match="unavailable after three attempts"):
        evaluation.load_verified_scifact_archive()
    assert len(attempts) == 3
