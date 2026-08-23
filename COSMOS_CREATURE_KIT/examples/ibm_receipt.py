#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from beastbox.creature.bridges import ibm_receipt_from_resident
if len(sys.argv) != 2:
    raise SystemExit("usage: ibm_receipt.py SANITIZED_IBM_RECEIPT.json")
value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(json.dumps(ibm_receipt_from_resident(value).to_dict(), indent=2, sort_keys=True))
