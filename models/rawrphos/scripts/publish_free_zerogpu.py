"""Explicitly provision only a *free* private ZeroGPU Gradio Space for RAWRPHØS.

No paid hardware, no dedicated Inference Endpoint, no automatic fallback.
Requires an eligible HF personal account and a token with Spaces write scope.
Creates no Space when free ZeroGPU quota/eligibility is unavailable.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

from huggingface_hub import HfApi, snapshot_download
from huggingface_hub.utils import HfHubHTTPError
from rawrphos.inference.snapshot import load_inference_snapshot, PINNED_12K_SHA

SPACE_ID = "phera-ra/rawrphos-12k-zerogpu"
MODEL_ID = "phera-ra/rawrphos-native-12k"
MODEL_REV = "4f019d41ec55850169de76dec495759167ddb42e"
HARDWARE = "zero-a10g"

MODULES = (
    "__init__.py",
    "architecture/__init__.py",
    "architecture/model.py",
    "architecture/generation.py",
    "tokenizer/__init__.py",
    "tokenizer/tokenizer.py",
    "training/__init__.py",
    "training/checkpoint.py",
    "inference/__init__.py",
    "inference/engine.py",
    "inference/snapshot.py",
)


def gradio_app() -> str:
    return '''"""Private, quota-limited Gradio API for exact RAWRPHØS 12K weights."""
import spaces  # Must initialize ZeroGPU CUDA emulation BEFORE importing torch.
import gradio as gr

from rawrphos.inference.engine import Engine

WEIGHT_SHA = "339fb8e1d6f3950e2aa15a6e33bf8c0f28dd655cefc93b7926fb7545e7e97601"
# The verifier checks every manifest member and the actual parameter identity.
# CUDA placement outside @spaces.GPU is supported by ZeroGPU's emulated CUDA.
engine = Engine("checkpoint", max_new_tokens=32, threads=2,
                expected_sha256=WEIGHT_SHA, device="cuda")
info = engine.info()
if (info["checkpoint_sha256"] != WEIGHT_SHA or info["training_steps"] != 12000
        or info["model_id"] != "rawrphos-native"):
    raise RuntimeError("wrong RAWRPHOS checkpoint; refusing to serve")


@spaces.GPU(duration=40)
def predict(prompt: str, max_tokens: int) -> str:
    """Generate a bounded story continuation from Cory Davis's native 12K model."""
    if not isinstance(prompt, str) or not 1 <= len(prompt) <= 1000:
        raise gr.Error("Text prompt must be 1–1000 characters")
    if isinstance(max_tokens, bool) or int(max_tokens) != max_tokens or not 1 <= max_tokens <= 32:
        raise gr.Error("Output must be 1–32 tokens")
    try:
        return engine.complete(prompt, max_tokens=int(max_tokens),
                               temperature=0, seed=67, timeout=35)
    except (ValueError, RuntimeError, TimeoutError, FloatingPointError):
        raise gr.Error("Native inference unavailable; no fallback") from None


def model_info():
    """Read the pinned model identity without spending ZeroGPU inference time."""
    # Only fixed identity fields; never expose model internals or any token.
    return {"model_id": "rawrphos-native", "ready": True,
            "training_steps": 12000, "checkpoint_sha256": WEIGHT_SHA,
            "serving_backend": "pytorch-zerogpu", "host": "private-hf-space"}


with gr.Blocks(title="RAWRPHØS Native 12K — Cory Davis / COSMOS") as demo:
    gr.Markdown("# RAWRPHØS 12K 🪰\\nPrivate experimental native-model API, not COSMOS memory or authority.")
    prompt = gr.Textbox(label="Story prompt", lines=2, max_lines=5)
    max_tokens = gr.Slider(minimum=1, maximum=32, step=1, value=16,
                           label="Output token budget")
    output = gr.Textbox(label="Native model response", lines=4)
    gr.Button("Generate").click(predict, inputs=[prompt, max_tokens],
                                outputs=output, api_name="predict",
                                concurrency_limit=1)
    info_box = gr.JSON(label="Pinned checkpoint identity")
    gr.Button("Model info").click(model_info, inputs=[], outputs=info_box,
                                   api_name="model_info")
demo.queue(max_size=8, default_concurrency_limit=1)
demo.launch()
'''


def stage(stage_dir: Path, token: str) -> None:
    root = Path(__file__).resolve().parents[3]
    if not (root / "models/rawrphos/architecture/model.py").exists():
        raise ValueError("expected the intact Beast Box repository checkout")
    download = snapshot_download(
        repo_id=MODEL_ID, repo_type="model", revision=MODEL_REV,
        token=token, local_dir=stage_dir.parent / "download"
    )
    model_path = Path(download)
    # The private Hub snapshot intentionally omits training_state.pt.
    verified = load_inference_snapshot(model_path, expected_checkpoint_sha256=PINNED_12K_SHA)
    if verified["metadata"]["training_steps"] != 12000:
        raise ValueError("not the 12K checkpoint")
    manifest = verified["manifest"]
    weights = stage_dir / "checkpoint"
    weights.mkdir(parents=True)
    for member in ("inference-manifest.json", *manifest["files"].keys()):
        src = model_path / member
        dest = weights / member
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    load_inference_snapshot(weights, expected_checkpoint_sha256=PINNED_12K_SHA)
    for member in MODULES:
        src = root / "models/rawrphos" / member
        if not src.is_file():
            if member.endswith("/__init__.py"):
                dest = stage_dir / "rawrphos" / member
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text("")
                continue
            raise ValueError("missing pinned model serving source: " + member)
        dest = stage_dir / "rawrphos" / member
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    app_source = gradio_app()
    compile(app_source, "<rawrphos-zerogpu-app>", "exec")
    (stage_dir / "app.py").write_text(app_source)
    (stage_dir / "requirements.txt").write_text(
        "torch==2.8.0\ntokenizers==0.23.2\nsafetensors==0.8.0\ngradio==5.50.0\n"
    )
    (stage_dir / "README.md").write_text(
        "---\ntitle: RAWRPHØS Native 12K\nemoji: 🪰\nsdk: gradio\nsdk_version: 5.50.0\n"
        "python_version: 3.12.12\nsuggested_hardware: zero-a10g\n"
        "pinned: false\n---\n\n"
        "# RAWRPHØS native 12K\n\nPrivate zero-hourly-cost ZeroGPU Gradio endpoint. "
        "Space creation requires an eligible account and available free quota; "
        "do not switch to billed GPU or Docker.\n\n"
        "Source: https://github.com/NavisWORLD/The-beast-box-/tree/feature/rawrphos-native-model-001/models/rawrphos\n"
        "Model snapshot: https://huggingface.co/" + MODEL_ID + "\n"
        "Immutable Hub revision: " + MODEL_REV + "\n"
        "Weight SHA-256: " + PINNED_12K_SHA + "\n\n"
        "API: Gradio `/predict` and `/model_info` (not OpenAI chat completions). "
        "Daily ZeroGPU quotas apply. The private Space needs owner HF auth. "
        "No paid inference or COSMOS access is automatically granted.\n"
    )
    if list(stage_dir.rglob("training_state.pt")):
        raise ValueError("optimizer state is forbidden in the serving Space")


def assert_free_hardware(api: HfApi) -> None:
    info = api.space_info(SPACE_ID)
    if not info.private:
        raise PermissionError("refusing public owner Space")
    runtime = api.get_space_runtime(SPACE_ID)
    current = str(getattr(runtime, "hardware", "") or "").lower()
    requested = str(getattr(runtime, "requested_hardware", "") or "").lower()
    # During build the current hardware may be None; the requested hardware
    # still MUST explicitly be zero-a10g (no implicit paid CPU fallback).
    if requested != HARDWARE and current != HARDWARE:
        try:
            api.pause_space(SPACE_ID)
        except Exception:
            pass
        raise RuntimeError("Space is not confirmed to request free ZeroGPU; paused if possible")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true",
                        help="Attempt creation of only a private free ZeroGPU Space")
    args = parser.parse_args()
    token = os.environ.get("HF_TOKEN", "")
    if args.confirm and (len(token) < 20 or any(char in token for char in "\r\n")):
        parser.error("Hugging Face repository-and-Space-write token required")
    if not args.confirm:
        print(json.dumps({"space_id": SPACE_ID, "hardware": HARDWARE,
                          "status": "DRY_RUN", "paid_hardware": False}))
        return
    api = HfApi(token=token)
    if api.whoami().get("name") != "phera-ra":
        raise PermissionError("not the verified HF account owner")
    with tempfile.TemporaryDirectory(prefix="rawrphos-free-space-") as tmp:
        staged = Path(tmp) / "space"
        staged.mkdir()
        stage(staged, token)
        try:
            info = api.space_info(SPACE_ID)
        except HfHubHTTPError as error:
            if error.response.status_code != 404:
                raise
            info = None
        if info is None:
            # Atomic creation request specifies the free ZeroGPU hardware. If
            # account eligibility, quota or Spaces permissions are absent, HF
            # rejects creation. Never retry on paid CPU, GPU or Endpoint.
            api.create_repo(repo_id=SPACE_ID, repo_type="space", space_sdk="gradio",
                            space_hardware=HARDWARE, private=True, exist_ok=False)
        assert_free_hardware(api)
        commit = api.upload_folder(repo_id=SPACE_ID, repo_type="space",
                                   folder_path=str(staged),
                                   commit_message="Serve pinned RAWRPHØS native 12K on free ZeroGPU")
        assert_free_hardware(api)
        runtime = api.get_space_runtime(SPACE_ID)
        print(json.dumps({"space_url": f"https://huggingface.co/spaces/{SPACE_ID}",
                          "commit_url": getattr(commit, "commit_url", None),
                          "hardware": HARDWARE, "paid_hardware": False,
                          "runtime_stage": getattr(runtime, "stage", None),
                          "checkpoint_sha256": PINNED_12K_SHA,
                          "actual_inference_attested": False,
                          "brain_bay_connected": False}, default=str))


if __name__ == "__main__":
    main()
