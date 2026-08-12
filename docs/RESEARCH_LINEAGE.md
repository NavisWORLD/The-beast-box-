# Research lineage and canonical references

The Beast Box is a public integration/reconstruction repository. It does not replace the canonical COSMOS/CST research artifacts; it gives them an installable continuity/containment harness.

## Canonical public research

- **Hugging Face — QC67_cosmo**  
  https://huggingface.co/phera-ra/QC67_cosmo
- **Master findings / corrections / nulls**  
  https://huggingface.co/phera-ra/QC67_cosmo/blob/main/FINDINGS.md
- **Architecture directory — state ladder, PHOS and mechanism tests**  
  https://huggingface.co/phera-ra/QC67_cosmo/tree/main/architecture
- **Training guide**  
  https://huggingface.co/phera-ra/QC67_cosmo/blob/main/TRAINING.md
- **Quantum creature/model-birth notes**  
  https://huggingface.co/phera-ra/QC67_cosmo/blob/main/QUANTUM_CREATURE.md
- **Quantum measurement manifest**  
  https://huggingface.co/phera-ra/QC67_cosmo/blob/main/data/quantum_measurements_manifest.json
- **Zenodo — 12-Dimensional Cosmic Synapse Theory**  
  https://doi.org/10.5281/zenodo.17574447
- **Public COSMOS runtime repository**  
  https://github.com/NavisWORLD/Cosmos
- **Earlier CST theory/simulation lineage**  
  https://github.com/NavisWORLD/The-theory-of-CST
- **Public 12D Hebbian transformer lineage**  
  https://github.com/NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer
- **Legacy simulation/memory reference**  
  https://github.com/PHERACLEASE/test/blob/main/test1maybe.py

## Evidence taxonomy

Use these words deliberately:

- **IMPLEMENTED** — a code path/component exists.
- **OBSERVED** — runtime evidence shows it executed.
- **MEASURED** — a defined metric was produced by a stated benchmark.
- **NULL** — the preregistered advantage was not demonstrated.
- **HYPOTHESIS** — a falsifiable research question.
- **METAPHOR / MODEL** — conceptual language, not literal physics/biology.

## Important existing results to preserve

The public research line distinguishes quantum **provenance** from quantum **advantage**. Auditable measurement-derived initialization/control provenance exists for specific artifacts, while matched quantum-injection experiments have not established a general predictive advantage.

The published state-ladder work treats dyn12/dyn42/dyn54/static54/tri/tri3 as controlled architecture conditions, with dyn12 being the compact efficiency result in the documented small-model comparison. Do not rewrite that as “more dimensions are always better.”

The paired-state benchmark is also a retained null: aligned measured state beat some destroyed-pairing controls but did not beat plain attention. That result belongs in the record.

## Hugging Face helper

```bash
pip install -e '.[huggingface]'
beastbox hf-info
beastbox hf-fetch
```

The default fetch intentionally selects research/code/manifest files rather than blindly downloading every potentially large artifact.
