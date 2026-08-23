#!/usr/bin/env python3
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from beastbox.creature.project import create_creature_project
from beastbox.creature.doctor import doctor_project

with TemporaryDirectory() as tmp:
    root = create_creature_project("Nova", Path(tmp))
    print(json.dumps(doctor_project(root), indent=2, sort_keys=True))
