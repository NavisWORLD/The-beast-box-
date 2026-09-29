# Exact original QC67 native adapter (opt-in research service)

This is a **separate original-model runtime**, not a fake replacement for the
existing RAWRPHØS 14K/18K services. The published PHOS and SAMGO weights are
downloaded **only at build time** from a fixed public Hugging Face commit and
verified against their full original SHA-256 digests. PHOS uses the exact
published dyn12 Ladder and its 162-character vocabulary. SAMGO uses the original
54D CosmosTransformer source pinned in Cory Davis's other public Apache-2.0
repository and the published GPT-2 tokenizer/configuration. Strict state-dict
load and CPU forward were verified in GitHub Actions; no retraining occurs.

The HF upstream model card currently declares `license: other`. Preserve its
existing provenance and confirm weight redistribution terms before exporting
images or releasing packaged weights to third parties. The original 54D source
is Apache-2.0 in its own repository. Runtime tests and model availability are
independent of unverifiable origin narratives or consciousness claims.

The native sidecar binds **only 127.0.0.1:8771** and requires the host-only
`RAWRPHOS_API_KEY` bearer. Choice IDs are `qc67-phos` and `qc67-samgo`. The
owner bridge exposes explicit `qc67_phos` and `qc67_samgo` choices only
after separately checking the loaded real model IDs, pinned original checksums
and immutable upstream revision. No fallback to any other model is allowed.

To enable on the pinned Railway image *after* the real native acceptance and
memory/volume tests pass, set host env `BEASTBOX_QC67_LOCAL_ENABLED=yes`. The
Docker build installs originals at `QC67_INSTALL_DIR`; the flag defaults OFF.
The bridge and native sidecar run in the existing owner-authenticated backend,
preserving existing persistent COSMOS data and model authority. CPU and memory
headroom must be independently verified before production enablement.

**Important limitation:** PHOS is a tiny character-level experiment and
SAMGO is an experimental limited-context 54D model. The native HTTP adapter
reduces composed COSMOS prompts to a bounded owner-input excerpt because the
original checkpoints cannot consume full Beast Box prompts. This is clearly
marked in the API `prompt_truncated` receipt. Native generation and real
weights do not establish reliable general conversation or safe code generation.

COSMIC.CYPHER is **already a coding agent, not a separate model checkpoint**.
It can register local original models through its existing OpenAI-compatible
backend, but tool/action JSON may be unreliable with these experimental weights.
For hands-on coding, select a capable verified installed language model and
provide an owner-selected workspace; running/editing code needs explicit flags:

```bash
cosmic.cypher-cli models add phos-original --backend openai-compatible \
  --model qc67-phos --url http://127.0.0.1:8771/v1
cosmic.cypher-cli models add samgo-original --backend openai-compatible \
  --model qc67-samgo --url http://127.0.0.1:8771/v1
cosmic.cypher-cli code samgo-original "Inspect this repository" \
  --workspace /owner/selected/workspace
```

For environments using the host API key, direct authenticated Beast Box owner
chat is the supported production entrypoint; COSMIC.CYPHER's standalone CLI
backend does not inject host secrets into requests, and is intended for
separately authorized local development only.
