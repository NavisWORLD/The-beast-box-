"""Honesty labels used everywhere in the Spark host (AI-WRITTEN GLUE).

The wording follows Cory's standing rules and the Beast Box routing classes
(beastbox/routing.json "classes": real / simulated / stale / control / missing).
"""
CONCEPT = "CONCEPT DESIGN / NOT BUILT HARDWARE"
PULSE = "pulse = ESTIMATE, non-medical"
MEASURED = "MEASURED"      # a number read from a sensor
DERIVED = "DERIVED"        # computed from MEASURED numbers (features, T=(S-D)/(W-D), dyn12)
ESTIMATE = "ESTIMATE"      # a model/heuristic guess (pulse, battery %)
SIMULATION = "SIMULATION — not a real measurement"
MODEL_RULE = "MODEL != MEMORY != STATE != AUTHORITY (models are mouths)"
