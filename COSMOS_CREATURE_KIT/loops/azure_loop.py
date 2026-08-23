#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from beastbox.creature.bridges import azure_receipt_from_payload
from beastbox.creature.loops import build_state_packet

if len(sys.argv) != 2:
    raise SystemExit("usage: azure_loop.py SANITIZED_AZURE_PAYLOAD.json")
raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
receipt = azure_receipt_from_payload(raw)
print(json.dumps(build_state_packet(receipt), indent=2, sort_keys=True, default=str))
