# COSMOS Creature Kit

Build a reproducible stateful COSMOS creature from a model backbone, persistent project state, CST/Trinity state composition, and optional sanitized state-source bridges.

## What is in the kit

- `weights/` keeps native checkpoints, real GGUF files, adapter manifests, and conversion/inspection tools separate.
- `templates/` provides blank, local, IBM, Azure, and hybrid creature manifests.
- `examples/` shows project creation and sanitized bridge adaptation.
- `loops/` shows how receipts become the same 12D -> 42D -> balanced 54D state packet.
- `spark/` exposes the CST/Trinity projection report.
- `libraries/` maps the reusable Python APIs.
- `evidence/` defines reproducible run receipts.

The executable implementation lives in `beastbox.creature`. The kit files intentionally call that package instead of maintaining a second implementation.

## Claim boundary

IBM, Azure, and classical inputs are state/provenance sources. A provider-specific effect is not by itself evidence of quantum advantage, consciousness, autonomy, or greater intelligence.

## Start

```bash
pip install -e .
cosmos-creature create Nova --root ./creatures
cosmos-creature doctor ./creatures/Nova
```

Then choose or import a backbone, record its weight manifest, configure a bridge, and keep the doctor green before making experimental claims.
