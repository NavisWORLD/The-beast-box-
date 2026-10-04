"""Lazy imports of the existing Spark Beast generator. Nothing here is rewritten."""

from __future__ import annotations

import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def spark_path() -> Path:
    return repo_root() / "spark-beasts"


def load():
    spark = str(spark_path())
    if spark not in sys.path:
        sys.path.insert(0, spark)
    from beastgen.genome import build_genome
    from beastgen.runs import get_run
    from beastgen.signal import simulate
    from qbeast_file import (
        PRIVATE,
        build_qbeast,
        generate_creature,
        hash_object,
        load_qbeast,
        serialize_qbeast,
        sha256_text,
    )

    return {
        "build_genome": build_genome,
        "get_run": get_run,
        "simulate": simulate,
        "PRIVATE": PRIVATE,
        "build_qbeast": build_qbeast,
        "generate_creature": generate_creature,
        "hash_object": hash_object,
        "load_qbeast": load_qbeast,
        "serialize_qbeast": serialize_qbeast,
        "sha256_text": sha256_text,
    }
