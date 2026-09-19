from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

from .hashutil import canonical_json, sha256_obj


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(out[:length])


def xor_seal(plaintext: bytes, key: bytes, nonce: bytes) -> bytes:
    stream = _keystream(key, nonce, len(plaintext))
    return bytes(a ^ b for a, b in zip(plaintext, stream))


@dataclass
class SealedShard:
    schema: str
    public_state: dict[str, Any]
    ciphertext_hex: str
    nonce_hex: str
    key_commitment: str
    shard_plaintext_sha256: str
    state_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "public_state": self.public_state,
            "ciphertext_hex": self.ciphertext_hex,
            "nonce_hex": self.nonce_hex,
            "key_commitment": self.key_commitment,
            "shard_plaintext_sha256": self.shard_plaintext_sha256,
            "state_id": self.state_id,
        }


def split_state(state: dict[str, Any], required_fields: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    required = set(required_fields)
    shard = {k: state[k] for k in state if k in required}
    public = {k: state[k] for k in state if k not in required}
    if not shard:
        raise ValueError("required_fields did not select any state")
    return public, shard


def prepare_required_shard(state: dict[str, Any], required_fields: list[str], key_bytes: int = 16) -> tuple[SealedShard, bytes]:
    """Create a mission-critical sealed shard and ephemeral transport key.

    The XOR construction is an experimental reversible sealer for the transport
    benchmark, not a replacement for authenticated production cryptography.
    """
    if key_bytes < 1:
        raise ValueError("key_bytes must be positive")
    public, shard = split_state(state, required_fields)
    plaintext = canonical_json(shard).encode("utf-8")
    key = os.urandom(key_bytes)
    nonce = os.urandom(16)
    ciphertext = xor_seal(plaintext, key, nonce)
    artifact = SealedShard(
        schema="beastbox.required-shard.v1",
        public_state=public,
        ciphertext_hex=ciphertext.hex(),
        nonce_hex=nonce.hex(),
        key_commitment=hashlib.sha256(key).hexdigest(),
        shard_plaintext_sha256=hashlib.sha256(plaintext).hexdigest(),
        state_id=sha256_obj(state),
    )
    return artifact, key


def recover_required_shard(artifact: SealedShard | dict[str, Any], key: bytes) -> dict[str, Any]:
    if isinstance(artifact, dict):
        artifact = SealedShard(**artifact)
    if hashlib.sha256(key).hexdigest() != artifact.key_commitment:
        raise ValueError("key commitment mismatch")
    plaintext = xor_seal(bytes.fromhex(artifact.ciphertext_hex), key, bytes.fromhex(artifact.nonce_hex))
    if hashlib.sha256(plaintext).hexdigest() != artifact.shard_plaintext_sha256:
        raise ValueError("shard hash mismatch")
    shard = json.loads(plaintext.decode("utf-8"))
    state = dict(artifact.public_state)
    state.update(shard)
    if sha256_obj(state) != artifact.state_id:
        raise ValueError("reconstructed state hash mismatch")
    return state


def key_to_chunks(key: bytes, chunk_bits: int = 8) -> list[str]:
    bits = "".join(f"{b:08b}" for b in key)
    if chunk_bits <= 0 or len(bits) % chunk_bits:
        raise ValueError("chunk_bits must divide key bit length")
    return [bits[i : i + chunk_bits] for i in range(0, len(bits), chunk_bits)]


def chunks_to_key(chunks: list[str]) -> bytes:
    bits = "".join(chunks)
    if len(bits) % 8 or any(b not in "01" for b in bits):
        raise ValueError("invalid bit chunks")
    return bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits), 8))


def continuity_score(state: dict[str, Any], required_fields: list[str]) -> float:
    if not required_fields:
        return 1.0
    present = sum(1 for field in required_fields if state.get(field) not in (None, "", [], {}))
    return present / len(required_fields)
