"""Real short-lived CA-validated HTTPS authority process; no production secrets.

The CI fixture uses a separate process and DB directory **under the same OS
user**, so it proves transport, CAS, crash and restart behavior, not actual
production off-host custody or independently administered authentication.
"""
from __future__ import annotations

import ipaddress
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from beastbox.durable import DurableRuntime
from beastbox.providers import ReferenceTextProvider
from beastbox.remote_anchor import HTTPSAnchorClient
from beastbox.trusted_anchor import AnchorMismatch, ContinuityTip

TOKEN = "operator-test-only-32-plus-byte-bearer-token-2026-never-production"


@pytest.fixture
def ephemeral_tls(tmp_path: Path):
    """Create a local-only CA and host certificate without repository secrets."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Finisher local test root")])
    ca = (x509.CertificateBuilder()
          .subject_name(name).issuer_name(name).public_key(key.public_key())
          .serial_number(x509.random_serial_number())
          .not_valid_before(now - timedelta(hours=1))
          .not_valid_after(now + timedelta(days=2))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .sign(key, hashes.SHA256()))
    host_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    host = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    cert = (x509.CertificateBuilder()
            .subject_name(host).issuer_name(name).public_key(host_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(hours=1))
            .not_valid_after(now + timedelta(days=2))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName(
                [x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(key, hashes.SHA256()))
    secure = tmp_path / "operator-only"
    secure.mkdir()
    cafile, certfile, keyfile, tokenfile = (
        secure / "ca.pem", secure / "server.pem", secure / "server.key", secure / "bearer.txt"
    )
    cafile.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    keyfile.write_bytes(host_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    tokenfile.write_text(TOKEN + "\n", encoding="ascii")
    keyfile.chmod(0o600)
    tokenfile.chmod(0o600)
    return cafile, certfile, keyfile, tokenfile, secure / "witness.sqlite3"


@contextmanager
def _serve(files: tuple[Path, Path, Path, Path, Path], *, force_port: int | None = None):
    ca, cert, key, tokenfile, db = files
    if force_port is None:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
    else:
        port = force_port
    server = subprocess.Popen(
        [sys.executable, "-u", "-m", "beastbox.anchor_service",
         "--db", str(db), "--cert", str(cert), "--key", str(key),
         "--token-file", str(tokenfile), "--bind", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    client = HTTPSAnchorClient(
        "https://127.0.0.1:" + str(port), api_token=TOKEN, ca_file=ca,
        timeout_seconds=1.0,
    )
    try:
        ready = False
        for _ in range(60):
            if server.poll() is not None:
                raise AssertionError("anchor service exited during startup: " + server.stderr.read())
            try:
                assert client.latest("readiness-probe") is None
                ready = True
                break
            except AnchorMismatch:
                time.sleep(0.1)
        assert ready, "real TLS anchor service did not become ready"
        yield client, port, server
    finally:
        if server.poll() is None:
            server.terminate()
        try:
            server.wait(timeout=6)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=6)
        if server.stderr:
            server.stderr.close()


def test_remote_tls_actual_process_monotonic_cas_and_restart(ephemeral_tls):
    with _serve(ephemeral_tls) as (client, port, _):
        ident = "finisher-offprocess-1"
        genesis = ContinuityTip(ident, 0, "a" * 64, "b" * 64)
        next_tip = ContinuityTip(ident, 1, "c" * 64, "d" * 64)
        assert client.latest(ident) is None
        client.advance(None, genesis)
        assert client.latest(ident) == genesis
        with pytest.raises(AnchorMismatch, match="rejected"):
            client.advance(None, genesis)
        client.advance(genesis, next_tip)
        assert client.latest(ident) == next_tip
        with pytest.raises(AnchorMismatch, match="rejected"):
            client.advance(genesis, ContinuityTip(ident, 1, "e" * 64, "f" * 64))
    with _serve(ephemeral_tls, force_port=port) as (resumed, _, _):
        assert resumed.latest(ident) == next_tip
        with pytest.raises(AnchorMismatch, match="rejected"):
            resumed.advance(None, genesis)


def test_real_tls_remote_authority_blocks_coherent_local_rollback(ephemeral_tls, tmp_path: Path):
    root = tmp_path / "untrusted-runtime"
    with _serve(ephemeral_tls) as (client, _, _):
        runtime = DurableRuntime(root, ReferenceTextProvider(), anchor_authority=client)
        try:
            runtime.respond("An independently witnessed ledger progression.")
            assert client.latest(runtime.system_id).sequence == 1
        finally:
            runtime.close()
        # This same-user CI fixture directly rolls the *local runtime* to a
        # self-consistent old snapshot; operator witness database is untouched.
        with sqlite3.connect(root / "runtime.sqlite3") as db:
            db.execute("DELETE FROM continuity WHERE sequence > 0")
            db.execute("DELETE FROM memories")
            db.execute("DELETE FROM associations")
            db.execute("DELETE FROM salience")
        local = DurableRuntime(root, ReferenceTextProvider())
        try:
            assert local.inspect()["sequence"] == 0
        finally:
            local.close()
        with pytest.raises(AnchorMismatch, match="external authority disagrees"):
            DurableRuntime(root, ReferenceTextProvider(), anchor_authority=client)


def test_remote_authentication_wrong_ca_and_network_failure_fail_closed(ephemeral_tls, tmp_path: Path):
    ca, _, _, _, _ = ephemeral_tls
    with _serve(ephemeral_tls) as (client, port, server):
        unapproved = HTTPSAnchorClient(
            "https://127.0.0.1:" + str(port),
            api_token="unauthorized-token-32-characters-long-abc123",
            ca_file=ca,
        )
        with pytest.raises(AnchorMismatch, match="unavailable or rejected"):
            unapproved.latest("readiness-probe")
        with pytest.raises(ValueError, match="HTTPS"):
            HTTPSAnchorClient("http://127.0.0.1:" + str(port), api_token=TOKEN, ca_file=ca)
        wrong_ca = tmp_path / "incorrect-ca.pem"
        wrong_ca.write_bytes(b"")
        with pytest.raises((OSError, ValueError)):
            HTTPSAnchorClient("https://127.0.0.1:" + str(port), api_token=TOKEN, ca_file=wrong_ca)
        # An unavailable service cannot fall back to local or silently reset.
        server.terminate()
        server.wait(timeout=6)
        with pytest.raises(AnchorMismatch, match="unavailable"):
            client.latest("readiness-probe")


def test_service_rejects_malformed_commands_and_divergent_system_id(ephemeral_tls):
    with _serve(ephemeral_tls) as (_, port, _):
        cafile = ephemeral_tls[0]
        import ssl
        context = ssl.create_default_context(cafile=str(cafile))
        url = "https://127.0.0.1:" + str(port) + "/v1/anchors/owner/advance"
        def send(body: bytes, *, auth: str = TOKEN):
            request = urllib.request.Request(
                url, data=body,
                headers={"Authorization": "Bearer " + auth, "Content-Type": "application/json"},
                method="POST",
            )
            try:
                urllib.request.urlopen(request, context=context, timeout=4)
            except urllib.error.HTTPError as exc:
                return exc.code
            raise AssertionError("server accepted invalid command")
        assert send(b'{"new":{"system_id":"other","sequence":0,"sha256":"' +
                    b"a" * 64 + b'","memory_digest":"' + b"b" * 64 +
                    b'"},"expected":null}') == 400
        assert send(b"not-json") == 400
        assert send(b'{"expected":null}', auth="invalid-token") == 401
        assert send(b"x" * 4097) == 400


def test_existing_unanchored_store_does_not_autoenroll_remote(ephemeral_tls, tmp_path: Path):
    root = tmp_path / "already-existing-local-runtime"
    unanchored = DurableRuntime(root, ReferenceTextProvider())
    unanchored.respond("This local history predates the independent service.")
    unanchored.close()
    with _serve(ephemeral_tls) as (client, _, _):
        with pytest.raises(AnchorMismatch, match="missing independently retained"):
            DurableRuntime(root, ReferenceTextProvider(), anchor_authority=client)
