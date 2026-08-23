#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from beastbox.creature.bridges import azure_receipt_from_payload, classical_receipt, ibm_receipt_from_resident
from beastbox.creature.loops import build_state_packet

p = argparse.ArgumentParser()
p.add_argument("provider", choices=["classical", "ibm", "azure"])
p.add_argument("--input")
p.add_argument("--seed", type=int, default=42)
a = p.parse_args()
if a.provider == "classical":
    receipt = classical_receipt(a.seed)
else:
    if not a.input:
        raise SystemExit("--input is required for IBM/Azure sanitized receipts")
    raw = json.loads(Path(a.input).read_text(encoding="utf-8"))
    receipt = ibm_receipt_from_resident(raw) if a.provider == "ibm" else azure_receipt_from_payload(raw)
print(json.dumps(build_state_packet(receipt), indent=2, sort_keys=True, default=str))
