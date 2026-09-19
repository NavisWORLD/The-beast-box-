# Publishing the QC67 / Zeref kit to Hugging Face

The repository contains a keyless GitHub Actions publisher at:

```text
.github/workflows/publish-huggingface.yml
```

It publishes only the curated files in `huggingface/` to the existing model repository `phera-ra/QC67_cosmo`; it does not replace the model-weight files.

## One-time Hugging Face setup

In the Hugging Face settings for `phera-ra/QC67_cosmo`, add a **Trusted Publisher** with these claims:

```text
Provider:   GitHub Actions
Repository: NavisWORLD/The-beast-box-
Workflow:   publish-huggingface.yml
```

You may additionally pin it to the branch/tag policy you want. The workflow requests GitHub's OIDC identity token and Hugging Face exchanges it for a short-lived token scoped to `phera-ra/QC67_cosmo`.

After the publisher is configured, run **Publish QC67 kit to Hugging Face** from GitHub Actions or create a `v*` tag.

## What gets published

```text
huggingface/QC67_MODEL_CARD_NEXT.md -> README.md
huggingface/ZEREF_OLLAMA_KIT/      -> ZEREF_OLLAMA_KIT/
```

The updated model card documents:

- direct Ollama use of `hf.co/phera-ra/QC67_cosmo`;
- the persistent COSMOS/Zeref runtime;
- switchable Ollama backends with shared memory;
- Windows and macOS launch paths;
- the distinction between persistent runtime learning/state and static GGUF weight training.

## Secret handling

Do not commit a Hugging Face access token into this repository, a Modelfile, a shell script, a DMG, or a workflow YAML file. Trusted publishing avoids a long-lived token entirely and keeps Hub write authority scoped to the model repository and CI identity.
