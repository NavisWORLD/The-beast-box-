# GGUF weights

This folder is for genuine GGUF files whose architecture is supported by the chosen GGUF runtime.

Recommended workflow:

1. Obtain a compatible source model under its license.
2. Use the architecture's supported converter.
3. Verify the output starts with GGUF magic.
4. Generate a `cosmos.weight-manifest.v1` record.
5. Test inference independently before attaching COSMOS state/memory layers.

QC67's native Spark checkpoint is custom and must remain native unless a converter plus runtime support for that architecture is implemented and verified.
