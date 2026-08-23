#!/usr/bin/env python3
import json
from beastbox.creature.bridges import classical_receipt
from beastbox.creature.loops import build_state_packet
receipt = classical_receipt(42)
print(json.dumps(build_state_packet(receipt), indent=2, sort_keys=True, default=str))
