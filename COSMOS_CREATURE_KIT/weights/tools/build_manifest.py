#!/usr/bin/env python3
import argparse
import json
from beastbox.creature.weights import build_weight_manifest

p = argparse.ArgumentParser()
p.add_argument("model")
p.add_argument("--architecture")
p.add_argument("--quantization")
p.add_argument("--tokenizer")
p.add_argument("--source-checkpoint")
p.add_argument("--license", dest="license_name")
p.add_argument("--provenance")
a = p.parse_args()
print(json.dumps(build_weight_manifest(a.model, architecture=a.architecture, quantization=a.quantization, tokenizer=a.tokenizer, source_checkpoint=a.source_checkpoint, license_name=a.license_name, provenance=a.provenance), indent=2, sort_keys=True))
