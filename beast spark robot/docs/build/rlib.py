"""Shared headless rendering + labelling helpers for the ZEREF SPARK guides.
DESIGN TARGET — not printed or test-fitted."""
import os, glob, textwrap
import numpy as np
import pyvista as pv
from PIL import Image, ImageDraw, ImageFont
pv.OFF_SCREEN = True
ROOT = "/workspace/zeref-spark"
STL = f"{ROOT}/out/stl/assembly_coords"
FD = "/usr/share/fonts/truetype/dejavu/"
def font(sz, bold=False):
    return ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), sz)
LABEL = "DESIGN TARGET — not printed or test-fitted · CONCEPT DESIGN / NOT BUILT HARDWARE"
CREDIT = "System logic: Cory Davis (NavisWORLD) · CAD geometry: AI-generated (CadQuery) · PX = third-party module proxy"

# style() copied from cad/render.py
_src = open(f"{ROOT}/cad/render.py").read()
_a = _src.index("NAVY, GLOSS"); _b = _src.index("def load(")
exec(_src[_a:_b])

_cache = {}
def mesh(stem):
    if stem not in _cache:
        p = f"{STL}/{stem}.stl"
        if not os.path.exists(p):
            p = f"{STL}/proxy/{stem}.stl"
        _cache[stem] = pv.read(p).compute_normals(split_vertices=True, feature_angle=35)
    return _cache[stem]

def all_stems():
    s = [os.path.basename(f)[:-4] for f in sorted(glob.glob(f"{STL}/*.stl"))]
    s += [os.path.basename(f)[:-4] for f in sorted(glob.glob(f"{STL}/proxy/*.stl"))]
    return s

def plotter(w=1400, h=1100, bg="light"):
    p = pv.Plotter(off_screen=True, window_size=(w, h))
    if bg == "light":
        p.set_background("#eef1f7", top="#ffffff")
    else:
        p.set_background("#05060f", top="#1a1440")
    p.enable_anti_aliasing("ssaa")
    p.add_light(pv.Light(position=(-400, -600, 700), intensity=0.8))
    p.add_light(pv.Light(position=(500, 300, 400), intensity=0.45))
    p.add_light(pv.Light(position=(0, 600, 100), intensity=0.3))
    return p

def visible_style(n):
    st = dict(style(n))
    # on light background boost dark parts slightly so silhouettes read
    if st.get("color") in ("#161c33", "#1f2747", "#0d1020", "#0b0e1a", "#04060b", "#1a2140", "#1b1b22"):
        st["color"] = {"#04060b": "#202838", "#1b1b22": "#3a3a44"}.get(st["color"], "#2a3560")
    if "opacity" in st and st["opacity"] < 0.5:
        st["opacity"] = 0.55
    return st

def project(p, pts, h):
    ren = p.renderer; out = []
    for q in pts:
        ren.SetWorldPoint(float(q[0]), float(q[1]), float(q[2]), 1.0)
        ren.WorldToDisplay()
        x, y, _ = ren.GetDisplayPoint()
        out.append((x, h - y))
    return out

def render_scene(items, cam, w=1400, h=1100, offsets=None, highlight=None, ghost_others=False, bg="light", edges=False):
    """items: list of stems. highlight: set of stems drawn bright with edges; others ghosted if ghost_others."""
    p = plotter(w, h, bg)
    anchors = {}
    for n in items:
        m = mesh(n)
        if offsets:
            m = m.translate(offsets(n), inplace=False)
        st = visible_style(n) if bg == "light" else dict(style(n))
        if highlight is not None:
            if n in highlight:
                st = dict(st); st["show_edges"] = False
                st.pop("opacity", None) if "tube" not in n and "window" not in n else None
            elif ghost_others:
                st = dict(color="#9aa3b5", opacity=0.13)
        p.add_mesh(m, **st)
        anchors[n] = np.array(m.center)
    if isinstance(cam, dict):
        p.reset_camera()
        f = np.array(p.camera.focal_point); dist = np.linalg.norm(np.array(p.camera.position) - f)
        v = np.array(cam["dir"], float); v /= np.linalg.norm(v)
        p.camera.position = tuple(f + v * dist); p.camera.up = (0, 0, 1)
        p.reset_camera(); p.camera.zoom(cam.get("zoom", 1.0))
    elif cam == "iso_fit":
        p.view_isometric(); p.camera.azimuth = -60; p.camera.elevation = 15; p.reset_camera(); p.camera.zoom(1.15)
    elif isinstance(cam, str):
        getattr(p, cam)(); p.reset_camera()
    else:
        p.camera_position = cam
    img = p.screenshot(return_img=True)
    pts = project(p, list(anchors.values()), h)
    p.close()
    return Image.fromarray(img), dict(zip(anchors.keys(), pts))

def callout_canvas(img, anchors, labels, margin=430, title=None, sub=None, numbered=False, fs=22):
    """Put labels in left/right margins with leader lines to anchors. labels: {stem: text}."""
    W, H = img.size
    top = 110 if title else 20
    bot = 70
    C = Image.new("RGB", (W + 2 * margin, H + top + bot), "white")
    C.paste(img, (margin, top))
    d = ImageDraw.Draw(C)
    items = [(s, labels[s], anchors[s]) for s in labels if s in anchors]
    left = sorted([i for i in items if i[2][0] < W / 2], key=lambda t: t[2][1])
    right = sorted([i for i in items if i[2][0] >= W / 2], key=lambda t: t[2][1])
    f = font(fs); fb = font(fs, True)
    for side, group in (("L", left), ("R", right)):
        n = len(group)
        if not n: continue
        step = (H - 20) / max(n, 1)
        step = min(step, 70)
        y0 = top + (H - step * n) / 2 + step / 2
        for k, (s, txt, (ax, ay)) in enumerate(group):
            y = y0 + k * step
            ax2, ay2 = ax + margin, ay + top
            lines = textwrap.wrap(txt, 30 if not numbered else 40)[:2]
            if side == "L":
                tx = 12; lx = margin - 12
                d.line([(lx, y), (ax2, ay2)], fill="#ff2d9b", width=2)
            else:
                tx = W + margin + 26; lx = W + margin + 12
                d.line([(lx, y), (ax2, ay2)], fill="#ff2d9b", width=2)
            d.ellipse([ax2 - 5, ay2 - 5, ax2 + 5, ay2 + 5], fill="#ff2d9b")
            for j, ln in enumerate(lines):
                d.text((tx, y - fs * 0.65 * len(lines) + j * (fs + 3)), ln, fill="#101828", font=fb if j == 0 else f)
    if title:
        d.rectangle([0, 0, C.width, 95], fill="#101633")
        d.text((24, 14), title, fill="#7ff6ff", font=font(38, True))
        if sub: d.text((24, 60), sub, fill="#e0e6ff", font=font(20))
    d.rectangle([0, C.height - 60, C.width, C.height], fill="#101633")
    d.text((24, C.height - 52), LABEL, fill="#ff9ae8", font=font(19, True))
    d.text((24, C.height - 28), CREDIT, fill="#c9d3ff", font=font(16))
    return C

# explode() copied from cad/render.py
_a = _src.index("def explode(n):"); _b = _src.index("finish(scene(load(True), explode)")
exec(_src[_a:_b])
