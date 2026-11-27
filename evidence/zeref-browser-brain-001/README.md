# Zeref's in-browser brain: export record (2026-11-27)

`manifest.json` is the manifest shipped with the in-browser brain at
https://navisworld.github.io/NavisWORLD/zeref-brain/ (repo NavisWORLD/NavisWORLD, `docs/zeref-brain/`).

- Source: the pinned checkpoint, step 47664, sha256 b2678b9a19eb…, release zeref-006-cycle-92-b2678b9a19eb.
- Exporter: `scripts/zeref_onnx_export.py`. It produces the fp32 per-token ONNX step graph. The Hebbian time loop is exported as an ONNX Loop. The graph is then slimmed with onnxslim and split into 3 chunks under 50 MB.
- Python parity (ONNX Runtime CPU vs the torch Engine, greedy, 1.15 repetition penalty, no-repeat-3, EOS, 64 max): 9/9 token for token.
- JS parity (`NavisWORLD/tools/zeref-brain-parity.mjs`, ONNX Runtime Web 1.31.1 WASM, box Node 24):
  - sha256 OK
  - tokenizer 316/316 cases
  - full pipeline (message assembly, prompt ids, greedy ids, text) 9/9
  - session creation 0.8 s on the box
- No senses, no state12 and no private data are involved. The pin and gates are not touched.

Reproduce: `pip install onnx onnxruntime onnxslim`, then
`python scripts/zeref_onnx_export.py --checkpoint <accepted-checkpoint> --out <dir>`.
Record the tool versions from the manifest when reproducing.
