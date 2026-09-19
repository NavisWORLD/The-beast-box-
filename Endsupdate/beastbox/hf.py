from __future__ import annotations

from pathlib import Path

PUBLIC_HF_REPO = "phera-ra/QC67_cosmo"
PUBLIC_LINKS = {
    "model": "https://huggingface.co/phera-ra/QC67_cosmo",
    "findings": "https://huggingface.co/phera-ra/QC67_cosmo/blob/main/FINDINGS.md",
    "architecture": "https://huggingface.co/phera-ra/QC67_cosmo/tree/main/architecture",
    "training": "https://huggingface.co/phera-ra/QC67_cosmo/blob/main/TRAINING.md",
    "quantum_creature": "https://huggingface.co/phera-ra/QC67_cosmo/blob/main/QUANTUM_CREATURE.md",
    "quantum_manifest": "https://huggingface.co/phera-ra/QC67_cosmo/blob/main/data/quantum_measurements_manifest.json",
    "paired_conditioning": "https://huggingface.co/phera-ra/QC67_cosmo/tree/main/benchmarks/results",
}


def info() -> dict[str, object]:
    return {"repo_id": PUBLIC_HF_REPO, "links": dict(PUBLIC_LINKS)}


def fetch_public_assets(local_dir: str | Path, patterns: list[str] | None = None) -> str:
    """Download selected public research artifacts. No private token is required by this helper."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError("Install Hugging Face extra: pip install 'cosmos-beast-box[huggingface]'") from exc
    allow = patterns or [
        "README.md",
        "FINDINGS.md",
        "TRAINING.md",
        "QUANTUM_CREATURE.md",
        "architecture/*.py",
        "benchmarks/*.py",
        "benchmarks/results/*.json",
        "data/quantum_measurements_manifest.json",
    ]
    path = snapshot_download(repo_id=PUBLIC_HF_REPO, local_dir=str(local_dir), allow_patterns=allow)
    return str(path)
