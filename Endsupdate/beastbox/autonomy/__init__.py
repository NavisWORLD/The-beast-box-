"""Out-of-band infrastructure for the Zeref Autonomous Hands research range.

This package does not implement or dispatch Zeref's native hand actions. The
subject's canonical hand/state implementation remains in the frozen Hugging
Face snapshot and is verified by hash before any run.
"""

from .native_stack import NativeStackLock, verify_native_stack

__all__ = ["NativeStackLock", "verify_native_stack"]
