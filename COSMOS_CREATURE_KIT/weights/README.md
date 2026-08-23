# Weight vault

Keep model formats explicit.

- `native/`: QC67/Spark `.pt`, `.pth`, `.ckpt`, safetensors, and architecture-specific checkpoints.
- `gguf/`: genuine GGUF files for runtimes that support the underlying architecture.
- `adapters/`: CST/state sidecars, manifests, and projection metadata.
- `tools/`: thin wrappers around the installed Creature SDK.

Every distributable weight should have a manifest with SHA-256, byte size, architecture, format, quantization when relevant, tokenizer identity, source checkpoint, license, provenance, and converter identity.

A `.pt` file does not become GGUF by changing its extension. The export helper refuses that operation unless a real converter command is supplied and produces a file with GGUF magic.
