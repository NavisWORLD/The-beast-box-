"""Bounded SOUL/SDT compatibility layer for the existing Beast runtime.

SOUL is historical project terminology for a software state/event lineage. The
package does not claim a literal soul, consciousness, biological continuity, or
quantum advantage.
"""

from .adapter import bridge_from_soul
from .bus import SoulTokenBus
from .loop import SoulLoop
from .qbt_source import QBTLoopbackSoulSource
from .replay import ReplaySoulSource
from .token import SoulToken

__all__ = [
    "QBTLoopbackSoulSource",
    "ReplaySoulSource",
    "SoulLoop",
    "SoulToken",
    "SoulTokenBus",
    "bridge_from_soul",
]
