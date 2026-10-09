#!/usr/bin/env python3
"""Authorized second IBM job; reuse original fixed-circuit guarded physical sampler."""
from pathlib import Path
import ibm_eternal_dragon_longer_probe as prior
prior.TAG = 'navisworld-20261009-second-final-dragon-onejob-v1'
prior.OUT = Path('_ibm_second_final_dragon_20261009')
prior.QPU_HARD_CAP = 120
if __name__ == '__main__':
    prior.run()
