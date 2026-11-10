import sys, json
sys.path.insert(0, "/workspace/zeref-spark/docs/build")
from rlib import *
from partmeta import M
IMG = f"{ROOT}/docs/img"
ALL = [s for s in all_stems() if s not in ("ZS-605_dark_reference_plug", "PX_ptfe_white_reference_25x3")]
def short(s):
    pn = s.split("_")[0] if s.startswith("ZS") else "PX"
    return f"{pn} {M[s][0]}"

# ---------------- 1. numbered exploded view
img, anc = render_scene(ALL, [(-900, -1250, 520), (0, -20, 110), (0, 0, 1)], 1700, 2000, offsets=explode)
order = sorted(ALL, key=lambda s: (s[:2] != "ZS", s))
num = {s: i + 1 for i, s in enumerate(order)}
labels = {s: f"{num[s]}  {s.split('_')[0] if s.startswith('ZS') else 'PX'}" for s in ALL}
C = callout_canvas(img, anc, labels, margin=230, title="ZEREF SPARK — exploded view, every part numbered",
                   sub="Numbers match the legend table in the Assembly Guide (Parts Catalog section)", fs=20)
C.save(f"{IMG}/exploded_numbered.png")
json.dump([[num[s], s, M[s][0]] for s in order], open(f"{IMG}/exploded_legend.json", "w"), indent=0)

# ---------------- 2. sub-assemblies
G = {k: [s for s in ALL if M[s][5] == k] for k in ("head", "pods", "torso", "limbs", "pedestal", "station", "power")}
SUB = {
 "sub_head": (G["head"] + G["power"], {"dir": (-1.0, -1.4, 0.7)}, "Head sub-assembly (incl. power bay)", lambda n: explode(n) * np.array([0, 1.0, 0]) ),
 "sub_ear_pods": (G["pods"], {"dir": (-1.2, -1.0, 0.5)}, "Ear pods + ears (left = mic, right = light)",
                  lambda n: np.array([(-1 if ("_L" in n or "podL" in n or "inmp" in n) else 1) * (25 if "rim" in n else 45 if "cap" in n else 0), 0, 40 if "ear_" in n else 0])),
 "sub_torso_chest": (G["torso"], {"dir": (-1.0, -1.6, 0.5)}, "Torso + chest core + sensor sled + ESP32-S3 cradle",
                     lambda n: np.array([0, -60 if "front" in n else 60 if "back" in n else -110 - (15 if "diffuser" in n else 30 if "lens" in n else 0) if ("chest" in n or "ring12_chest" in n) else -35 if ("sled" in n or "imu" in n or "bme" in n) else -80 if "max30102" in n else 0, 0])),
 "sub_limbs": (G["limbs"] + ["ZS-301_torso_shell_front"], {"dir": (-1.0, -1.6, 0.4)}, "Limbs — flanged pegs captured by the torso split",
               lambda n: np.array([(-30 if n.endswith("L") else 30) if "arm" in n else 0, 0, -25 if "leg" in n else 0])),
 "sub_pedestal_station": (G["pedestal"] + G["station"], {"dir": (0.9, -1.4, 0.8)}, "Pedestal + crystal-reading station",
                          lambda n: np.array([0, 0, (70 if any(k in n for k in ("shield", "pogo_pads", "magnet")) else 115 if any(k in n for k in ("sensor_mount", "AS7341", "uv_cut")) else 35 if "crystal_sample" in n else -45 if any(k in n for k in ("led_plug", "station_led", "led_white", "led_uv", "led_ir")) else -20 if "window" in n else -30 if "driver" in n else 0)])),
 "sub_power": (G["power"] + ["ZS-103_head_bulkhead", "PX_max98357a_amp", "PX_usbc_breakout_pedestal"], {"dir": (1.0, 1.6, 0.5)}, "Power: protected LiPo + PowerBoost 1000C + EN switch (+ pedestal USB-C)",
               lambda n: np.array([0, 25 if any(k in n for k in ("lipo", "109", "powerboost")) else 50 if "switch" in n else 0, 0])),
}
for key, (items, cam, title, off) in SUB.items():
    img, anc = render_scene(items, cam, 1300, 1100, offsets=off)
    C = callout_canvas(img, anc, {s: short(s) for s in items}, margin=420, title=title, sub="Labels: part number + name (PX = third-party module proxy)", fs=19)
    C.save(f"{IMG}/{key}.png"); print("wrote", key)
