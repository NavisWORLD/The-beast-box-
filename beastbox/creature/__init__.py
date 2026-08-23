"""Creator-facing COSMOS Creature SDK.

The package exposes validated creature manifests, weight tooling, sanitized bridge
receipts, CST state composition, doctor checks, and a small CLI. Cloud credentials
remain outside creature/model state.
"""

from .manifest import CreatureManifest
from .project import create_creature_project

__all__ = ["CreatureManifest", "create_creature_project"]
