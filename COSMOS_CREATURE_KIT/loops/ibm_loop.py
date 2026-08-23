#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from beastbox.creature.bridges import ibm_receipt_from_resident
from beastbox.creature.loops import build_state_packet

if len(sys.argv) != 2:
    raise SystemExit("usage: ibm_loop.py SANITIZED_IBM_RECEIPT.json")
raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
receipt = ibm_receipt_from_resident(raw)
print(json.dumps(build_state_packet(receipt), indent=2, sort_keys=True, default=str))
