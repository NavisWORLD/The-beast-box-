"""Cosmic Cypher: local-model registry, GGUF adapters, stateful dialogue and bounded coding tools."""

from .agent import CoderAgent
from .models import ModelSpec, create_model
from .registry import ModelRegistry
from .workspace import Workspace

__all__ = ["CoderAgent", "ModelRegistry", "ModelSpec", "Workspace", "create_model"]
