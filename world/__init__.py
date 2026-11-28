"""Sandboxed deterministic world for Zeref's world-tick runner.

Pure stdlib. The world is numbers, never pictures: nodes carry numeric physical
field baselines, entities carry discrete mutable states, and the sensorium reads
change (temporal differentials), never static snapshots.
"""
