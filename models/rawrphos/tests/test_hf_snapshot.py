"""Published inference-only snapshot contract: no optimizer/RNG state is required."""
import hashlib
import json
import shutil

import pytest
import torch


@pytest.fixture
def staged(tmp_path):
    from rawrphos.architecture.model import RawrphosConfig, RawrphosLM
    from rawrphos.tokenizer.tokenizer import RawrphosTokenizer
    from rawrphos.training.checkpoint import save_checkpoint, rng_state
    tokenizer = RawrphosTokenizer.train(["The little cat was safe."] * 10, 300)
    torch.manual_seed(8)
    model = RawrphosLM(RawrphosConfig(
        vocab_size=tokenizer.vocab_size, d_model=32, n_heads=4,
        n_layers=2, max_seq_len=256
    ))
    ids = torch.tensor([tokenizer.encode("The little cat was safe.")])
    opt = torch.optim.AdamW(model.parameters(), lr=0.001)
    model(ids[:, :-1], targets=ids[:, 1:])["loss"].backward()
    opt.step()
    original = tmp_path / "original"
    metadata = save_checkpoint(
        original, model, tokenizer,
        {"training_steps": 1, "training_tokens": ids.shape[1] - 1,
         "training_seq_len": ids.shape[1] - 1,
         "release_status": "test-fixture-trained"},
        {"rng": rng_state()},
    )
    target = tmp_path / "snapshot"
    target.mkdir()
    required = ("model.safetensors", "metadata.json", "config.json",
                "tokenizer/tokenizer.json", "tokenizer/metadata.json")
    digests = {}
    for name in required:
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original / name, dest)
        digests[name] = hashlib.sha256(dest.read_bytes()).hexdigest()
    (target / "inference-manifest.json").write_text(json.dumps({
        "schema": "rawrphos-inference-snapshot-v1",
        "model_id": "rawrphos-native",
        "training_steps": 1,
        "checkpoint_sha256": metadata["checkpoint_sha256"],
        "files": digests,
    }))
    return target, metadata["checkpoint_sha256"]


def test_inference_only_snapshot_generates_without_optimizer(staged):
    from rawrphos.inference.engine import Engine
    path, expected = staged
    assert not (path / "training_state.pt").exists()
    engine = Engine(path, max_new_tokens=8, threads=1,
                    expected_sha256=expected)
    assert engine.info()["checkpoint_sha256"] == expected
    assert engine.info()["training_steps"] == 1
    response = engine.complete("The cat", max_tokens=4, temperature=0)
    assert isinstance(response, str)
    assert engine.last_metrics["generated_tokens"] > 0


def test_inference_snapshot_rejects_wrong_hash_and_tampering(staged):
    from rawrphos.inference.engine import Engine
    from rawrphos.inference.snapshot import load_inference_snapshot
    path, expected = staged
    with pytest.raises(ValueError, match="pinned weight SHA"):
        Engine(path, max_new_tokens=4, threads=1)
    with pytest.raises(ValueError, match="identity mismatch"):
        load_inference_snapshot(path, "0" * 64)
    tokenizer_file = path / "tokenizer/tokenizer.json"
    tokenizer_file.write_bytes(tokenizer_file.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_inference_snapshot(path, expected)


def test_inference_snapshot_rejects_path_traversal(staged):
    from rawrphos.inference.snapshot import load_inference_snapshot
    path, expected = staged
    manifest_path = path / "inference-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["../leak.txt"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="unsafe inference member"):
        load_inference_snapshot(path, expected)
