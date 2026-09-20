# i dare you 💀 — Open Model Swap Lab

Cory Davis · Beast Box · **SmolLM2-135M-Instruct ↔ authentic PHOS**

This branch replaces the earlier proprietary-provider protocol with two independently accessible models. Earlier experiments remain in Git history; their evidence is not retroactively rewritten. Only files in this isolated experiment folder and the dedicated CI workflow are in scope.

## Actual model identities

- **A — SmolLM2-135M-Instruct:** HuggingFaceTB/SmolLM2-135M-Instruct, Apache-2.0; download a pinned revision at runtime. Do not mix it up with the older, non-instruction model.
- **B — published PHOS:** phera-ra/QC67_cosmo, revision `b414724c627300c41b099dcc6853766d08fd27a4`, `weights/phos.pt`. Pinned SHA-256: `bdcd4a39aa54bfc6c274580e210f993e528214d7207cb19dc258a2f801f6b84d`; from a successful repository CI download preflight. Load its actual `cosmos_state_ladder.Ladder` source, not a generic reference model.
- Separate external state is supplied to providers as explicit context. It does not change either model's weights.

## Run it

Launch the dedicated GitHub Actions workflow `I Dare You - Open Model Swap` on this feature branch or run on a suitably provisioned local machine:

```bash
python -m pip install 'torch>=2.4' 'transformers>=4.45,<5' 'huggingface-hub>=0.27' safetensors
hf download phera-ra/QC67_cosmo weights/phos.pt --revision b414724c627300c41b099dcc6853766d08fd27a4 --local-dir _real_phos
hf download phera-ra/QC67_cosmo --include 'architecture/*.py' --revision b414724c627300c41b099dcc6853766d08fd27a4 --local-dir _real_phos
PHOS_EXPECTED_SHA256=bdcd4a39aa54bfc6c274580e210f993e528214d7207cb19dc258a2f801f6b84d python 'i dare you/open_swap.py' --output /tmp/open-model-swap-001 --phos-revision b414724c627300c41b099dcc6853766d08fd27a4
python 'i dare you/open_swap.py' --verify /tmp/open-model-swap-001/events.jsonl
```

`events.jsonl` is append-only, UTC stamped and SHA-256 linked. `summary.json` records executed/blocked phases. PHOS model loading fails closed if its hash or architecture mismatches. The run does not pretend that external-memory retrieval proves weight-level learning; authentic fine-tuning (B1/B2) is explicitly **not executed** until an independent training protocol can be verified.

## Sharing boundaries

Publish your original experiment code and permitted public evidence only. Verify licenses for PHOS model files before redistributing weights. The workflow uploads **receipts and generated public text only**, not either model's weight files. Never publish confidential prompts, API secrets, or unrelated user data.

Status: implementation and CI must be separately validated. A successful workflow exit is not proof that every phase executed: inspect `summary.json` for A0, B0, B1, B2 and A1 individually. No merge until independently reviewed.
