# Spark / Trinity creature state

The creator API reuses the tested Beast Box Trinity implementation. It does not fork the state math.

`compose_creature_state(state12)` returns external 12D, projected 42D, block-balanced 54D, dynamic state snapshots, and projection hashes. `zero_state_report()` verifies that zero input remains exactly zero through the creator-facing state path.

Run `report.py` to print the current projection hashes from code rather than trusting copied documentation.
