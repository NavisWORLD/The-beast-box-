from beastbox.creature.native_gguf import conversion_recipe, conversion_matrix


def test_requested_native_models_have_explicit_recipes():
    expected = {"phos", "cosmos-born", "samgo-5.7", "cosmos-best"}
    assert set(conversion_matrix()) == expected


def test_born_records_real_tokenizer_boundary():
    recipe = conversion_recipe("cosmos-born")
    assert recipe.source_path == "weights/cosmos_born.pt"
    assert recipe.architecture == "cosmos"
    assert recipe.tokenizer == "char-99"
    assert recipe.stock_llamacpp is False
    assert "tokenizer" in recipe.runtime_requirement.lower()


def test_phos_uses_cosmos_architecture_not_fake_llama_label():
    recipe = conversion_recipe("phos")
    assert recipe.source_path == "weights/phos.pt"
    assert recipe.architecture == "cosmos"
    assert recipe.stock_llamacpp is False
    assert "LLM_ARCH_COSMOS" in recipe.runtime_requirement


def test_samgo_and_cosmos_best_keep_gpt2_tokenizer_lineage():
    samgo = conversion_recipe("samgo-5.7")
    best = conversion_recipe("cosmos-best")
    assert samgo.tokenizer == "gpt2-bpe"
    assert best.tokenizer == "gpt2-bpe"
    assert samgo.d_model == 512
    assert best.d_model == 512
    assert best.vocab_size == 50257
    assert best.layers == 2
    assert best.heads == 8


def test_output_names_are_stable_and_distinct():
    names = {conversion_recipe(name).output_name for name in conversion_matrix()}
    assert names == {
        "cosmos-phos-f32.gguf",
        "cosmos-born-f32.gguf",
        "cosmos-samgo-5.7-f32.gguf",
        "cosmos-best-f32.gguf",
    }
