#!/usr/bin/env python3
"""Stage the pinned public RAWRPHOS 14K inference files for the static site.

The archive is the GitHub release checked by models/rawrphos/scripts/install_pinned_14k.py.
Only the inference files are copied. Optimizer state is not published on the site.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import tarfile
import urllib.request
from pathlib import Path, PurePosixPath

TAG = "rawrphos-native-conversation-step-00014000-run-35951509482"
ARCHIVE_URL = f"https://github.com/NavisWORLD/The-beast-box-/releases/download/{TAG}/rawrphos-native-step-00014000.tar.gz"
ARCHIVE_SHA256 = "3875bc47e8b9d2024b4dae7889bf326f269c5a73955d2d3fc27936ba6794239c"
MAX_DOWNLOAD = 100 * 1024 * 1024
EXPECTED = {
    "model.safetensors": "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5",
    "tokenizer.json": "f704e9b75e816cc4ef203bc6c4afeeb966cbc11f369fb3b5f4d81c1505c8619c",
    "tokenizer-metadata.json": "29c704d725bf6fe2e4c868e63dc29b1f299044542325a81f2bf08607b55889d2",
    "config.json": "2c235032f96a32d6e05b96ebec36ac879edd5dce80298df0682e777768b40650",
}
ARCHIVE_MEMBERS = {
    "model.safetensors": "step-00014000/model.safetensors",
    "tokenizer.json": "step-00014000/tokenizer/tokenizer.json",
    "tokenizer-metadata.json": "step-00014000/tokenizer/metadata.json",
    "config.json": "step-00014000/config.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def already_staged(destination: Path) -> bool:
    for name, expected in EXPECTED.items():
        path = destination / name
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            return False
    return True


def stage(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if any((destination / name).is_symlink() for name in EXPECTED):
        raise ValueError("refusing to write through a symlink")
    if already_staged(destination):
        print("pinned RAWRPHOS inference files already match")
        return
    payload = bytearray()
    with urllib.request.urlopen(ARCHIVE_URL, timeout=180) as response:
        if not response.geturl().startswith("https://"):
            raise ValueError("insecure release URL")
        while block := response.read(1024 * 1024):
            if len(payload) + len(block) > MAX_DOWNLOAD:
                raise ValueError("release archive exceeds limit")
            payload.extend(block)
    archive_sha = hashlib.sha256(payload).hexdigest()
    if archive_sha != ARCHIVE_SHA256:
        raise ValueError("release archive hash mismatch")
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        members = {member.name: member for member in archive.getmembers()}
        for name, member_name in ARCHIVE_MEMBERS.items():
            member = members.get(member_name)
            path = PurePosixPath(member_name)
            if (member is None or not member.isfile() or path.is_absolute() or ".." in path.parts
                    or member.size > MAX_DOWNLOAD):
                raise ValueError("unsafe or missing release member: " + member_name)
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError("missing release member: " + member_name)
            data = extracted.read()
            if hashlib.sha256(data).hexdigest() != EXPECTED[name]:
                raise ValueError("release file hash mismatch: " + name)
            target = destination / name
            target.write_bytes(data)
    if not already_staged(destination):
        raise ValueError("staged files failed the final hash check")
    print("staged pinned RAWRPHOS inference files")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=Path("site/weights"))
    args = parser.parse_args()
    stage(args.destination)


if __name__ == "__main__":
    main()
