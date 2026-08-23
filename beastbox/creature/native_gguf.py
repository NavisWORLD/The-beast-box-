from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .weights import inspect_weight


@dataclass(frozen=True)
class NativeGGUFRecipe:
    model_id: str
    source_path: str
    output_name: str
    architecture: str
    tokenizer: str
    stock_llamacpp: bool
    runtime_requirement: str
    checkpoint_state_key: str | None = None
    d_model: int | None = None
    layers: int | None = None
    heads: int | None = None
    vocab_size: int | None = None
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


_RECIPES: dict[str, NativeGGUFRecipe] = {
    "phos": NativeGGUFRecipe(
        model_id="phos",
        source_path="weights/phos.pt",
        output_name="cosmos-phos-f32.gguf",
        architecture="cosmos",
        tokenizer="checkpoint-defined",
        stock_llamacpp=False,
        runtime_requirement=(
            "Requires the COSMOS llama.cpp fork with LLM_ARCH_COSMOS and the PHOS/dyn12 graph; "
            "do not relabel this checkpoint as llama, qwen, or another stock architecture."
        ),
        notes=(
            "PHOS is the custom dyn12/phi-scaffold lineage. The published lineage documents a real "
            "LLM_ARCH_COSMOS graph path; source checkpoint tensors must still be inspected and hashed "
            "before conversion."
        ),
    ),
    "cosmos-born": NativeGGUFRecipe(
        model_id="cosmos-born",
        source_path="weights/cosmos_born.pt",
        output_name="cosmos-born-f32.gguf",
        architecture="cosmos",
        tokenizer="char-99",
        stock_llamacpp=False,
        runtime_requirement=(
            "Requires COSMOS runtime support for the original 99-symbol character tokenizer. "
            "Stock llama.cpp BPE/SPM tokenizers are not equivalent."
        ),
        d_model=192,
        layers=4,
        heads=4,
        vocab_size=99,
        notes=(
            "The historical tensor remap was forward-checked against PyTorch, but stock llama.cpp "
            "rejected the character tokenizer. A GGUF container is valid only when this tokenizer "
            "boundary is preserved explicitly."
        ),
    ),
    "samgo-5.7": NativeGGUFRecipe(
        model_id="samgo-5.7",
        source_path="weights/samgo_weights.pt",
        output_name="cosmos-samgo-5.7-f32.gguf",
        architecture="cosmos",
        tokenizer="gpt2-bpe",
        stock_llamacpp=False,
        runtime_requirement=(
            "Requires a COSMOS graph that preserves the model's 54D CST/Hebbian/chaos state path; "
            "GPT-2 BPE compatibility alone does not make the custom model a stock GPT-2 graph."
        ),
        d_model=512,
        notes=(
            "samgo 5.7 uses the GPT-2 BPE lineage and the 12D + 24D + 18D state decomposition. "
            "Its exact layer/head/state-dict schema must be read from the source checkpoint before "
            "the tensor map is frozen."
        ),
    ),
    "cosmos-best": NativeGGUFRecipe(
        model_id="cosmos-best",
        source_path="Cosmos/checkpoints/cosmos/cosmos_best.pt",
        output_name="cosmos-best-f32.gguf",
        architecture="cosmos",
        tokenizer="gpt2-bpe",
        stock_llamacpp=False,
        runtime_requirement=(
            "Requires a COSMOS graph that implements CST phase modulation, Hebbian plasticity, "
            "Lorenz chaos state, persistent memory, and the original transformer path."
        ),
        checkpoint_state_key="model_state_dict",
        d_model=512,
        layers=2,
        heads=8,
        vocab_size=50257,
        notes=(
            "The canonical training script saves model_state_dict + config and uses GPT-2 vocab 50257, "
            "d_model 512, two layers, eight heads, d_ff 2048, max context 512."
        ),
    ),
}


def conversion_matrix() -> dict[str, dict[str, Any]]:
    return {name: recipe.as_dict() for name, recipe in _RECIPES.items()}


def conversion_recipe(model_id: str) -> NativeGGUFRecipe:
    key = str(model_id).strip().lower()
    try:
        return _RECIPES[key]
    except KeyError as exc:
        known = ", ".join(sorted(_RECIPES))
        raise KeyError(f"unknown COSMOS model recipe {model_id!r}; choose one of: {known}") from exc


def build_conversion_plan(
    model_id: str,
    *,
    source: str | Path | None = None,
    output_dir: str | Path = ".",
) -> dict[str, Any]:
    recipe = conversion_recipe(model_id)
    src = Path(source) if source is not None else Path(recipe.source_path)
    out = Path(output_dir) / recipe.output_name

    source_record: dict[str, Any] = {
        "path": str(src),
        "expected_path": recipe.source_path,
        "exists": src.is_file(),
    }
    status = "SOURCE_MISSING"
    if src.is_file():
        info = inspect_weight(src)
        source_record.update(
            {
                "filename": info["filename"],
                "size": info["size"],
                "sha256": info["sha256"],
                "format": info["format"],
            }
        )
        status = "SOURCE_READY"

    return {
        "schema": "cosmos.native-gguf-plan.v1",
        "model_id": recipe.model_id,
        "status": status,
        "architecture": recipe.architecture,
        "tokenizer": recipe.tokenizer,
        "source": source_record,
        "output": str(out),
        "runtime": {
            "stock_llamacpp": recipe.stock_llamacpp,
            "requirement": recipe.runtime_requirement,
        },
        "checkpoint_state_key": recipe.checkpoint_state_key,
        "model_shape": {
            "d_model": recipe.d_model,
            "layers": recipe.layers,
            "heads": recipe.heads,
            "vocab_size": recipe.vocab_size,
        },
        "notes": recipe.notes,
    }
