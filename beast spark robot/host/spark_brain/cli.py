"""python -m spark_brain {replay FILE | serial PORT | demo}  (AI-WRITTEN GLUE)

replay: feed a captured JSON-lines log through the brain (no device needed).
serial: talk to a real Spark over USB (needs pyserial). Sends expression commands only.
demo  : SIMULATION frames (clearly labeled) through the full brain once.
--beastbox-features DIR writes features into Cory's Beast Box FeatureStore (his BEASTBOX_FEATURE_DIR) so a Beast Box
started with BEASTBOX_LIVE_ROUTING=on routes the Spark's signals itself.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .brain import SparkBrain
from .link import SerialLink, iter_frames
from . import simulate
from .speech import SpeechSender


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="spark_brain")
    ap.add_argument("mode", choices=["replay", "serial", "demo"])
    ap.add_argument("target", nargs="?")
    ap.add_argument("--data", default=str(Path.home() / ".zeref-spark"))
    ap.add_argument("--beastbox-features", default=None)
    ap.add_argument("--psi", action="store_true", help="add the optional CST psi readout (DERIVED, never drives hardware)")
    ap.add_argument("--speak", action="store_true", help="speak the approved mouth's replies on the Spark speaker")
    ap.add_argument("--say", default=None, help="demo/serial: one owner line to answer (and speak with --speak)")
    a = ap.parse_args(argv)
    if a.mode == "demo":
        clock = iter(range(10**9))
        brain = SparkBrain(a.data, feature_dir=a.beastbox_features, clock=lambda: 1_800_000_000.0 + next(clock) * 0.25,
                           psi=a.psi, speech=a.speak, approve_mouth=lambda key, cap: key == "reference")
        brain.mouths.activate("reference")   # demo only: the built-in reference mouth (no model)
        brain.bridge.sim_drive = True
        for f in simulate.frames(35):
            brain.on_frame(f)
        for f in simulate.crystal_frames():
            brain.on_frame(f)
        step, cmds = brain.tick()
        out = {"tally": step["tally"], "merged_tally": step["merged"]["tally"], "phos": step["phos"],
               "heart": step["heart"], "commands": cmds, "simulation": step.get("simulation")}
        if "psi" in step:
            out["psi"] = {k: step["psi"][k] for k in ("psi", "terms", "label", "drives_hardware")}
        if a.say:
            t = brain.talk(a.say)
            out["talk"] = {k: t[k] for k in ("reply", "mouth") if k in t} | ({"speech": t["speech"]} if "speech" in t else {})
        print(json.dumps(out, indent=1, default=str))
        return 0
    brain = SparkBrain(a.data, feature_dir=a.beastbox_features, psi=a.psi, speech=a.speak)
    if a.mode == "replay":
        lines = Path(a.target).read_text(encoding="utf-8").splitlines()
        for f in iter_frames(lines):
            brain.on_frame(f)
        print(json.dumps(brain.tick()[0]["tally"]))
        return 0
    link = SerialLink(a.target)
    sender = SpeechSender(link.send)
    if a.say:
        brain.talk(a.say)
        sender.start(brain.pending_speech)
    last = 0.0
    for f in iter_frames(link.lines()):
        sender.on_frame(f)
        for c in brain.on_frame(f):
            link.send(c)
        if time.time() - last >= 1.0:
            last = time.time()
            step, cmds = brain.tick()
            for c in ["PING", *cmds]:
                link.send(c)
            print(json.dumps({"tally": step["tally"], "phos": round(step["phos"], 4)}), file=sys.stderr)
    return 0
