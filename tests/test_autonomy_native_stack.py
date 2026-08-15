import json
from pathlib import Path

from beastbox.autonomy.native_stack import NativeStackLock, verify_native_stack


REPO_ID = "phera-ra/QC67_cosmo"
REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"
GGUF_PATH = "weights/cosmos-cst.gguf"
GGUF_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
ENTRYPOINT = "serving/cosmos_coder.py"
REQUIRED = {
    "START_CODER.bat": "cb7cc112c924c6f3e171b125439cd73e1ac62a0898f8eb6b43099f857d4e5819",
    "serving/cosmos_coder.py": "941de6ffd3b075affb25ac7d2f08424678c695d2f5c75152013419042eae00a4",
    "serving/cosmos_serve.py": "02a509f9c2a20f63c38dca186c082bfdc2603aa8b6f1f903ec19a0e709218d87",
    "genesis_engine/soul/loop.py": "84823850910d008c8f2e093ce99d993ec4e0eb0cded18d2a8b19ba7e5dba3f94",
    "soul/cosmos_bridge.py": "59a0a1a6465a4ac0415189b4391767308ce5ba87a09dcc4a2dfac4ea1d034b5c",
    "soul/math_hand.py": "9fedc668e98880f99b59f288b026f0ed651cc7d9ab545064bf195dcf999be548",
    "architecture/cosmos-arch.patch": "d77fa6fcecdadc8d8f0caceed9909dbbfca563c958d9f7f3efe320bc942c0445",
    "architecture/llama_cpp_cosmos.cpp": "442ca1d9692c7240857aeb91c9588e8eefe929b5221b9fccb28175fd0fa88ed6",
    "architecture/cosmos_spark_cst.py": "955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc",
    "weights/spark_cst.pt": "aa0cb13c1e67d459db280a53b6407dfc2b5b5f3fd6f640bc43686b70d799acd1",
}
LOCK_PATH = Path("experiments/autonomous-hands/native-stack.lock.json")


def make_lock(*, entrypoint: str = ENTRYPOINT) -> NativeStackLock:
    return NativeStackLock(
        repo_id=REPO_ID,
        revision=REVISION,
        gguf_path=GGUF_PATH,
        gguf_sha256=GGUF_SHA256,
        entrypoint=entrypoint,
        required_files=REQUIRED,
    )


def test_native_stack_lock_rejects_missing_snapshot_files(tmp_path: Path) -> None:
    errors = verify_native_stack(tmp_path, make_lock())
    assert errors
    assert any("missing" in error.lower() for error in errors)


def test_native_entrypoint_must_be_relative_and_cannot_traverse_parent(tmp_path: Path) -> None:
    absolute = make_lock(entrypoint="/tmp/cosmos_coder.py")
    traversal = make_lock(entrypoint="../cosmos_coder.py")
    assert any("entrypoint" in error.lower() for error in verify_native_stack(tmp_path, absolute))
    assert any("entrypoint" in error.lower() for error in verify_native_stack(tmp_path, traversal))


def test_native_stack_lock_requires_exact_frozen_identity(tmp_path: Path) -> None:
    wrong = NativeStackLock(
        repo_id="someone/else",
        revision="deadbeef",
        gguf_path=GGUF_PATH,
        gguf_sha256=GGUF_SHA256,
        entrypoint=ENTRYPOINT,
        required_files={},
    )
    errors = verify_native_stack(tmp_path, wrong)
    assert "unexpected repo_id" in errors
    assert "unexpected revision" in errors


def test_repository_lock_records_exact_native_hands_and_state_lineage() -> None:
    raw = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    assert raw["repo_id"] == REPO_ID
    assert raw["revision"] == REVISION
    assert raw["gguf_path"] == GGUF_PATH
    assert raw["gguf_sha256"] == GGUF_SHA256
    assert raw["entrypoint"] == ENTRYPOINT
    assert raw["required_files"] == REQUIRED
    assert raw["native_execution_hand"] == "serving/cosmos_coder.py"
    assert raw["native_autonomy_component"] == "genesis_engine/soul/loop.py"
    assert raw["native_physics_bridge"] == "soul/cosmos_bridge.py"
    assert raw["native_cst_runtime"] == "serving/cosmos_serve.py"
    assert raw["native_cst_architecture"] == "architecture/cosmos_spark_cst.py"
    assert raw["native_cst_checkpoint"] == "weights/spark_cst.pt"
    assert raw["action_wrapper"] is None
