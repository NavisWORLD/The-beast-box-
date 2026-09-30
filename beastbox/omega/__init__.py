"""OMEGA: observation, bounded operation and evaluation around DurableRuntime.

Nothing in this package changes routing, memory, checkpoint or authority
semantics. The tracer reads values at existing stage boundaries; the operator
drives the runtime through its public API under host-owned budgets and grants.
"""

from .tracer import TracedDurableRuntime, TraceWriter, verify_trace_file

__all__ = ["TracedDurableRuntime", "TraceWriter", "verify_trace_file"]
