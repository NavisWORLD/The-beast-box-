"""Install only the pinned public 14K release into an empty private model directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tarfile
import tempfile
import urllib.request

from rawrphos.training.checkpoint import load_checkpoint

TAG = "rawrphos-native-conversation-step-00014000-run-35951509482"
BASE = "https://github.com/NavisWORLD/The-beast-box-/releases/download/" + TAG
ARCHIVE_SHA = "3875bc47e8b9d2024b4dae7889bf326f269c5a73955d2d3fc27936ba6794239c"
WEIGHT_SHA = "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5"
MAX_DOWNLOAD = 100 * 1024 * 1024


def verify(path):
    loaded = load_checkpoint(path, expected_checkpoint_sha256=WEIGHT_SHA,
                             load_training_state=False)
    metadata = loaded["metadata"]
    if (metadata["training_steps"] != 14000 or metadata["model_id"] != "rawrphos-native"
            or metadata.get("conversation_steps") != 2000):
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
        with urllib.request.urlopen(BASE + "/rawrphos-native-step-00014000.tar.gz", timeout=180) as response, archive_file.open("wb") as output:
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
                        name.parts[0] != "step-00014000" or
                        not (member.isfile() or member.isdir())):
                    raise ValueError("unsafe release archive member")
            archive.extractall(staging, filter="data")
        checkpoint = staging / "step-00014000"
        sha = verify(checkpoint)
        os.replace(checkpoint, destination)
        return sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    print(json.dumps({"model_id": "rawrphos-native", "training_steps": 14000,
                      "checkpoint_sha256": install(args.destination)}))


if __name__ == "__main__":
    main()
