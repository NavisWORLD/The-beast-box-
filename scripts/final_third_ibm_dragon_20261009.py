#!/usr/bin/env python3
"""One NEW idempotent, quota-guarded physical IBM hardware birth. No simulation fallback."""
from pathlib import Path
import ibm_eternal_dragon_longer_probe as probe
probe.TAG='navisworld-20261009-third-unique-final-dragon-onejob-v1'
probe.OUT=Path('_ibm_third_final_dragon_20261009')
probe.QPU_HARD_CAP=120
if __name__=='__main__': probe.run()
