#!/usr/bin/env python3
import argparse
import json
from beastbox.creature.gguf import export_gguf
from beastbox.creature.weights import inspect_weight

p = argparse.ArgumentParser(description="Run a real external GGUF converter, or copy an already-valid GGUF file.")
p.add_argument("source")
p.add_argument("output")
p.add_argument("--converter", nargs="+")
a = p.parse_args()
path = export_gguf(a.source, a.output, converter=a.converter)
print(json.dumps(inspect_weight(path), indent=2, sort_keys=True))
