#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from beastbox.creature.bridges import azure_receipt_from_payload
if len(sys.argv) != 2:
    raise SystemExit("usage: azure_receipt.py SANITIZED_AZURE_PAYLOAD.json")
value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(json.dumps(azure_receipt_from_payload(value).to_dict(), indent=2, sort_keys=True))
