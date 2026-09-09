"""Application-layer sealed files using AES-256-GCM.

The core Beast Box runtime stays stdlib-only. Sealed storage requires the
optional extra: ``pip install 'cosmos-beast-box[secure]'``.

Passphrases and keys never enter portable manifests, SQLite, logs, or git.
Sealing is confidentiality for owner-controlled backups and idle stores. It
is not a signature, not a hostile-host boundary, and not a substitute for
revoking credentials. A crash may leave a 0600 plaintext working copy.

Data classes:

- USER CONTENT / PRIVATE / AUDIT — sealed when a passphrase is supplied
- CONFIG — stays host-local (provider JSON, desktop settings)
- CREDENTIAL — never persisted; env only
- AUTHORITY — never persisted; session only
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

MAGIC = b"BBSEAL1\n"
AAD = b"beastbox-sealed-v1"
HEADER_LIMIT = 4096
PLAINTEXT_LIMIT = 256 * 1024 * 1024
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
KEY_LEN = 32
MIN_PASSPHRASE = 8
PASSPHRASE_ENV = "BEASTBOX_SEAL_PASSPHRASE"
SEALED_NAME = "runtime.sqlite3.sealed"
WORKING_NAME = "runtime.sqlite3"


class SealedStorageError(ValueError):
    """Fail-closed sealed-storage contract error."""


class CryptoUnavailable(SealedStorageError):
    """The [secure] extra is not installed."""


class AuthenticationFailed(SealedStorageError):
    """Passphrase mismatch or ciphertext tamper."""


def crypto_available() -> bool:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
    except ImportError:
        return False
    return True


def encryption_status(*, sealed: bool = False) -> dict[str, str]:
    if not crypto_available():
        return {
            "status": "MISSING_SECURE_EXTRA",
            "detail": "Install cosmos-beast-box[secure] for AES-256-GCM sealed backups.",
        }
    if sealed:
        return {
            "status": "ACTIVE",
            "detail": "AES-256-GCM sealed file present. Working SQLite is 0600 plaintext while a process holds it.",
        }
    return {
        "status": "AVAILABLE",
        "detail": "AES-256-GCM sealing is available. This substrate is currently plaintext at rest.",
    }


def require_crypto() -> None:
    if not crypto_available():
        raise CryptoUnavailable(
            "Sealed storage requires the [secure] extra: pip install 'cosmos-beast-box[secure]'"
        )


def passphrase_from_env() -> str:
    value = os.environ.get("BEASTBOX_SEAL_PASSPHRASE", "")
    if not isinstance(value, str) or len(value) < MIN_PASSPHRASE:
        raise SealedStorageError(f"{PASSPHRASE_ENV} must contain at least {MIN_PASSPHRASE} characters")
    return value


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    if not isinstance(passphrase, str) or len(passphrase) < MIN_PASSPHRASE:
        raise SealedStorageError(f"passphrase must contain at least {MIN_PASSPHRASE} characters")
    if b"\x00" in passphrase.encode("utf-8"):
        raise SealedStorageError("passphrase must be UTF-8 text without NUL")
    return hashlib.scrypt(
        passphrase.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=KEY_LEN,
    )


def seal_bytes(plaintext: bytes, passphrase: str) -> bytes:
    require_crypto()
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not isinstance(plaintext, (bytes, bytearray)):
        raise SealedStorageError("plaintext must be bytes")
    if len(plaintext) > PLAINTEXT_LIMIT:
        raise SealedStorageError("plaintext exceeds the 256 MiB sealed limit")
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive_key(passphrase, salt)
    ciphertext = AESGCM(key).encrypt(nonce, bytes(plaintext), AAD)
    header = json.dumps(
        {
            "schema": "beastbox-sealed-v1",
            "kdf": "scrypt",
            "n": SCRYPT_N,
            "r": SCRYPT_R,
            "p": SCRYPT_P,
            "dklen": KEY_LEN,
            "salt": salt.hex(),
            "nonce": nonce.hex(),
            "aead": "AES-256-GCM",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(header) > HEADER_LIMIT:
        raise SealedStorageError("sealed header is oversized")
    return MAGIC + len(header).to_bytes(4, "big") + header + ciphertext


def unseal_bytes(blob: bytes, passphrase: str) -> bytes:
    require_crypto()
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not isinstance(blob, (bytes, bytearray)):
        raise SealedStorageError("sealed blob must be bytes")
    data = bytes(blob)
    if len(data) > PLAINTEXT_LIMIT + HEADER_LIMIT + 128:
        raise SealedStorageError("sealed blob exceeds supported size")
    if not data.startswith(MAGIC):
        raise SealedStorageError("not a Beast Box sealed file")
    body = data[len(MAGIC) :]
    if len(body) < 4:
        raise SealedStorageError("truncated sealed header")
    header_len = int.from_bytes(body[:4], "big")
    if not 1 <= header_len <= HEADER_LIMIT or len(body) < 4 + header_len:
        raise SealedStorageError("invalid sealed header length")
    try:
        header = json.loads(body[4 : 4 + header_len].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SealedStorageError("invalid sealed header") from exc
    required = {"schema", "kdf", "n", "r", "p", "dklen", "salt", "nonce", "aead"}
    if not isinstance(header, dict) or set(header) != required:
        raise SealedStorageError("unsupported sealed header fields")
    if (
        header["schema"] != "beastbox-sealed-v1"
        or header["kdf"] != "scrypt"
        or header["aead"] != "AES-256-GCM"
        or header["n"] != SCRYPT_N
        or header["r"] != SCRYPT_R
        or header["p"] != SCRYPT_P
        or header["dklen"] != KEY_LEN
    ):
        raise SealedStorageError("unsupported sealed algorithm parameters")
    try:
        salt = bytes.fromhex(header["salt"])
        nonce = bytes.fromhex(header["nonce"])
    except (TypeError, ValueError) as exc:
        raise SealedStorageError("invalid sealed salt or nonce") from exc
    if len(salt) != 16 or len(nonce) != 12:
        raise SealedStorageError("invalid sealed salt or nonce length")
    ciphertext = body[4 + header_len :]
    if not ciphertext:
        raise SealedStorageError("missing sealed ciphertext")
    key = _derive_key(passphrase, salt)
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, AAD)
    except InvalidTag as exc:
        raise AuthenticationFailed("sealed file authentication failed") from exc


def _safe_file(path: Path) -> Path:
    supplied = Path(path)
    if ".." in supplied.parts or any(part.is_symlink() for part in (supplied, *supplied.parents)):
        raise SealedStorageError("sealed paths must not traverse parents or symlinks")
    return supplied


def write_sealed_file(path: Path, plaintext: bytes, passphrase: str) -> dict[str, Any]:
    from .runtime_cli import file_sha256

    target = _safe_file(path)
    if target.exists():
        raise SealedStorageError("sealed destination already exists")
    blob = seal_bytes(plaintext, passphrase)
    fd, name = tempfile.mkstemp(prefix=".beast-seal-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(blob)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, 0o600)
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)
    target.chmod(0o600)
    return {"path": str(target), "bytes": target.stat().st_size, "sha256": file_sha256(target)}


def read_sealed_file(path: Path, passphrase: str) -> bytes:
    target = _safe_file(path)
    if not target.is_file() or target.is_symlink():
        raise SealedStorageError("sealed file is missing or a symlink")
    if target.stat().st_size > PLAINTEXT_LIMIT + HEADER_LIMIT + 128:
        raise SealedStorageError("sealed file exceeds supported size")
    return unseal_bytes(target.read_bytes(), passphrase)


def seal_runtime_root(root: Path, passphrase: str, *, remove_plaintext: bool = True) -> dict[str, Any]:
    """Encrypt the closed SQLite file. Caller must close the runtime first."""
    from .runtime_cli import verify_database

    base = _safe_file(Path(root)).absolute()
    database = base / WORKING_NAME
    sealed = base / SEALED_NAME
    if sealed.exists():
        sealed.unlink()
    verify_database(database, standalone=True)
    wal = Path(str(database) + "-wal")
    shm = Path(str(database) + "-shm")
    if wal.exists() and wal.stat().st_size:
        db = sqlite3.connect(database)
        try:
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            db.execute("PRAGMA journal_mode=DELETE")
        finally:
            db.close()
    plaintext = database.read_bytes()
    receipt = write_sealed_file(sealed, plaintext, passphrase)
    if remove_plaintext:
        database.unlink()
        wal.unlink(missing_ok=True)
        shm.unlink(missing_ok=True)
    else:
        database.chmod(0o600)
    return {
        "sealed": True,
        "sealed_path": receipt["path"],
        "sealed_sha256": receipt["sha256"],
        "plaintext_removed": remove_plaintext,
        "authority": "NOT_TRANSFERRED",
        "credentials": "HOST_CONFIGURATION_EXCLUDED",
    }


def unseal_runtime_root(root: Path, passphrase: str) -> dict[str, Any]:
    """Restore a working SQLite file from the sealed idle copy."""
    from .runtime_cli import verify_database

    base = _safe_file(Path(root)).absolute()
    database = base / WORKING_NAME
    sealed = base / SEALED_NAME
    if not sealed.exists():
        return {"unsealed": False, "reason": "no sealed file"}
    plaintext = read_sealed_file(sealed, passphrase)
    if database.exists():
        if database.read_bytes() != plaintext:
            raise SealedStorageError("working database does not match the sealed file")
        database.chmod(0o600)
        checkpoint = verify_database(database, standalone=True)
        return {"unsealed": True, "already_present": True, "system_id": checkpoint["system_id"]}
    fd, name = tempfile.mkstemp(prefix=".beast-unseal-", dir=base)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(plaintext)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, 0o600)
        os.replace(name, database)
    finally:
        Path(name).unlink(missing_ok=True)
    database.chmod(0o600)
    checkpoint = verify_database(database, standalone=True)
    return {
        "unsealed": True,
        "already_present": False,
        "system_id": checkpoint["system_id"],
        "checkpoint_sha256": checkpoint["sha256"],
    }


def maybe_unseal_root(root: Path) -> dict[str, Any]:
    """Open helper: if only a sealed file exists, require BEASTBOX_SEAL_PASSPHRASE."""
    base = Path(root)
    sealed = base / SEALED_NAME
    working = base / WORKING_NAME
    if sealed.exists() and not working.exists():
        return unseal_runtime_root(base, passphrase_from_env())
    return {"unsealed": False, "reason": "working copy present or no sealed file"}


def maybe_seal_root(root: Path) -> dict[str, Any]:
    """Close helper: seal when BEASTBOX_SEAL_PASSPHRASE is a real passphrase."""
    value = os.environ.get("BEASTBOX_SEAL_PASSPHRASE", "")
    if not isinstance(value, str) or len(value) < MIN_PASSPHRASE:
        return {"sealed": False, "reason": "passphrase not configured"}
    working = Path(root) / WORKING_NAME
    if not working.exists():
        return {"sealed": False, "reason": "working database missing"}
    return seal_runtime_root(Path(root), value, remove_plaintext=True)


def export_sealed_snapshot(root: Path, destination: Path, passphrase: str) -> dict[str, Any]:
    """Create a v2 sealed portable bundle. Authority and credentials still do not travel."""
    from . import __version__
    from .portable_state import private_history_check, safe_path
    from .runtime_cli import backup_database, file_sha256, verify_database

    safe_path(root)
    safe_path(destination)
    if destination.exists():
        raise SealedStorageError("portable export requires a new destination directory")
    if not destination.parent.is_dir():
        raise SealedStorageError("portable export parent directory must exist")
    with tempfile.TemporaryDirectory(prefix=".beast-sealed-export-", dir=destination.parent) as temp:
        stage = Path(temp) / "snapshot"
        stage.mkdir(mode=0o700)
        database = stage / WORKING_NAME
        backup_database(root, database)
        db = sqlite3.connect(database)
        try:
            db.execute("PRAGMA journal_mode=DELETE")
        finally:
            db.close()
        database.chmod(0o600)
        private_history_check(database)
        checkpoint = verify_database(database, standalone=True)
        sealed = stage / SEALED_NAME
        write_sealed_file(sealed, database.read_bytes(), passphrase)
        database.unlink()
        manifest = {
            "schema": "beastbox-portable-state-v2",
            "package_version": __version__,
            "checkpoint_schema": "continuity-checkpoint-v1",
            "system_id": checkpoint["system_id"],
            "checkpoint_sha256": checkpoint["sha256"],
            "sequence": checkpoint["sequence"],
            "database": {
                "name": SEALED_NAME,
                "bytes": sealed.stat().st_size,
                "sha256": file_sha256(sealed),
            },
            "authority": "NOT_TRANSFERRED",
            "credentials": "HOST_CONFIGURATION_EXCLUDED",
            "encryption": {
                "status": "ACTIVE",
                "aead": "AES-256-GCM",
                "kdf": "scrypt",
            },
        }
        path = stage / "manifest.json"
        path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        path.chmod(0o600)
        digest = file_sha256(path)
        verify_sealed_snapshot(stage, digest, passphrase)
        for file in (sealed, path):
            with file.open("r+b") as handle:
                os.fsync(handle.fileno())
        if destination.exists():
            raise SealedStorageError("portable destination appeared during export")
        os.rename(stage, destination)
    return {
        "exported": True,
        "schema": "beastbox-portable-state-v2",
        "manifest_sha256": digest,
        "system_id": checkpoint["system_id"],
        "checkpoint_sha256": checkpoint["sha256"],
        "authority": "NOT_TRANSFERRED",
        "credentials": "HOST_CONFIGURATION_EXCLUDED",
        "encryption": "ACTIVE",
    }


def verify_sealed_snapshot(bundle: Path, expected: str, passphrase: str) -> dict[str, Any]:
    import re

    from .portable_state import private_history_check, safe_path
    from .runtime_cli import file_sha256, verify_database

    safe_path(bundle)
    if not re.fullmatch("[0-9a-f]{64}", expected):
        raise SealedStorageError("expected manifest SHA-256 must be 64 lowercase hex characters")
    names = {p.name for p in bundle.iterdir()}
    if names != {"manifest.json", SEALED_NAME}:
        raise SealedStorageError("sealed snapshot must contain exactly manifest.json and runtime.sqlite3.sealed")
    path = bundle / "manifest.json"
    if path.stat().st_size > 16384 or file_sha256(path) != expected:
        raise SealedStorageError("portable manifest SHA-256 mismatch or oversized manifest")
    data = json.loads(path.read_text())
    fields = {
        "schema",
        "package_version",
        "checkpoint_schema",
        "system_id",
        "checkpoint_sha256",
        "sequence",
        "database",
        "authority",
        "credentials",
        "encryption",
    }
    if not isinstance(data, dict) or set(data) != fields or data["schema"] != "beastbox-portable-state-v2":
        raise SealedStorageError("unsupported sealed portable manifest schema or fields")
    if data["authority"] != "NOT_TRANSFERRED" or data["credentials"] != "HOST_CONFIGURATION_EXCLUDED":
        raise SealedStorageError("portable manifest cannot transfer credentials or authority")
    encryption = data["encryption"]
    if not isinstance(encryption, dict) or encryption.get("status") != "ACTIVE" or encryption.get("aead") != "AES-256-GCM":
        raise SealedStorageError("sealed portable manifest encryption field is invalid")
    info = data["database"]
    if not isinstance(info, dict) or set(info) != {"name", "bytes", "sha256"} or info["name"] != SEALED_NAME:
        raise SealedStorageError("invalid sealed database manifest")
    sealed = bundle / SEALED_NAME
    if sealed.stat().st_size != info["bytes"] or file_sha256(sealed) != info["sha256"]:
        raise SealedStorageError("sealed database SHA-256 or size mismatch")
    plaintext = read_sealed_file(sealed, passphrase)
    with tempfile.NamedTemporaryFile(prefix=".beast-verify-", suffix=".sqlite3", delete=False) as handle:
        handle.write(plaintext)
        handle.flush()
        os.fsync(handle.fileno())
        temp = Path(handle.name)
    try:
        temp.chmod(0o600)
        private_history_check(temp)
        checkpoint = verify_database(temp, standalone=True)
    finally:
        temp.unlink(missing_ok=True)
    if any(
        data[key] != checkpoint[other]
        for key, other in (("system_id", "system_id"), ("checkpoint_sha256", "sha256"), ("sequence", "sequence"))
    ):
        raise SealedStorageError("sealed portable checkpoint does not match manifest")
    return {
        "verified": True,
        "schema": "beastbox-portable-state-v2",
        "system_id": checkpoint["system_id"],
        "checkpoint_sha256": checkpoint["sha256"],
        "manifest_sha256": expected,
        "authority": "NOT_TRANSFERRED",
        "encryption": "ACTIVE",
    }


def import_sealed_snapshot(bundle: Path, destination: Path, expected: str, passphrase: str) -> dict[str, Any]:
    from .portable_state import safe_path
    from .runtime_cli import verify_database

    safe_path(destination)
    if destination.exists() or not destination.parent.is_dir():
        raise SealedStorageError("restore requires a new directory in an existing parent")
    receipt = verify_sealed_snapshot(bundle, expected, passphrase)
    plaintext = read_sealed_file(bundle / SEALED_NAME, passphrase)
    with tempfile.TemporaryDirectory(prefix=".beast-sealed-import-", dir=destination.parent) as temp:
        stage = Path(temp) / "state"
        stage.mkdir(mode=0o700)
        database = stage / WORKING_NAME
        database.write_bytes(plaintext)
        database.chmod(0o600)
        verify_database(database, standalone=True)
        with database.open("r+b") as handle:
            os.fsync(handle.fileno())
        if destination.exists():
            raise SealedStorageError("restore destination appeared during import")
        os.rename(stage, destination)
    return {**receipt, "restored": True}
