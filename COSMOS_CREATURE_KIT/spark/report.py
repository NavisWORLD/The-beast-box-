#!/usr/bin/env python3
import json
from beastbox.creature.spark import zero_state_report
print(json.dumps(zero_state_report(), indent=2, sort_keys=True))
