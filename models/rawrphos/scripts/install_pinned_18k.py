"""Install only the pinned 18K unpromoted experimental release into an empty private model directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tarfile
import tempfile
import urllib.request

from rawrphos.training.checkpoint import load_checkpoint

TAG = "rawrphos-native-experimental-inference-step-00018000-run-36008364848"
BASE = "https://github.com/NavisWORLD/The-beast-box-/releases/download/" + TAG
ARCHIVE_SHA = "ca7da2f59b0f1aba54e2e5928e113d47d4b2da8ca48283db78500d03e39c8ec9"
WEIGHT_SHA = "20932937afb3e0e1b62a4e5f38f92170046ae2928b437dc31b8a37d6538e701e"
MAX_DOWNLOAD = 100 * 1024 * 1024


def verify(path):
    loaded = load_checkpoint(path, expected_checkpoint_sha256=WEIGHT_SHA,
                             load_training_state=False)
    metadata = loaded["metadata"]
    if (metadata["training_steps"] != 18000 or metadata["model_id"] != "rawrphos-native"
            or metadata.get("conversation_steps") != 6000):
        raise ValueError("wrong model release")
    return metadata["checkpoint_sha256"]


def install(destination):
    destination = Path(destination).expanduser()
    if destination.is_symlink() or destination.parent.is_symlink():
        raise ValueError("unsafe model destination")
    if destination.exists():
        if not destination.is_dir():
            raise ValueError("model path is not a directory")
        return verify(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".rawrphos-install-", dir=destination.parent) as temp:
        staging = Path(temp)
        archive_file = staging / "release.tar.gz"
        digest = hashlib.sha256()
        size = 0
        with urllib.request.urlopen(BASE + "/rawrphos-native-step-00018000.tar.gz", timeout=180) as response, archive_file.open("wb") as output:
            if not response.geturl().startswith("https://"):
                raise ValueError("insecure release URL")
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > MAX_DOWNLOAD:
                    raise ValueError("release archive exceeds limit")
                digest.update(block)
                output.write(block)
            output.flush()
            os.fsync(output.fileno())
        if digest.hexdigest() != ARCHIVE_SHA:
            raise ValueError("release archive hash mismatch")
        with tarfile.open(archive_file, mode="r:gz") as archive:
            for member in archive.getmembers():
                name = PurePosixPath(member.name)
                if (name.is_absolute() or ".." in name.parts or not name.parts or
                        name.parts[0] != "step-00018000" or
                        not (member.isfile() or member.isdir())):
                    raise ValueError("unsafe release archive member")
            archive.extractall(staging, filter="data")
        checkpoint = staging / "step-00018000"
        sha = verify(checkpoint)
        os.replace(checkpoint, destination)
        return sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    print(json.dumps({"model_id": "rawrphos-native", "training_steps": 18000,
                      "checkpoint_sha256": install(args.destination)}))


if __name__ == "__main__":
    main()
