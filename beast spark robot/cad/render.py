"""Render ZEREF SPARK STLs (assembly coords). DESIGN TARGET — not printed or test-fitted."""
import os, glob
import numpy as np
import pyvista as pv
pv.OFF_SCREEN = True
BASE = os.path.join(os.path.dirname(__file__), "..")
STL = os.path.join(BASE, "out", "stl", "assembly_coords")
OUT = os.path.join(BASE, "renders")
os.makedirs(OUT, exist_ok=True)
LABEL = "ZEREF SPARK  |  DESIGN TARGET — not printed or test-fitted  |  CONCEPT DESIGN / NOT BUILT HARDWARE"

NAVY, GLOSS = "#161c33", "#1f2747"
def style(n):
    if "crystal_sample" in n: return dict(color="#b48cff", opacity=0.75, specular=1.0, specular_power=80, smooth_shading=False)
    if "window" in n: return dict(color="#cfefff", opacity=0.35, specular=1.0)
    if "light_shield" in n: return dict(color="#1a2140", specular=0.6, specular_power=30, smooth_shading=True)
    if "station_led_plug" in n: return dict(color="#d9dde8")
    if "sensor_mount" in n or "driver_bay" in n: return dict(color="#5a6280")
    if "dark_reference" in n: return dict(color="#050505")
    if "ptfe" in n: return dict(color="#ffffff", ambient=0.5)
    if "AS7341" in n: return dict(color="#20242c")
    if "led_uv365" in n: return dict(color="#8a2cff", ambient=1.0)
    if "led_ir940" in n: return dict(color="#5a0010", ambient=0.6)
    if "led_white" in n: return dict(color="#ffffff", ambient=1.0)
    if "pogo" in n: return dict(color="#d4a52a", specular=1.0)
    if "magnet" in n: return dict(color="#c0c0c0", specular=1.0)
    if "reed" in n: return dict(color="#a8e0ff", opacity=0.7)
    if "uv_cut" in n: return dict(color="#ffd27a", opacity=0.5)
    if "powerboost" in n: return dict(color="#1d3fa0")
    if "slide_switch" in n: return dict(color="#222222")
    if "visor" in n: return dict(color="#04060b", opacity=0.62, specular=1.0, specular_power=60, smooth_shading=True)
    if "eye_lightpipe" in n or "ring_diffuser" in n: return dict(color="#3ff4ff", ambient=1.0, diffuse=0.2)
    if "accent_lightpipe" in n: return dict(color="#ff3fd8", ambient=0.9)
    if "center_lens" in n: return dict(color="#c43cff", ambient=0.8, specular=0.6)
    if "rim_diffuser" in n: return dict(color="#7a3cff", ambient=0.55, diffuse=0.3)
    if "pedestal" in n: return dict(color="#1b1b22", specular=0.15)
    if "support_tube" in n: return dict(color="#bfe9ff", opacity=0.35, specular=1.0)
    if "pod_cap" in n: return dict(color="#0b0e1a", specular=0.9, specular_power=40, smooth_shading=True)
    if "bulkhead" in n or "sled" in n or "carrier" in n: return dict(color="#5a6280")
    if "chest_core_housing" in n or "neck" in n: return dict(color="#0d1020", specular=0.8)
    if "shell" in n or "ear_" in n: return dict(color=GLOSS if "front" in n else NAVY, specular=0.45,
                                                   specular_power=25, smooth_shading=True)
    if n.startswith("PX_"):
        if "led" in n: return dict(color="#e8e8ff")
        if "speaker" in n: return dict(color="#777777")
        if "lipo" in n: return dict(color="#c9a23a")
        return dict(color="#1e7a4e")
    return dict(color=NAVY, specular=0.4, smooth_shading=True)

def load(proxies=False):
    meshes = {}
    for f in sorted(glob.glob(os.path.join(STL, "*.stl"))):
        if "ZS-605" in f: continue
        meshes[os.path.basename(f)[:-4]] = pv.read(f).compute_normals(split_vertices=True, feature_angle=35)
    if proxies:
        for f in sorted(glob.glob(os.path.join(STL, "proxy", "*.stl"))):
            if "ptfe" in f: continue
            meshes[os.path.basename(f)[:-4]] = pv.read(f)
    return meshes

def plotter():
    p = pv.Plotter(off_screen=True, window_size=(1600, 1600))
    p.set_background("#05060f", top="#1a1440")
    p.enable_anti_aliasing("ssaa")
    p.add_light(pv.Light(position=(-400, -600, 700), intensity=0.9))
    p.add_light(pv.Light(position=(500, 300, 400), intensity=0.45, color="#a080ff"))
    p.add_light(pv.Light(position=(0, 600, 100), intensity=0.35, color="#40e0ff"))
    return p

def finish(p, name, title, cam):
    p.add_text(title, position="upper_left", font_size=14, color="#e0f7ff")
    p.add_text(LABEL, position="lower_edge", font_size=9, color="#ff9ae8")
    p.camera_position = cam
    p.show(screenshot=os.path.join(OUT, name), auto_close=True)
    print("wrote", name)

def scene(meshes, offsets=None, skip=()):
    p = plotter()
    for n, m in meshes.items():
        if any(s in n for s in skip): continue
        mm = m.translate(offsets(n), inplace=False) if offsets else m
        p.add_mesh(mm, **style(n))
    return p

C = (0, 0, 150)
m = load()
finish(scene(m), "01_hero_three_quarter.png", "ZEREF SPARK — assembled (hero 3/4)", [(-420, -620, 330), C, (0, 0, 1)])
finish(scene(m), "02_front.png", "Front", [(0, -900, 150), C, (0, 0, 1)])
finish(scene(m), "03_side_right.png", "Right side", [(900, 0, 150), C, (0, 0, 1)])
finish(scene(m), "04_back.png", "Back (speaker grille, ESP32 vents)", [(350, 800, 260), C, (0, 0, 1)])

def explode(n):
    o = np.zeros(3)
    if any(k in n for k in ("head", "visor", "face_carrier", "eye_", "accent", "pod", "ear_")): o[2] += 110
    if "neck" in n: o[2] += 55
    if "shell_front" in n or "visor" in n: o[1] -= 70
    if "shell_back" in n: o[1] += 70
    if "visor" in n: o[1] -= 50
    if "face_carrier" in n: o[1] -= 30
    if "eye_" in n: o[1] -= 80
    if "chest" in n: o[1] -= 110 + (15 if "diffuser" in n else 30 if "lens" in n else 0)
    if "sled" in n: o[1] -= 40
    if "pod" in n or "ear_" in n:
        s = -1 if n.endswith("_L") or "_L_" in n else 1
        o[0] += s * (40 + (20 if "rim" in n else 35 if "cap" in n else 0))
        if "ear_" in n: o[2] += 40
    if "arm" in n: o[0] += (-45 if n.endswith("L") else 45)
    if "leg" in n: o[2] -= 30; o[0] += (-15 if n.endswith("L") else 15)
    st = any(k in n for k in ("ZS-60", "crystal", "AS7341", "uv_cut", "pogo", "reed", "magnet", "station", "led_white", "led_uv365", "led_ir940"))
    if "pedestal" in n or st: o[2] -= 90
    if st:
        o[1] -= 130
        if any(k in n for k in ("light_shield", "pogo_pads", "magnet")): o[2] += 95
        if any(k in n for k in ("sensor_mount", "AS7341", "uv_cut")): o[2] += 135
        if "crystal" in n: o[2] += 40
        if any(k in n for k in ("led_plug", "station_led_board", "led_white", "led_uv", "led_ir")): o[2] -= 30
        if "window" in n: o[2] -= 25
        if "driver" in n: o[2] -= 25
    if any(k in n for k in ("109_battery", "lipo", "powerboost")): o[1] += 30
    if "tube" in n: o[2] -= 55
    if "accent" in n: o[2] += 30
    return o
finish(scene(load(True), explode), "05_exploded.png", "Exploded assembly (parts + purchased-part proxies)",
       [(-750, -1000, 450), (0, 0, 130), (0, 0, 1)])

# crystal station close-up: section through x=0 of pedestal + shield + plug, crystal whole
def station_closeup():
    mm = load(True)
    p = plotter()
    cut_these = ("pedestal", "light_shield", "station_led_plug", "sensor_mount", "window", "uv_cut")
    for n, m in mm.items():
        if any(k in n for k in ("head", "visor", "face_carrier", "eye_", "accent", "pod", "ear_", "neck", "109", "lipo", "powerboost", "switch", "gnss", "speaker", "max98357a", "led_ring12_pod")):
            continue
        if any(k in n for k in cut_these):
            m = m.clip(normal=(1, 0, 0), origin=(0, 0, 0), invert=True)
        p.add_mesh(m, **style(n))
    p.add_text("Crystal-reading station (section x=0): white / 365 nm UV / 940 nm IR LEDs below window,\n"
               "crystal in light-tight cup, AS7341 looking down from removable shield",
               position="upper_left", font_size=12, color="#e0f7ff")
    p.add_text("Raw AS7341 counts = MEASURED | ratios = DERIVED | crystal-type label = ESTIMATE\n"
               "DESIGN TARGET - not printed or test-fitted | CONCEPT DESIGN / NOT BUILT HARDWARE",
               position="lower_left", font_size=10, color="#ff9ae8")
    p.camera_position = [(260, -120, 70), (0, -46, 0), (0, 0, 1)]
    p.show(screenshot=os.path.join(OUT, "10_crystal_station_closeup.png"), auto_close=True)
    print("wrote 10_crystal_station_closeup.png")
station_closeup()

# section: hide front halves to show the nervous system inside
mp = load(True)
finish(scene(mp, skip=("shell_front", "visor", "chest", "eye_", "face_carrier", "sled", "PX_RB-002", "PX_RB-004", "PX_RB-005", "PX_led_eye", "PX_led_ring12_chest", "accent")),
       "06_section_internals_front_removed.png", "Internals — front shells removed (ESP32-S3 cradle, bulkheads, pods)",
       [(-250, -800, 200), C, (0, 0, 1)])
finish(scene(mp, skip=("shell_front", "visor", "eye_", "accent")),
       "07_section_sensor_sled_chest.png", "Front shells removed — sensor sled + chest core + face carrier",
       [(300, -750, 160), (0, 0, 140), (0, 0, 1)])
finish(scene(m), "08_top.png", "Top (ears splay 8° outward)", [(0, -80, 1000), C, (0, 1, 0)])
finish(scene(mp, skip=("shell_back",)), "09_rear_internals_back_removed.png",
       "Rear — back shells removed (ESP32-S3 DevKitC-1 in cradle, speaker, amp, GNSS, optional LiPo)",
       [(250, 800, 200), C, (0, 0, 1)])
