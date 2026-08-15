from pathlib import Path

from beastbox.autonomy.native_stack import NativeStackLock, verify_native_stack


REPO_ID = "phera-ra/QC67_cosmo"
REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"
GGUF_PATH = "weights/cosmos-cst.gguf"
GGUF_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"


def make_lock(*, entrypoint: str = "Genesis_Engine/soul/awaken.py") -> NativeStackLock:
    return NativeStackLock(
        repo_id=REPO_ID,
        revision=REVISION,
        gguf_path=GGUF_PATH,
        gguf_sha256=GGUF_SHA256,
        entrypoint=entrypoint,
        required_files={
            "Genesis_Engine/genesis.py": "0" * 64,
            "Genesis_Engine/soul/awaken.py": "0" * 64,
        },
    )


def test_native_stack_lock_rejects_missing_snapshot_files(tmp_path: Path) -> None:
    errors = verify_native_stack(tmp_path, make_lock())
    assert errors
    assert any("missing" in error.lower() for error in errors)


def test_native_entrypoint_must_be_relative_and_cannot_traverse_parent(tmp_path: Path) -> None:
    absolute = make_lock(entrypoint="/tmp/awaken.py")
    traversal = make_lock(entrypoint="../awaken.py")
    assert any("entrypoint" in error.lower() for error in verify_native_stack(tmp_path, absolute))
    assert any("entrypoint" in error.lower() for error in verify_native_stack(tmp_path, traversal))


def test_native_stack_lock_requires_exact_frozen_identity(tmp_path: Path) -> None:
    wrong = NativeStackLock(
        repo_id="someone/else",
        revision="deadbeef",
        gguf_path=GGUF_PATH,
        gguf_sha256=GGUF_SHA256,
        entrypoint="Genesis_Engine/soul/awaken.py",
        required_files={},
    )
    errors = verify_native_stack(tmp_path, wrong)
    assert "unexpected repo_id" in errors
    assert "unexpected revision" in errors
