#!/usr/bin/env python3
import json
import sys
from beastbox.creature.weights import inspect_weight

if len(sys.argv) != 2:
    raise SystemExit("usage: inspect_weights.py MODEL")
print(json.dumps(inspect_weight(sys.argv[1]), indent=2, sort_keys=True))
