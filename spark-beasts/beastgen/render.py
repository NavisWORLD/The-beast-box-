"""Genome + stage -> 64x64 pixel-art sprite (Pillow + numpy), modular parts.

Pipeline: parts (masks with material + z + light dome) -> stage-stable pattern overlay ->
5-tone ramp shading (deep/shadow/mid/light/highlight) with 4x4 ordered dither -> selective
inner outlines -> rim light on the shadow-side silhouette -> dark exterior outline ->
face (big cute eyes, pose-aware) -> contact shadow -> glow sparkles.
11 body plans (pup, fox, sprout, moth, axolotl, golem, dragonling, bird, fish, serpent, biped);
poses: front / three_quarter / side (drawn facing right, mirrored by genome['facing']).
All colours are snapped to GBA BGR555 (5 bits per channel).
"""
from __future__ import annotations

import colorsys
import math

import numpy as np
from PIL import Image, ImageDraw

from .genome import PALETTES, Stream

W = 64
CX = 31.5
G = 61  # ground line (feet bottom)
BASE, ALT, BELLY, ACCENT, DARK, GLOW, CHEEK, EYE, IRIS, WHITE, NOSE, BEAK = range(1, 13)
STAGE_K = {1: 0.60, 2: 0.80, 3: 1.0}
NAVY = (14, 20, 44)


def snap(rgb):
    return tuple(min(248, int(round(c / 255 * 31)) * 8) for c in rgb)


def hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360, max(0, min(1, s)), max(0, min(1, v)))
    return (int(r * 255), int(g * 255), int(b * 255))


DEEP, SHADOW, MID, LIGHT, HI, LINE = range(6)


def ramp(h, s, v):
    """deep / shadow / mid / light / highlight / line; shadows drift cool, lights drift warm (GBA style)."""
    cool = 12 if 60 < h % 360 < 240 else -14
    warm = -(8 if 60 < h % 360 < 240 else -6)
    deep = tuple(int(0.8 * a + 0.2 * b) for a, b in zip(hsv(h + 1.8 * cool, s * 1.1 + 0.16, v * 0.46), NAVY))
    sh = hsv(h + cool, s * 1.05 + 0.08, v * 0.68)
    mid = hsv(h, s, v)
    li = hsv(h + warm, s * 0.80, min(1, v * 1.16 + 0.05))
    hi = hsv(h + 1.6 * warm, s * 0.45, min(1, v * 1.32 + 0.16))
    ln = tuple(int(0.45 * a + 0.55 * b) for a, b in zip(hsv(h + 15, s * 1.1 + 0.15, v * 0.34), NAVY))
    return [snap(deep), snap(sh), snap(mid), snap(li), snap(hi), snap(ln)]


GLOW_HSV = {"gold": (46, .85, 1.0), "cyan": (184, .80, 1.0)}


def palette(gen) -> dict:
    p = PALETTES[gen["island"]]
    gg = gen["genes"]
    dh = (gg["hue"] - 0.5) * 30
    ds = (gg["sat"] - 0.5) * 0.25
    dv = (gg["val"] - 0.5) * 0.18
    adj = lambda t: (t[0] + dh, t[1] + ds, t[2] + dv)  # noqa: E731
    glow = p["glow"] if gen["glow"] == "native" else GLOW_HSV[gen["glow"]]
    pal = {BASE: ramp(*adj(p["base"])), ALT: ramp(*adj(p["alt"])), BELLY: ramp(*adj(p["belly"])),
           ACCENT: ramp(*adj(p["accent"])), GLOW: ramp(glow[0], glow[1] * 0.85, glow[2]),
           CHEEK: ramp(350, .45, 1.0), DARK: ramp(p["base"][0] + 20, .5, .32), NOSE: ramp(240, .3, .2),
           BEAK: ramp(40, .72, .97), WHITE: ramp(220, .04, .97)}
    gl = hsv(*glow)
    pal[GLOW] = [snap(hsv(glow[0], glow[1], .7)), snap(hsv(glow[0], glow[1], .85)), snap(gl), snap(hsv(glow[0], glow[1] * .35, 1)),
                 (248, 248, 248), snap(hsv(glow[0], glow[1], .45))]
    pal["outline"] = snap(tuple(int(0.5 * a + 0.5 * b) for a, b in zip(pal[BASE][LINE], NAVY)))
    rim = GLOW_HSV["cyan"] if gen["glow"] != "gold" else GLOW_HSV["gold"]
    pal["rim"] = hsv(rim[0], rim[1] * 0.7, 1.0)
    pal["iris"] = snap(gl) if gen["glow"] != "native" or gen["island"] != "Cinder Drift" else snap(hsv(40, .9, 1))
    return pal


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self):
        self.mat = np.zeros((W, W), np.int16)
        self.part = np.zeros((W, W), np.int16)
        self.light = np.zeros((W, W), np.float32)
        self.flat = np.zeros((W, W), bool)
        self.n = 0
        yy, xx = np.mgrid[0:W, 0:W]
        self.xx, self.yy = xx.astype(np.float32), yy.astype(np.float32)
        self.overlay = []  # (x, y, rgb) drawn after outline
        self.layer = np.zeros((W, W), np.int8)  # 1 = back (wings/tail), 2 = main
        self.cur = "main"
        self.skip_main = False
        self.bias = 0.0  # added to the light of every part drawn while set (far limbs / far wing)

    def mask(self, fn) -> np.ndarray:
        im = Image.new("L", (W, W), 0)
        fn(ImageDraw.Draw(im))
        return np.array(im) > 0

    def add(self, m, material, centre=None, r=None, flat=False, light=None, outline=True, bias=0.0):
        if not m.any() or (self.skip_main and self.cur == "main"):
            return m
        self.layer[m] = 1 if self.cur == "back" else 2
        self.n += 1
        if light is None:
            if centre is None:
                ys, xs = np.nonzero(m)
                centre = (xs.mean(), ys.mean())
                r = max(2.0, 0.5 * max(np.ptp(xs) + 1, np.ptp(ys) + 1))
            dx = (self.xx - centre[0]) / r
            dy = (self.yy - centre[1]) / r
            light = -(0.55 * dx + 0.85 * dy) - 0.25 * (dx * dx + dy * dy)
        self.mat[m] = material
        if outline:
            self.part[m] = self.n
        else:
            self.part[m & (self.part == 0)] = self.n
        self.light[m] = (light[m] if hasattr(light, "shape") else light) + bias + self.bias
        self.flat[m] = flat
        return m

    # shape helpers ---------------------------------------------------
    def ell(self, cx, cy, rx, ry):
        return self.mask(lambda d: d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255))

    def poly(self, pts):
        return self.mask(lambda d: d.polygon([tuple(p) for p in pts], fill=255))

    def line(self, pts, w):
        def f(d):
            d.line([tuple(p) for p in pts], fill=255, width=max(1, int(round(w))))
            for x, y in pts:
                rr = w / 2
                d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=255)
        return self.mask(f)

    def chain(self, pts_r):
        """Union of circles; light computed from nearest circle (for tails / serpent bodies)."""
        m = np.zeros((W, W), bool)
        best = np.full((W, W), 1e9, np.float32)
        light = np.zeros((W, W), np.float32)
        self.chain_dy = np.zeros((W, W), np.float32)
        for x, y, r in pts_r:
            c = self.ell(x, y, r, r)
            m |= c
            d = ((self.xx - x) ** 2 + (self.yy - y) ** 2) / max(r, 1) ** 2
            upd = c & (d < best)
            dx, dy = (self.xx - x) / max(r, 1), (self.yy - y) / max(r, 1)
            l = -(0.55 * dx + 0.85 * dy) - 0.25 * (dx * dx + dy * dy)
            light[upd] = l[upd]
            self.chain_dy[upd] = dy[upd]
            best[upd] = d[upd]
        return m, light


def mirror_pts(pts):
    return [(63 - x, y) for x, y in pts]


# ---------------------------------------------------------------- parts
def flame_pts(x, y, w, h, lean=0.0, tongues=3):
    pts = [(x - w / 2, y)]
    for i in range(tongues):
        t0 = (i + 0.5) / tongues
        tx = x - w / 2 + w * t0 + lean * h * 0.35
        th = h * (0.6 + 0.4 * math.sin(math.pi * t0))
        pts += [(x - w / 2 + w * (i / tongues) + w / tongues * 0.15, y - th * 0.45), (tx, y - th)]
    pts += [(x + w / 2, y), (x, y + w * 0.25)]
    return pts


def leaf(cv, x, y, length, ang, width, mat=ACCENT):
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for i in range(13):
        t = i / 12
        ww = width * math.sin(math.pi * t)
        pts.append((x + ca * length * t - sa * ww, y + sa * length * t + ca * ww))
    for i in range(12, -1, -1):
        t = i / 12
        ww = width * math.sin(math.pi * t) * 0.9
        pts.append((x + ca * length * t + sa * ww, y + sa * length * t - ca * ww))
    m = cv.poly(pts)
    cv.add(m, mat)
    vein = cv.line([(x, y), (x + ca * length * 0.8, y + sa * length * 0.8)], 1) & m
    cv.light[vein] -= 0.8


def crystal(cv, x, y, h, w, ang, mat=ACCENT):
    ca, sa = math.cos(ang), math.sin(ang)
    tip = (x + ca * h, y + sa * h)
    l = (x - sa * w, y + ca * w)
    r = (x + sa * w, y - ca * w)
    m = cv.poly([l, tip, r])
    cv.add(m, mat)
    half = cv.poly([(x, y), tip, r]) & m
    cv.light[half] += 0.7  # bright facet
    return m


FRONT_EARS = {"crown", "leaf"}


def ears(cv, gen, hx, hy, hr, k, stage, layer="back"):
    kind, size = gen["ears"], gen["genes"]["ear_size"]
    if (kind in FRONT_EARS) != (layer == "front"):
        return
    eh = (4 + 6 * size) * k * (0.8 if stage == 1 else 1.0 + 0.15 * (stage == 3))
    for side in (-1, 1):
        bx = hx + side * hr * 0.55
        by = hy - hr * 0.62
        if kind == "pointy":
            pts = [(bx - side * eh * 0.45, by + 2), (bx + side * eh * 0.25, by - eh), (bx + side * eh * 0.55, by + 1.5)]
            cv.add(cv.poly(pts), BASE)
            inner = [(bx - side * eh * 0.15, by + 1), (bx + side * eh * 0.22, by - eh * 0.6), (bx + side * eh * 0.35, by + 1)]
            cv.add(cv.poly(inner), CHEEK if stage < 3 else DARK, outline=False)
        elif kind == "round":
            r = eh * 0.45
            cv.add(cv.ell(bx + side * 1, by - r * 0.5, r, r), BASE)
            cv.add(cv.ell(bx + side * 1, by - r * 0.4, r * 0.5, r * 0.5), CHEEK, outline=False)
        elif kind == "crystal":
            crystal(cv, bx, by + 1, eh * 1.2, max(1.6, eh * 0.28), -math.pi / 2 + side * 0.45)
            if stage >= 2:
                crystal(cv, bx - side * 2.5, by - 0.5, eh * 0.8, max(1.3, eh * 0.2), -math.pi / 2 + side * 0.15)
        elif kind == "flame":
            cv.add(cv.poly(flame_pts(bx + side * 1, by + 1, eh * 0.9, eh * 1.3, lean=side * 0.6, tongues=2)), GLOW, flat=True)
            cv.add(cv.poly([(bx - side * eh * 0.3, by + 2), (bx + side * eh * 0.2, by - eh * 0.7), (bx + side * eh * 0.5, by + 1.5)]), BASE)
        elif kind == "horns" or kind == "crown":
            if kind == "crown" and side == 1:
                n = 3 if stage < 3 else 5
                cw = hr * 0.9
                pts = [(hx - cw, hy - hr * 0.78)]
                for i in range(n):
                    t = (i + 0.5) / n
                    pts += [(hx - cw + 2 * cw * t, hy - hr * 0.78 - eh * (0.9 if i == n // 2 else 0.6)),
                            (hx - cw + 2 * cw * (i + 1) / n, hy - hr * 0.78)]
                m = cv.poly(pts + [(hx + cw * 0.8, hy - hr * 0.6), (hx - cw * 0.8, hy - hr * 0.6)])
                cv.add(m, GLOW)
                cv.overlay.append((int(hx), int(hy - hr * 0.78 - eh * 0.5), "glow_hi"))
            elif kind == "horns":
                pts = [(bx + side * t * eh * 0.7 + side * math.sin(t * 2.2) * eh * 0.15, by - t * eh * 1.1) for t in np.linspace(0, 1, 6)]
                cv.add(cv.line(pts, max(1.5, 2.6 * k * (1.2 - 0.6 * 0))), ACCENT)
        elif kind == "leaf":
            if side == 1:
                leaf(cv, hx, hy - hr * 0.85, eh * 1.4, -math.pi / 2 - 0.7, eh * 0.4)
                leaf(cv, hx, hy - hr * 0.85, eh * 1.2, -math.pi / 2 + 0.75, eh * 0.35)
                cv.add(cv.line([(hx, hy - hr * 0.7), (hx, hy - hr * 0.95)], 1), ALT)
        elif kind == "antlers":
            pts = [(bx, by + 1), (bx + side * eh * 0.3, by - eh * 0.5), (bx + side * eh * 0.4, by - eh * 1.2)]
            cv.add(cv.line(pts, max(1.2, 1.8 * k)), ALT)
            cv.add(cv.line([(bx + side * eh * 0.3, by - eh * 0.5), (bx + side * eh * 0.9, by - eh * 0.9)], max(1, 1.4 * k)), ALT)
            if stage >= 2:
                leaf(cv, bx + side * eh * 0.4, by - eh * 1.2, eh * 0.7, -math.pi / 2 + side * 0.9, eh * 0.25)
            if stage == 3:
                cv.add(cv.line([(bx + side * eh * 0.36, by - eh * 0.9), (bx - side * eh * 0.1, by - eh * 1.4)], 1.2), ALT)
        elif kind == "antenna" or kind == "feelers":
            tip = (bx + side * eh * 0.6, by - eh * 1.3)
            mid = (bx + side * eh * 0.1, by - eh * 0.8)
            cv.add(cv.line([(bx, by + 1), mid, tip], 1), DARK if kind == "antenna" else ACCENT)
            if kind == "antenna":
                cv.add(cv.ell(tip[0], tip[1], 1.6 * max(k, .8), 1.6 * max(k, .8)), GLOW, flat=True)
            else:
                for t in (0.45, 0.65, 0.85):
                    px, py = mid[0] + (tip[0] - mid[0]) * t, mid[1] + (tip[1] - mid[1]) * t
                    cv.add(cv.line([(px, py), (px + side * 1.5 * k + side, py + 1.5)], 1), ACCENT)
                cv.add(cv.ell(tip[0], tip[1], 1.2, 1.2), GLOW, flat=True)
        elif kind == "bolts":
            cv.add(cv.ell(bx, by + 1, eh * 0.35, eh * 0.35), ALT)
            cv.add(cv.line([(bx, by), (bx + side * eh * 0.3, by - eh * 0.9)], 1), DARK)
            cv.add(cv.ell(bx + side * eh * 0.3, by - eh * 0.9, 1.3, 1.3), GLOW, flat=True)
        elif kind == "gills":
            for j, a in enumerate((-0.55, -0.05, 0.45)):
                ang = math.pi + a if side < 0 else -a
                x0, y0 = hx + side * hr * 1.05, hy - hr * 0.1 + j * 0.0
                ln = eh * (1.0 - 0.15 * abs(j - 1))
                ex, ey = x0 + math.cos(ang) * ln, y0 + math.sin(ang) * ln * 0.9 - 1
                m = cv.line([(x0, y0), (ex, ey)], max(1.6, 2.2 * k))
                cv.add(m, ACCENT)
                for t in (0.35, 0.7):
                    fx, fy = x0 + (ex - x0) * t, y0 + (ey - y0) * t
                    cv.add(cv.line([(fx, fy), (fx + side * 1.0, fy - 1.6)], 1), ACCENT, outline=False)


def _tail(cv, gen, x, y, k, stage, side=1):
    kind, size = gen["tail"], gen["genes"]["tail_size"]
    L = (8 + 7 * size) * k * (0.7 if stage == 1 else 1.0 + 0.2 * (stage == 3))
    if kind in ("none", "fishtail", "tip"):
        return
    if kind == "spade":
        pts = [(x + side * L * 0.55 * t, y - L * 0.75 * math.sin(t * 2.0) + L * 0.15 * t, (1.9 - 0.9 * t) * k + 0.6) for t in np.linspace(0, 1, 9)]
        m, l = cv.chain(pts)
        cv.add(m, BASE, light=l)
        ex, ey = pts[-1][:2]
        s2 = (2.6 + 2.2 * (stage - 1)) * k + 1
        cv.add(cv.poly([(ex - side * s2 * 0.2, ey + s2 * 0.4), (ex + side * s2 * 0.9, ey - s2 * 0.9), (ex + side * s2 * 1.3, ey + s2 * 0.5), (ex + side * s2 * 0.4, ey + s2 * 0.9)]), ACCENT)
        return
    if kind in ("fluffy", "plume"):
        pts = []
        for i in range(7):
            t = i / 6
            ang = -0.2 - 1.9 * t
            pts.append((x + side * (math.cos(ang) * L * 0.55 + L * 0.25 * t), y + math.sin(ang) * L * 0.9,
                        (1.6 + 3.2 * math.sin(math.pi * (0.2 + 0.7 * t))) * k * (1.25 if kind == "plume" else 1.05)))
        m, l = cv.chain(pts)
        cv.add(m, BASE, light=l)
        tx, ty, tr = pts[-1]
        tip, l2 = cv.chain([(tx, ty, tr * 0.9), pts[-2][:2] + (pts[-2][2] * 0.5,)])
        cv.add(tip & m, BELLY if kind == "fluffy" else GLOW, light=l2)
    elif kind == "leaf":
        cv.add(cv.line([(x, y), (x + side * L * 0.4, y - L * 0.3)], max(1.2, 1.6 * k)), ALT)
        leaf(cv, x + side * L * 0.3, y - L * 0.2, L * 0.9, -math.pi / 2 + side * 0.55, L * 0.28)
    elif kind == "flame":
        pts = [(x + side * L * 0.15 * t * 3, y - L * 0.25 * t * 3, (2.4 - t) * k * 1.4) for t in (0, .33, .66)]
        m, l = cv.chain(pts)
        cv.add(m, BASE, light=l)
        fx, fy = x + side * L * 0.5, y - L * 0.55
        cv.add(cv.poly(flame_pts(fx, fy + L * 0.3, L * 0.7, L * 1.0, lean=side * 0.8, tongues=3)), GLOW, flat=True)
        cv.add(cv.poly(flame_pts(fx, fy + L * 0.3, L * 0.35, L * 0.55, lean=side * 0.8, tongues=2)), WHITE, flat=True, outline=False)
    elif kind in ("crystal", "fin"):
        pts = [(x + side * L * 0.35 * t, y - L * 0.15 * t + L * 0.1 * math.sin(t * 3), (2.6 - 1.2 * t) * k * 1.3) for t in np.linspace(0, 1, 5)]
        m, l = cv.chain(pts)
        cv.add(m, BASE, light=l)
        ex, ey = pts[-1][:2]
        if kind == "fin":
            cv.add(cv.poly([(ex - side * 2, ey - 1), (ex + side * L * 0.55, ey - L * 0.55), (ex + side * L * 0.45, ey + L * 0.25), (ex - side * 1, ey + 2)]), ACCENT)
        else:
            crystal(cv, ex, ey, L * 0.7, max(1.5, L * 0.18), -math.pi / 2 + side * 0.6)
            crystal(cv, ex - side * 1.5, ey, L * 0.45, max(1.2, L * 0.12), -math.pi / 2 + side * 1.2)
    elif kind in ("cable", "gear"):
        pts = [(x + side * L * 0.5 * t, y - L * 0.6 * math.sin(t * 2.0), 1.2 * k + 0.6) for t in np.linspace(0, 1, 8)]
        m, l = cv.chain(pts)
        cv.add(m, ALT, light=l)
        ex, ey = pts[-1][:2]
        if kind == "gear":
            gr = 2.5 * k + 1.5
            teeth = [(ex + math.cos(a) * gr * (1.35 if i % 2 == 0 else 1.0), ey + math.sin(a) * gr * (1.35 if i % 2 == 0 else 1.0))
                     for i, a in enumerate(np.linspace(0, 2 * math.pi, 17)[:-1])]
            cv.add(cv.poly(teeth), ALT)
            cv.add(cv.ell(ex, ey, gr * 0.4, gr * 0.4), GLOW, flat=True, outline=False)
        else:
            cv.add(cv.ell(ex, ey, 1.6 * k + 0.8, 1.6 * k + 0.8), GLOW, flat=True)


# ---------------------------------------------------------------- wings
def feather_wing(cv, x, y, sw, side, tilt, stage, k):
    """Layered bird wing: long primaries from the wrist, secondaries along the arm, covert scallops on top.
    Every feather is its own part, so inner outlines separate them and the wing reads as feathers."""
    a0 = -math.pi / 2 + side * (0.95 - tilt)
    la = sw * 0.52
    wx, wy = x + math.cos(a0) * la, y + math.sin(a0) * la
    n_p = 3 + (stage >= 2) + (stage == 3)
    fw = max(1.6, 1.25 * k + 0.9)
    for j in range(n_p):  # primaries (back-most), fanning from up-out to out-down
        ang = a0 - side * 0.15 + side * 1.25 * j / max(1, n_p - 1)
        leaf(cv, wx, wy, sw * (0.78 - 0.08 * j), ang, fw, ALT)
    for j, t in enumerate((0.35, 0.62, 0.88)[: 2 + (stage >= 2)]):  # secondaries
        sx, sy = x + (wx - x) * t, y + (wy - y) * t
        leaf(cv, sx, sy, sw * (0.42 + 0.1 * t), a0 + side * 1.75, fw * 0.95, BASE)
    cov = [(x + (wx - x) * t, y + (wy - y) * t + 0.6, (1.3 + 1.1 * (1 - t)) * k + 0.7) for t in np.linspace(0.05, 1.0, 5)]
    m, l = cv.chain(cov)
    cv.add(m, BELLY, light=l)


def bat_wing(cv, x, y, sw, side, tilt, stage, k):
    """Bat/dragon wing: arm to the wrist, 2-3 finger bones, scalloped membrane between the tips."""
    a0 = -math.pi / 2 + side * (0.75 - tilt)
    wx, wy = x + math.cos(a0) * sw * 0.5, y + math.sin(a0) * sw * 0.5
    nf = 2 if stage == 1 else 3
    tips = []
    for j in range(nf):
        ang = a0 - side * 0.25 + side * (1.45 if nf == 3 else 1.1) * j / max(1, nf - 1)
        ln = sw * (0.62 + 0.18 * (j == 1) - 0.06 * j)
        tips.append((wx + math.cos(ang) * ln, wy + math.sin(ang) * ln))
    base = (x + side * sw * 0.08, y + sw * 0.32)
    poly = [(x, y), (wx, wy), tips[0]]
    for a, b in zip(tips, tips[1:] + [base]):
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        poly += [(mx + (wx - mx) * 0.28, my + (wy - my) * 0.28), b]
    mem = cv.poly(poly)
    cv.add(mem, ACCENT, centre=(wx, wy), r=sw * 0.9, bias=0.25)
    for tx, ty in tips:  # finger bones (no extra outline; they read as ridges in the membrane)
        cv.add(cv.line([(wx, wy), (tx, ty)], 1) & mem, ALT, outline=False, bias=-0.2)
    cv.add(cv.line([(x, y), (wx, wy)], max(1.6, 1.8 * k + 0.6)), ALT)
    cv.overlay.append((int(round(wx)), int(round(wy - 1)), "white"))  # thumb claw


def one_wing(cv, gen, kind, x, y, sw, side, tilt, stage, k):
    if kind == "feather":
        feather_wing(cv, x, y, sw, side, tilt, stage, k)
    elif kind == "bat":
        bat_wing(cv, x, y, sw, side, tilt, stage, k)
    elif kind == "moth":
        sw *= 1.25
        ux, uy = x + side * sw * 0.66, y - sw * 0.42
        up = cv.ell(ux, uy, sw * 0.62, sw * 0.52)
        cv.add(up, ACCENT, centre=(ux - side * sw * 0.2, uy - sw * 0.2), r=sw * 0.8)
        lx, ly = x + side * sw * 0.45, y + sw * 0.25
        lo = cv.ell(lx, ly, sw * 0.42, sw * 0.38)
        cv.add(lo, ACCENT, centre=(lx, ly - sw * 0.2), r=sw * 0.6)
        band = (up & ~cv.ell(ux - side * 1, uy + 1, sw * 0.62 - 2, sw * 0.52 - 2))
        cv.mat[band] = ALT
        er = max(1.2, sw * 0.14)
        cv.mat[cv.ell(ux + side * sw * 0.12, uy, er + 1, er + 1) & up] = DARK
        spot = cv.ell(ux + side * sw * 0.12, uy, er, er) & up
        cv.mat[spot] = GLOW
        cv.flat[spot] = True
    elif kind == "leaf":
        leaf(cv, x, y, sw * 1.1, -math.pi / 2 + side * (1.15 - tilt), sw * 0.38)
        leaf(cv, x, y + 2, sw * 0.8, -math.pi / 2 + side * (1.65 - tilt), sw * 0.3)
    elif kind == "crystal":
        crystal(cv, x + side * 1, y, sw * 1.1, max(2, sw * 0.22), -math.pi / 2 + side * (0.85 - tilt))
        crystal(cv, x + side * 1, y + 2, sw * 0.8, max(1.6, sw * 0.17), -math.pi / 2 + side * (1.3 - tilt))
    elif kind == "flame":
        cv.add(cv.poly(flame_pts(x + side * sw * 0.5, y + 2, sw * 0.9, sw * 1.2, lean=side * 1.0, tongues=3)), GLOW, flat=True)
    elif kind == "vanes":
        for j in range(3):
            ang = -math.pi / 2 + side * (0.7 - tilt + 0.35 * j)
            ex, ey = x + math.cos(ang) * sw, y + math.sin(ang) * sw
            cv.add(cv.line([(x, y), (ex, ey)], max(1.5, 2.2 * k)), ALT)
            cv.add(cv.ell(ex, ey, 1.2, 1.2), GLOW, flat=True, outline=False)


def _wings(cv, gen, x, y, k, stage, span_scale=1.0, off=0.0, pose="front"):
    kind = gen["wings"]
    if kind == "none" or (stage == 1 and kind not in ("moth", "bat") and gen["genes"]["wing_size"] < 0.6):
        return
    size = gen["genes"]["wing_size"]
    sw = (9 + 8 * size) * k * span_scale * (0.55 if stage == 1 else 1.0 if stage == 2 else 1.3)
    if kind == "bat":
        sw *= 1.5
    if pose == "front":
        plan = [(-1, 1.0, 0.0, 0.0, -off), (1, 1.0, 0.0, 0.0, off)]
    elif pose == "three_quarter":  # far wing smaller, more upright and darker; near wing full
        plan = [(1, 0.68, 0.35, -0.45, off * 0.4), (-1, 1.0, 0.1, 0.0, -off * 0.3)]
    else:  # side: near wing up-back, far wing peeking behind it
        plan = [(-1, 0.8, 0.55, -0.5, 2.5), (-1, 1.0, 0.3, 0.0, 0.0)]
    for side, sc, tilt, bias, dx in plan:
        cv.bias = bias
        one_wing(cv, gen, kind, x + dx, y, sw * sc, side, tilt, stage, k)
    cv.bias = 0.0


def _back(fn):
    def wrapped(cv, *a, **kw):
        prev, cv.cur = cv.cur, "back"
        try:
            return fn(cv, *a, **kw)
        finally:
            cv.cur = prev
    return wrapped


tail = _back(_tail)
wings = _back(_wings)
back_part = _back(lambda cv, fn: fn())


# ---------------------------------------------------------------- face
def face(cv, gen, hx, hy, hr, k, stage, px_list, pose="front", mouth_xy=None, eye_y=None):
    gg = gen["genes"]
    big = {1: 1.12, 2: 1.0, 3: 0.86}[stage]
    ew = max(2.0, hr * (0.19 + 0.07 * gg["eye_size"]) * big)
    eh = ew * 1.3
    gap = max(ew + 1.6, hr * (0.44 + 0.10 * gg["eye_gap"]))
    ey = eye_y if eye_y is not None else hy + hr * (0.10 if stage < 3 else 0.02)
    if pose == "front":
        eyes = [(hx - gap, ew, -1, True), (hx + gap, ew, 1, True)]
    elif pose == "three_quarter":
        far_w = max(1.6, ew * 0.74)
        fx = min(hx + gap * 0.95, hx + hr * 0.92 - far_w)
        eyes = [(hx - gap * 0.5, ew * 1.04, -1, True), (fx, far_w, 1, False)]
    else:
        eyes = [(hx + hr * 0.25, ew * 1.08, 1, True)]
    style = gen["eye_style"]
    fierce = stage == 3 and gen["temperament"] in ("Fierce", "Bold")
    for ex, w, side, near in eyes:
        h = w * 1.3 if near else eh * 0.95
        m = cv.ell(ex, ey, w, h)
        cv.mat[m] = EYE
        cv.flat[m] = True
        iris = m & cv.ell(ex + (0.25 * w if pose != "front" else 0), ey + h * 0.32, w * 0.78, h * 0.55)
        cv.mat[iris] = IRIS
        lid = None
        if style == "closed":
            lid = m.copy()
        elif style == "sleepy":
            lid = m & (cv.yy < ey - h * 0.1)
        elif fierce:
            inner = (cv.xx - ex) * (-side) / max(w, 1)
            lid = m & (cv.yy < ey - h * 0.75 + (inner + 1) * h * 0.32)
        if lid is not None:
            cv.mat[lid] = BASE
            cv.flat[lid] = False
            cv.light[lid] = 0.0
            edge = m & ~lid & np.roll(lid, 1, axis=0)
            cv.mat[edge] = EYE
        if style == "closed":
            for q in range(-int(w * 0.8), int(w * 0.8) + 1):
                yy = int(round(ey + h * 0.2 - (1 if abs(q) >= w * 0.6 else 0)))
                px_list.append((int(round(ex + q)), yy, "line"))
            continue
        hlx, hly = int(round(ex - w * 0.45)), int(round(ey - h * (0.45 if lid is None else 0.0)))
        px_list.append((hlx, hly, "white"))
        if w >= 3.0 and lid is None:
            px_list += [(hlx + 1, hly, "white"), (hlx, hly + 1, "white"), (hlx + 1, hly + 1, "white")]
        px_list.append((int(round(ex + w * 0.4)), int(round(ey + h * 0.45)), "white"))
        if style == "sparkle":
            px_list.append((int(round(ex + w * 0.15)), int(round(ey - h * 0.1)), "white"))
        if near and (stage < 3 or gen["temperament"] in ("Playful", "Gentle", "Serene")):
            cs = side if pose == "front" else -1
            px_list += [(int(round(ex + cs * w * 0.9 + q)), int(round(ey + h * 1.05)), "cheek") for q in (0, cs)]
    if mouth_xy is None:
        my = int(round(ey + eh * 1.05 + (1 if stage == 3 else 0)))
        mx = int(round(hx - 0.5 + (gap * 0.25 if pose == "three_quarter" else 0)))
    else:
        mx, my = int(round(mouth_xy[0])), int(round(mouth_xy[1]))
    m = gen["mouth"]
    if pose == "side":
        px_list += [(mx, my, "line"), (mx - 1, my, "line"), (mx - 2, my - 1, "line")]
        if m == "fang":
            px_list.append((mx - 1, my + 1, "white"))
        elif m == "open":
            px_list += [(mx - 1, my + 1, "mouth"), (mx, my + 1, "line")]
        return
    if m == "w":
        px_list += [(mx - 1, my, "line"), (mx, my + 1, "line"), (mx + 1, my + 1, "line"), (mx + 2, my, "line")]
    elif m == "fang":
        px_list += [(mx, my, "line"), (mx + 1, my, "line"), (mx - 1, my - 1, "line"), (mx + 2, my - 1, "line"), (mx + 1, my + 1, "white")]
    elif m == "open":
        px_list += [(mx, my, "line"), (mx + 1, my, "line"), (mx, my + 1, "mouth"), (mx + 1, my + 1, "mouth"), (mx - 1, my, "line"), (mx + 2, my, "line")]
    else:
        px_list += [(mx - 1, my, "line"), (mx, my + 1, "line"), (mx + 1, my + 1, "line"), (mx + 2, my, "line")] if stage < 3 else [(mx, my, "line"), (mx + 1, my, "line")]


def bezier(ctrl, n):
    pts = []
    for i in range(n):
        t = i / (n - 1)
        q = list(ctrl)
        while len(q) > 1:
            q = [((1 - t) * a[0] + t * b[0], (1 - t) * a[1] + t * b[1]) for a, b in zip(q, q[1:])]
        pts.append(q[0])
    return pts


# ---------------------------------------------------------------- body plans
def quadruped(cv, gen, stage, k, hr0, chub, legf, pose, px):
    """fox / dragonling in three_quarter or side pose (drawn facing right)."""
    gg, body = gen["genes"], gen["body"]
    drag = body == "dragonling"
    leg_h = (7.5 if not drag else 5.5) * k * legf
    brx = (13.0 if not drag else 12.0) * k * chub
    bry = (6.2 if not drag else 7.6) * k * chub
    bcx = CX - 6.0 * k
    bcy = G - leg_h - bry * 0.6
    hr = hr0 * (0.9 if not drag else 0.98)
    hx = bcx + brx * (0.8 if pose == "three_quarter" else 0.95)
    hy = bcy - bry * 0.85 - hr * 0.45
    hy = max(hy, hr + 6 * k + (2 if gen["ears"] in ("pointy", "horns", "flame", "crystal", "antlers") else 0))
    wings(cv, gen, bcx + brx * 0.05, bcy - bry * 0.7, k, stage, off=brx * 0.25, pose=pose)
    tail(cv, gen, bcx - brx * 0.85, bcy - bry * 0.15, k, stage, side=-1)
    lw = (2.5 if not drag else 3.0) * k * chub + 0.6
    paw_mat = ALT if gen["element"] in ("ember", "machine") or drag else BELLY
    cv.bias = -0.5  # far legs
    for lx in (bcx - brx * 0.5 + 2.5, bcx + brx * 0.55 + 2.5):
        cv.add(cv.ell(lx, G - leg_h * 0.5 - 1, lw, leg_h * 0.55 + 1.5), BASE)
        cv.add(cv.ell(lx + 0.8, G - 1.3, lw + 0.5, 1.3 + k), paw_mat)
    cv.bias = 0.0
    if drag and stage >= 2 and gen["wings"] == "none":  # back spikes
        for t in np.linspace(-0.55, 0.45, 3 + stage):
            sx = bcx + brx * t
            sy = bcy - bry * math.sqrt(max(0.0, 1 - t * t)) + 1
            s = (1.8 + 0.8 * stage) * k
            cv.add(cv.poly([(sx - s * 0.6, sy + 1), (sx - s * 0.1, sy - s * 1.2), (sx + s * 0.6, sy + 1)]), ALT)
    cv.add(cv.ell(bcx, bcy, brx, bry), BASE)
    neck = [(bcx + brx * 0.55, bcy - bry * 0.2, bry * 0.8), (hx - hr * 0.15, hy + hr * 0.45, hr * 0.5)]
    m, l = cv.chain(neck)
    cv.add(m, BASE, light=l, outline=False)
    bm = cv.ell(bcx + brx * 0.12, bcy + bry * 0.45, brx * 0.62, bry * 0.5) & cv.ell(bcx, bcy, brx, bry)
    cv.add(bm, BELLY, outline=False)
    if drag:  # belly plates
        for yy in range(int(bcy + bry * 0.2), int(bcy + bry), 2):
            cv.light[bm & (cv.yy == yy)] -= 0.7
    else:  # chest ruff
        ruff = [(hx - hr * 0.35 + i * 1.4 * k, hy + hr * 0.75 + (i % 2) * 1.2, (2.0 + 0.6 * (stage - 1)) * k + 0.4) for i in range(4)]
        m, l = cv.chain(ruff)
        cv.add(m, BELLY, light=l)
    for lx in (bcx - brx * 0.58, bcx + brx * 0.45):
        cv.add(cv.ell(lx, G - leg_h * 0.5 - 1, lw, leg_h * 0.55 + 1.5), BASE)
        cv.add(cv.ell(lx + 0.8, G - 1.3, lw + 0.6, 1.4 + k), paw_mat)
    eh_shift = hr * (0.18 if pose == "three_quarter" else 0.38)
    g2 = gen
    ears(cv, g2, hx - eh_shift, hy, hr * (0.85 if pose == "three_quarter" else 0.55), k, stage)
    cv.add(cv.ell(hx, hy, hr, hr * 0.88), BASE)
    sx = hx + hr * (0.72 if pose == "three_quarter" else 0.88)
    sy = hy + hr * 0.32
    srx, sry = hr * (0.46 if not drag else 0.52), hr * (0.32 if not drag else 0.36)
    cv.add(cv.ell(sx, sy, srx, sry), BASE)
    cv.add(cv.ell(sx, sy + sry * 0.45, srx * 0.85, sry * 0.55) & cv.ell(sx, sy, srx, sry), BELLY, outline=False)
    ears(cv, g2, hx - eh_shift, hy, hr * (0.85 if pose == "three_quarter" else 0.55), k, stage, "front")
    nx = int(round(sx + srx - 1))
    px += [(nx, int(round(sy - sry * 0.4)), "nose"), (nx - 1, int(round(sy - sry * 0.4)), "nose")]
    face(cv, gen, hx - hr * 0.08, hy - hr * 0.05, hr, k, stage, px, pose, mouth_xy=(sx + srx * 0.25, sy + sry * 0.35))
    return hx, hy, hr


def bird(cv, gen, stage, k, hr0, chub, legf, pose, px):
    gg = gen["genes"]
    leg_h = 4.5 * k * legf + 1
    brx = (9.5 + 1.5 * gg["chub"]) * k * (1.15 if stage == 1 else 1.0)
    bry = brx * (1.0 if stage == 1 else 1.12)
    bcx = CX - 1.5
    bcy = G - leg_h - bry
    q = pose == "three_quarter"
    if stage == 1:
        hr, hx, hy = brx * 0.92, bcx + (1.5 if q else 0), bcy - bry * 0.2
    else:
        hr = hr0 * 0.85
        hx, hy = bcx + (brx * 0.32 if q else 0), bcy - bry * 0.82
    # tail feather fan (back layer)
    def fan():
        tx, ty = (bcx - brx * 0.75, bcy + bry * 0.25) if q else (bcx, bcy + bry * 0.5)
        n = 3 + (stage >= 2) + (stage == 3)
        for j in range(n):
            a = (math.pi * (0.85 + 0.35 * (j / max(1, n - 1)))) if q else (math.pi / 2 + (j - (n - 1) / 2) * 0.32)
            L = (7 + 5 * gg["tail_size"]) * k * (1.0 + 0.25 * (stage == 3)) * (0.75 if not q else 1.0)
            leaf(cv, tx, ty, L, a, max(1.5, 1.3 * k + 0.6), ALT if j % 2 == 0 else ACCENT)
    back_part(cv, fan)
    if stage >= 2 and gen["wings"] != "none":
        wings(cv, gen, bcx - (1 if q else 0), bcy - bry * 0.45, k, stage, span_scale=1.3, off=brx * 0.5, pose=pose)
    for side in ((-1, 1) if not q else (-0.35, 0.55)):  # legs
        lx = bcx + side * brx * 0.38
        cv.add(cv.line([(lx, bcy + bry * 0.8), (lx, G - 1)], max(1.0, 1.1 * k + 0.2)), BEAK)
        cv.add(cv.line([(lx - 1.5, G - 0.5), (lx + 2.0, G - 0.5)], 1), BEAK)
    cv.add(cv.ell(bcx, bcy, brx, bry), BASE)
    cv.add(cv.ell(bcx + (brx * 0.25 if q else 0), bcy + bry * 0.35, brx * 0.58, bry * 0.55) & cv.ell(bcx, bcy, brx, bry), BELLY, outline=False)
    # folded near wing on the body side
    fx, fy = (bcx - brx * 0.15, bcy - bry * 0.15) if q else (bcx - brx * 0.78, bcy - bry * 0.05)
    for j in range(2 + (stage >= 2)):
        ang = math.pi * (0.62 + 0.07 * j) if q else math.pi * (0.55 + 0.05 * j)
        leaf(cv, fx, fy + j * 1.2, brx * (0.95 - 0.12 * j), ang, max(1.8, brx * 0.24), (BASE, ALT, ACCENT)[j % 3])
    if not q:
        for j in range(2 + (stage >= 2)):
            leaf(cv, bcx + brx * 0.78, bcy - bry * 0.05 + j * 1.2, brx * (0.95 - 0.12 * j), math.pi * (0.45 - 0.05 * j), max(1.8, brx * 0.24), (BASE, ALT, ACCENT)[j % 3])
    if stage >= 2:
        cv.add(cv.ell(hx, hy, hr, hr * 0.92), BASE)
    # crest from the ear gene
    kind = gen["ears"]
    if kind in ("pointy", "round", "leaf", "flame", "crystal", "feelers", "antlers"):
        n = 3 if stage < 3 else 4
        for j in range(n):
            a = -math.pi / 2 - 0.5 + (0.9 * j / (n - 1)) - (0.4 if q else 0)
            if kind == "flame":
                cv.add(cv.poly(flame_pts(hx - 2 + j * 1.5, hy - hr * 0.8, 3, 5 * k + 2, lean=-0.6, tongues=1)), GLOW, flat=True)
            else:
                leaf(cv, hx - (2 if q else 0), hy - hr * 0.8, (4 + 3 * gg["ear_size"]) * k + 1.5 * (stage == 3), a, max(1.2, 1.0 * k + 0.4), ACCENT)
    else:
        ears(cv, gen, hx, hy, hr, k, stage)
        ears(cv, gen, hx, hy, hr, k, stage, "front")
    # beak
    by = hy + hr * (0.18 if stage == 1 else 0.12)
    if q:
        bx = hx + hr * 0.78
        bl = (2.0 + 1.1 * stage) * k + 1
        cv.add(cv.poly([(bx - 1, by - bl * 0.38), (bx + bl, by + bl * 0.08), (bx - 1, by + bl * 0.42)]), BEAK)
        face(cv, gen, hx - hr * 0.1, hy - hr * 0.05, hr, k, stage, px, pose, mouth_xy=(bx + 2, by + 3), eye_y=hy - hr * 0.02)
    else:
        bl = (1.8 + 0.8 * stage) * k + 1
        cv.add(cv.poly([(hx - bl, by + 1), (hx + 0.5, by - bl * 0.3), (hx + bl + 1, by + 1), (hx + 0.5, by + bl * 1.1)]), BEAK)
        face(cv, gen, hx, hy - hr * 0.08, hr, k, stage, px, pose, mouth_xy=(hx, by + bl * 1.2 + 1), eye_y=hy - hr * 0.1)
    return hx, hy, hr


def fish(cv, gen, stage, k, hr0, chub, legf, pose, px):
    gg = gen["genes"]
    brx = (13 + 2 * gg["chub"]) * k * (1.08 if stage == 1 else 1.0)
    bry = (8.0 + 2.5 * gg["chub"]) * k * (1.1 if stage == 1 else 1.0)
    bcx = CX + 1
    bcy = G - 5 - 5 * k - bry
    finL = (6 + 6 * gg["tail_size"]) * k * (1 + 0.3 * (stage == 3))

    def backfins():
        tx = bcx - brx * 0.98
        cv.add(cv.poly([(tx + 2, bcy - 1), (tx - finL * 0.9, bcy - finL * 0.95), (tx - finL * 0.55, bcy), (tx - finL * 0.9, bcy + finL * 0.85), (tx + 2, bcy + 1)]),
               ACCENT, centre=(tx, bcy - finL * 0.3), r=finL)
        for s in (-1, 1):
            cv.add(cv.line([(tx + 1, bcy), (tx - finL * 0.75, bcy + s * finL * 0.7)], 1), ACCENT, outline=False, bias=0.6)
        dh = bry * (0.65 + 0.25 * stage) + 2
        d0, d1 = bcx - brx * 0.45, bcx + brx * 0.3
        cv.add(cv.poly([(d0, bcy - bry * 0.7), (d0 + (d1 - d0) * 0.2, bcy - bry * 0.8 - dh), (d1, bcy - bry * 0.75)]), ACCENT, centre=(d0, bcy - bry - dh * 0.5), r=dh)
        for t in (0.25, 0.5, 0.75):
            cv.add(cv.line([(d0 + (d1 - d0) * t, bcy - bry * 0.75), (d0 + (d1 - d0) * 0.2 * (1 - t) + (d1 - d0) * t * 0.6, bcy - bry * 0.8 - dh * (1 - 0.6 * t))], 1),
                   ACCENT, outline=False, bias=0.6)
        cv.add(cv.poly([(bcx - brx * 0.35, bcy + bry * 0.75), (bcx - brx * 0.6, bcy + bry * 0.75 + finL * 0.55), (bcx - brx * 0.05, bcy + bry * 0.85)]), ACCENT)
    back_part(cv, backfins)
    body = cv.ell(bcx, bcy, brx, bry) | cv.poly([(bcx - brx * 0.55, bcy - bry * 0.55), (bcx - brx * 1.0, bcy - bry * 0.2), (bcx - brx * 1.0, bcy + bry * 0.2), (bcx - brx * 0.55, bcy + bry * 0.55)])
    cv.add(body, BASE, centre=(bcx, bcy), r=max(brx, bry))
    bel = body & (cv.yy > bcy + bry * 0.22)
    cv.mat[bel] = BELLY
    gx = bcx + brx * 0.22
    arc = cv.line([(gx, bcy - bry * 0.55), (gx - 1.5, bcy), (gx, bcy + bry * 0.55)], 1) & body
    cv.light[arc] -= 1.1
    if stage >= 2 and gen["element"] == "crystal":
        for t in (-0.45, -0.1, 0.25)[: stage]:
            crystal(cv, bcx + brx * t, bcy - bry * 0.8, (3 + 2 * stage) * k, 1.6, -math.pi / 2 - 0.3)
    if stage >= 2 and gen["element"] in ("umbral", "machine"):
        ax, ay = bcx + brx * 0.55, bcy - bry * 0.7
        tip = (ax + 6 * k, ay - 7 * k)
        cv.add(cv.line([(ax, ay), (ax + 4 * k, ay - 7 * k), tip], 1), DARK)
        cv.add(cv.ell(tip[0], tip[1] + 1, 1.8 * k + 0.5, 1.8 * k + 0.5), GLOW, flat=True)
    hx, hy, hr = bcx + brx * 0.48, bcy - bry * 0.12, bry * 0.95
    leaf(cv, bcx + brx * 0.05, bcy + bry * 0.3, finL * 0.75, math.pi * 0.82, max(1.6, finL * 0.22), ACCENT)
    face(cv, gen, hx, hy, hr, k, stage, px, "side", mouth_xy=(bcx + brx * 0.93, bcy + bry * 0.18), eye_y=hy - hr * 0.05)
    cv.float_h = 5 + 5 * k
    return hx, hy, hr


def serpent(cv, gen, stage, k, hr0, chub, legf, pose, px):
    gg = gen["genes"]
    br = (5.0 + 2 * gg["chub"]) * k * 1.1
    j = gg["tail_size"] - 0.5
    span = {1: 14, 2: 21, 3: 26}[stage]
    ctrl = [(CX - span, G - br * 0.6 - 1), (CX - span * 0.45, G - br - 9 * k * (1 + j)), (CX - span * 0.05, G - br * 0.5),
            (CX + span * 0.45, G - br * 0.6), (CX + span * 0.5, G - 16 * k - 4)]
    n = {1: 14, 2: 22, 3: 30}[stage]
    pts = [(x, y, br * (0.35 + 0.65 * (i / (n - 1)) ** 0.6)) for i, (x, y) in enumerate(bezier(ctrl, n))]
    hr = hr0 * 0.9
    nx, ny, _ = pts[-1]
    hx, hy = nx + 1.5 * k, ny - hr * 0.55
    hy = max(hy, hr + 6)
    tail(cv, gen, pts[0][0], pts[0][1], k * 0.8, stage, side=-1)
    if gen["wings"] in ("crystal", "flame", "bat") and stage >= 2:  # dorsal crest
        for i in range(3, n - 3, 4):
            x, y, r = pts[i]
            if gen["wings"] == "crystal":
                crystal(cv, x, y - r * 0.6, r * 1.3 + 1, max(1.3, r * 0.3), -math.pi / 2 - 0.25)
            else:
                back_part(cv, lambda x=x, y=y, r=r: cv.add(cv.poly([(x - r, y - r * 0.4), (x - r * 0.2, y - r * 1.9), (x + r * 0.7, y - r * 0.5)]), ACCENT))
    m, l = cv.chain(pts)
    cv.add(m, BASE, light=l)
    cv.mat[m & (cv.chain_dy > 0.4)] = BELLY
    if stage >= 2:  # segment rings
        for i in range(2, n - 2, 3):
            x, y, r = pts[i]
            ring = m & (np.abs((cv.xx - x) + 0.3 * (cv.yy - y)) < 0.5) & (((cv.xx - x) ** 2 + (cv.yy - y) ** 2) < r * r)
            cv.light[ring] -= 0.6
    ears(cv, gen, hx - hr * 0.45, hy, hr * 0.6, k, stage)
    cv.add(cv.ell(hx, hy, hr * 1.0, hr * 0.85), BASE)
    sx, sy = hx + hr * 0.82, hy + hr * 0.25
    cv.add(cv.ell(sx, sy, hr * 0.5, hr * 0.34), BASE)
    cv.add(cv.ell(sx, sy + hr * 0.18, hr * 0.42, hr * 0.17) & cv.ell(sx, sy, hr * 0.5, hr * 0.34), BELLY, outline=False)
    ears(cv, gen, hx - hr * 0.45, hy, hr * 0.6, k, stage, "front")
    px.append((int(round(sx + hr * 0.38)), int(round(sy - hr * 0.15)), "nose"))
    face(cv, gen, hx - hr * 0.1, hy - hr * 0.05, hr, k, stage, px, "side", mouth_xy=(sx + hr * 0.35, sy + hr * 0.15))
    return hx, hy, hr


def biped(cv, gen, stage, k, hr0, chub, legf, pose, px):
    gg = gen["genes"]
    q = pose == "three_quarter"
    leg_h = (3.5 + 3 * (stage - 1)) * k * (0.8 + 0.4 * gg["legs"])
    bw = (8.0 + 2 * gg["chub"]) * k
    bh = (7.5 + 2.0 * (stage - 1)) * k
    bcx = CX
    bcy = G - leg_h - bh * 0.85
    hr = hr0 * 1.02
    hx = bcx + (hr * 0.1 if q else 0)
    hy = bcy - bh * 0.7 - hr * 0.62
    hy = max(hy, hr + 7 * k)
    if stage == 3:  # cape
        back_part(cv, lambda: cv.add(cv.poly([(bcx - bw * 0.8, bcy - bh * 0.6), (bcx + bw * 0.8, bcy - bh * 0.6), (bcx + bw * 1.45, G - 1), (bcx - bw * 1.45, G - 1)]), ACCENT))
    wings(cv, gen, bcx, bcy - bh * 0.4, k, stage, off=bw * 0.5, pose=pose)
    tail(cv, gen, bcx + bw * 0.6, bcy + bh * 0.3, k, stage, side=1)
    for side in (-1, 1):
        lx = bcx + side * bw * 0.45
        cv.add(cv.ell(lx, G - leg_h * 0.5 - 1, 2.6 * k + 0.7, leg_h * 0.5 + 1.5), BASE)
        cv.add(cv.ell(lx + side * 0.6 + (1 if q else 0), G - 1.3, 3.0 * k + 0.8, 1.4 + k), ALT)
    cv.add(cv.ell(bcx, bcy, bw, bh), BASE)
    cv.add(cv.ell(bcx + (1 if q else 0), bcy + bh * 0.15, bw * 0.55, bh * 0.65) & cv.ell(bcx, bcy, bw, bh), BELLY, outline=False)
    for side in (-1, 1):  # arms
        ax = bcx + side * (bw + 0.8 * k)
        ar = (2.2 + 0.8 * (stage - 1)) * k + 0.6
        cv.add(cv.ell(ax, bcy + bh * 0.05, ar, bh * 0.55), BASE, bias=-0.3 if (q and side > 0) else 0.0)
        cv.add(cv.ell(ax, bcy + bh * 0.5, ar + 0.4, ar + 0.2), BELLY if gen["element"] not in ("machine", "ember") else ALT)
    if stage >= 2:  # scarf / collar
        cv.add(cv.ell(bcx, bcy - bh * 0.8, bw * 0.75, 2.0 * k + 0.6), ALT)
    ears(cv, gen, hx, hy, hr, k, stage)
    cv.add(cv.ell(hx, hy, hr, hr * 0.9), BASE)
    ears(cv, gen, hx, hy, hr, k, stage, "front")
    face(cv, gen, hx, hy, hr, k, stage, px, pose)
    return hx, hy, hr


NEW_PLANS = {"fox": quadruped, "dragonling": quadruped, "bird": bird, "fish": fish, "serpent": serpent, "biped": biped}


def build(gen, stage, layer="all", sparkle=True):
    cv = Canvas()
    cv.skip_main = layer == "back"
    cv.float_h = 0
    k = STAGE_K[stage]
    gg = gen["genes"]
    body = gen["body"]
    pose = gen.get("pose", "front")
    px = []
    headboost = {1: 1.28, 2: 1.06, 3: 0.92}[stage]
    hr = (10.5 + 3 * gg["head"]) * k * headboost
    chub = 0.85 + 0.35 * gg["chub"]
    legf = {1: 0.45, 2: 1.0, 3: 1.25}[stage] * (0.7 + 0.6 * gg["legs"])
    did_face = body in NEW_PLANS
    if did_face:
        hx, hy, hr = NEW_PLANS[body](cv, gen, stage, k, hr, chub, legf, pose, px)
    elif body == "pup":
        leg_h = 6 * k * legf
        brx, bry = 13 * k * chub, 8.5 * k * chub
        bcy = G - leg_h - bry * 0.55
        hx, hy = CX, bcy - bry * 0.45 - hr * 0.55
        if hy - hr < 9 * k:
            hy = hr + 9 * k
        wings(cv, gen, CX, bcy - bry * 0.5, k, stage, off=brx * 0.55)
        tail(cv, gen, CX + brx * 0.75, bcy - bry * 0.1, k, stage, side=1)
        for side in (-1, 1):  # back legs
            lx = CX + side * brx * 0.78
            cv.add(cv.ell(lx, G - leg_h * 0.45 - 1, 3.0 * k * chub + 0.5, leg_h * 0.5 + 2), BASE)
            cv.add(cv.ell(lx + side * 0.5, G - 1.2, 3.0 * k + 0.6, 1.6 + k), ALT if gen["element"] in ("ember", "machine") else BASE)
        cv.add(cv.ell(CX, bcy, brx, bry), BASE)
        if stage == 3:  # mane / collar
            mane = [(CX + math.cos(a) * hr * 0.95, hy + hr * 0.55 + math.sin(a) * hr * 0.45, hr * 0.32) for a in np.linspace(0.1, math.pi - 0.1, 7)]
            m, l = cv.chain(mane)
            cv.add(m, GLOW if gen["element"] == "ember" else ALT, light=l, flat=gen["element"] == "ember")
        cv.add(cv.ell(CX, bcy + bry * 0.25, brx * 0.42, bry * 0.65), BELLY, outline=False)
        for side in (-1, 1):  # front legs
            lx = CX + side * hr * 0.42
            cv.add(cv.ell(lx, G - leg_h * 0.5 - 1, 2.6 * k * chub + 0.7, leg_h * 0.55 + 1.5), BASE)
            paw = cv.ell(lx, G - 1.4, 3.0 * k + 0.7, 1.4 + k)
            cv.add(paw, BELLY if gen["element"] not in ("ember", "machine") else ALT)
        ears(cv, gen, hx, hy, hr, k, stage)
        cv.add(cv.ell(hx, hy, hr, hr * 0.9), BASE)
        ears(cv, gen, hx, hy, hr, k, stage, "front")
        cv.add(cv.ell(hx, hy + hr * 0.5, hr * 0.42, hr * 0.3), BELLY, outline=False)
        px.append((int(round(hx - 0.5)), int(round(hy + hr * 0.35)), "nose"))
        px.append((int(round(hx + 0.5)), int(round(hy + hr * 0.35)), "nose"))
        targets = ("body", "head")
    elif body == "sprout":
        brx = (12.5 + 2 * gg["chub"]) * k * (1.15 if stage == 1 else 1.0) * (1.08 if stage == 3 else 1)
        bry = brx * 0.88
        bcy = G - 2 * k - bry
        hx, hy, hr = CX, bcy - bry * 0.18, brx
        wings(cv, gen, CX, bcy - bry * 0.1, k, stage, off=brx * 0.6)
        tail(cv, gen, CX + brx * 0.7, bcy + bry * 0.4, k, stage)
        for side in (-1, 1):
            cv.add(cv.ell(CX + side * brx * 0.5, G - 2.2 * k - 0.5, 3.4 * k + 0.6, 2.2 * k + 0.8), ALT if stage > 1 else BASE)
        if stage >= 2:
            for side in (-1, 1):
                ax = CX + side * brx * 0.95
                ar = (2.4 + 1.6 * (stage == 3)) * k + 0.6
                cv.add(cv.ell(ax, bcy + bry * 0.25, ar, ar * 1.3), BASE)
        ears(cv, gen, hx, hy - hr * 0.05, hr * 0.85, k, stage)
        cv.add(cv.ell(CX, bcy, brx, bry), BASE)
        cv.add(cv.ell(CX, bcy + bry * 0.5, brx * 0.55, bry * 0.42), BELLY, outline=False)
        ears(cv, gen, hx, hy - hr * 0.05, hr * 0.85, k, stage, "front")
        if stage == 3:
            for side in (-1, 1):
                ax = CX + side * brx * 0.95
                if gen["element"] in ("verdant", "grove"):
                    leaf(cv, ax, bcy - bry * 0.1, 6 * k, -math.pi / 2 + side * 0.6, 2)
                elif gen["element"] in ("crystal", "frost"):
                    crystal(cv, ax, bcy, 6, 1.6, -math.pi / 2 + side * 0.5)
                elif gen["element"] == "ember":
                    cv.add(cv.poly(flame_pts(ax, bcy, 5, 7, lean=side, tongues=2)), GLOW, flat=True)
        hy = bcy - bry * 0.2
        hr = brx * 0.95
        targets = ("body",)
    elif body == "moth":
        brx = (9 + 2 * gg["chub"]) * k * (1.2 if stage == 1 else 1.0)
        bry = brx * (1.05 if stage == 1 else 1.15)
        bcy = G - 3 * k - bry
        wings(cv, gen, CX, bcy - bry * 0.1, k, stage, span_scale=1.15)
        for side in (-1, 1):
            cv.add(cv.ell(CX + side * brx * 0.45, G - 2, 2 * k + 0.5, 2 * k + 0.6), ALT)
        cv.add(cv.ell(CX, bcy, brx, bry), BASE)
        # fluffy ruff
        ruff = [(CX + math.cos(a) * brx * 0.8, bcy + bry * 0.05 + math.sin(a) * bry * 0.3, brx * 0.32) for a in np.linspace(0.15, math.pi - 0.15, 7)]
        m, l = cv.chain(ruff)
        cv.add(m, BELLY, light=l)
        hr = brx * 0.95
        hx, hy = CX, bcy - bry * 0.4
        g2 = dict(gen, ears="feelers" if gen["ears"] not in ("horns", "round") else gen["ears"])
        ears(cv, g2, hx, hy, hr, k, stage)
        cv.add(cv.ell(hx, hy, hr, hr * 0.82), BASE)
        tail(cv, gen, CX + brx * 0.6, bcy + bry * 0.6, k * 0.8, stage)
        targets = ("body", "head")
    elif body == "axolotl":
        hr = (10 + 3 * gg["head"]) * k * headboost * 0.95
        n = {1: 4, 2: 7, 3: 11}[stage]
        br = (6.0 + 2 * gg["chub"]) * k * (1.0 if stage < 3 else 1.1)
        if stage < 3:
            ctrl = [(CX - 1, G - br - 3 * k), (CX + 8 * k, G - br * 0.9), (CX + 16 * k, G - br * 0.6), (CX + 22 * k, G - 9 * k)]
        else:
            j1, j2 = gg["tail_size"] - 0.5, gg["legs"] - 0.5
            ctrl = [(CX - 3, 38), (CX + 2 + 6 * j2, 58), (CX + 22 + 4 * j1, 60), (CX + 26 - 8 * j2, 34 + 10 * j1), (CX + 18 + 10 * j1, 14 + 8 * j2)]
        n = {1: 10, 2: 16, 3: 30}[stage]
        pts = []
        for i in range(n):
            t = i / (n - 1)
            q = list(ctrl)
            while len(q) > 1:
                q = [((1 - t) * a[0] + t * b[0], (1 - t) * a[1] + t * b[1]) for a, b in zip(q, q[1:])]
            pts.append((q[0][0], q[0][1], br * (1 - 0.72 * t) + 0.9))
        hx = CX - (3 if stage < 3 else 4) * k
        hy = (pts[0][1] - br * 0.6 - hr * 0.55) if stage < 3 else 20
        hy = max(hy, hr + 6)
        if stage == 3:  # body starts right under the head, no separate neck ball
            ctrl = [(hx + 1, hy + hr * 0.4)] + ctrl[1:]
            pts = []
            for i in range(n):
                t = i / (n - 1)
                q = list(ctrl)
                while len(q) > 1:
                    q = [((1 - t) * a[0] + t * b[0], (1 - t) * a[1] + t * b[1]) for a, b in zip(q, q[1:])]
                pts.append((q[0][0], q[0][1], br * (1 - 0.72 * t) + 0.9))
            legs_at = [pts[int(n * 0.3)], pts[int(n * 0.5)]]
            for x, y, r in legs_at:
                cv.add(cv.ell(x - 1, y + r * 0.8, 2.6, 2.4), BASE)
            for i in range(6, n - 2, 4):
                x, y, r = pts[i]
                crystal(cv, x, y - r * 0.6, r * 1.4, max(1.4, r * 0.35), -math.pi / 2 + 0.25 * math.sin(i))
        m, l = cv.chain(pts[::-1])
        cv.add(m, BASE, light=l)
        belly_m = m & (cv.chain_dy > 0.35)
        cv.mat[belly_m] = BELLY
        tail(cv, dict(gen), pts[-1][0], pts[-1][1], k * 0.8, stage)
        if stage < 3:
            neck = [(hx + 2, hy + hr * 0.6, br * 0.9), (pts[0][0], pts[0][1], br)]
            m2, l2 = cv.chain(neck)
            cv.add(m2, BASE, light=l2)
            for side in (-1, 1):
                lx = hx + side * hr * 0.5 + 2
                cv.add(cv.ell(lx, G - 2.2 * k, 2.4 * k + 0.6, 2.4 * k + 0.7), BASE)
        ears(cv, gen, hx, hy, hr, k, stage)
        cv.add(cv.ell(hx, hy, hr * 1.12, hr * 0.85), BASE)
        targets = ("body", "head")
    else:  # golem
        tw = (12 + 3 * gg["chub"]) * k
        th = (13 + 2 * gg["legs"]) * k
        leg_h = 5 * k * legf
        ty1 = G - leg_h
        ty0 = ty1 - th
        hr = (8.5 + 2.5 * gg["head"]) * k * headboost
        hx, hy = CX, ty0 - hr * 0.55
        wings(cv, gen, CX, ty0 + 3, k, stage, off=tw * 0.6)
        tail(cv, gen, CX + tw * 0.7, ty1 - th * 0.2, k, stage)
        for side in (-1, 1):
            cv.add(cv.poly([(CX + side * tw * 0.25, ty1 - 2), (CX + side * tw * 0.75, ty1 - 2), (CX + side * tw * 0.8, G), (CX + side * tw * 0.2, G)]), ALT)
        torso = cv.poly([(CX - tw * 0.85, ty0 + 2), (CX + tw * 0.85, ty0 + 2), (CX + tw, ty0 + th * 0.55), (CX + tw * 0.7, ty1), (CX - tw * 0.7, ty1), (CX - tw, ty0 + th * 0.55)])
        torso |= cv.ell(CX, ty0 + th * 0.45, tw * 0.98, th * 0.55)
        cv.add(torso, BASE)
        cv.add(cv.ell(CX, ty0 + th * 0.55, tw * 0.45, th * 0.32), BELLY if gen["element"] != "machine" else ALT, outline=True)
        if gen["element"] == "machine":
            core = cv.ell(CX, ty0 + th * 0.55, tw * 0.18 + 0.5, tw * 0.18 + 0.5)
            cv.add(core, GLOW, flat=True)
        for side in (-1, 1):
            ax = CX + side * (tw + 2.5 * k)
            ar = (3 + 1.5 * (stage == 3)) * k + 0.8
            cv.add(cv.ell(ax, ty0 + th * 0.45, ar, th * 0.42), BASE)
            cv.add(cv.ell(ax, ty0 + th * 0.85, ar + 0.6, ar + 0.3), ALT)
            cv.add(cv.ell(CX + side * tw * 0.8, ty0 + 2, ar + 0.8, ar * 0.8), ALT)  # pauldron
        ears(cv, gen, hx, hy, hr, k, stage)
        cv.add(cv.ell(hx, hy, hr * 1.05, hr * 0.92), BASE)
        ears(cv, gen, hx, hy, hr, k, stage, "front")
        targets = ("body",)

    if body == "moth":
        cv.float_h = 0
    if layer == "back":
        cv.mat[cv.layer != 1] = 0
        return cv, []
    pattern(cv, gen, stage)
    if not did_face:
        face(cv, gen, hx, hy, hr, k, stage, px, "front")
    if layer == "main":
        cv.mat[cv.layer != 2] = 0
        cv.overlay = [o for o in cv.overlay if 0 <= o[0] < W and 0 <= o[1] < W and cv.layer[o[1], o[0]] == 2]
    if sparkle and layer == "all" and (stage == 3 or gen["genes"]["glow_amount"] > 0.8):
        sparkles(cv, gen, stage, px)
    return cv, px


def pattern(cv, gen, stage):
    """Stage-stable markings: positions are drawn once from the seed in body-relative (0..1)
    coordinates, so the same spots / stars / cracks sit in the same places at every stage."""
    kind, v = gen["pattern"], gen["pattern_variant"]
    s = Stream(gen["seed"], "pattern")
    m = cv.mat == BASE
    if not m.any():
        return
    ys, xs = np.nonzero(m)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    k = STAGE_K[stage]
    dens = 0.5 + gen["genes"]["pattern_density"]

    def at(u, w):
        return x0 + u * (x1 - x0), y0 + w * (y1 - y0)

    def snap_to_mask(x, y):
        d = (xs - x) ** 2 + (ys - y) ** 2
        i = int(np.argmin(d))
        return xs[i], ys[i]

    if kind == "spots":
        for _ in range(int((3 + (v % 4)) * dens * 1.3) + 1):
            x, y = snap_to_mask(*at(s.u(), s.u()))
            r = (0.9 + s.u() * 1.9) * k + 0.25
            cv.mat[cv.ell(x, y, r, r) & m] = ALT
    elif kind == "stripes":
        period = 3 + (v % 3)
        tilt = ((v >> 2) % 3 - 1) * 0.4
        rel = (cv.yy - y0) / max(1, (y1 - y0))
        band = ((((cv.yy - y0) / max(k, 0.6) + (cv.xx - x0) * tilt).astype(int) // 2) % period == 0) & m & (cv.light > -0.2) & (rel < 0.62)
        cv.mat[band] = ALT
    elif kind == "moss":
        for _ in range(int((4 + (v % 5)) * dens) + 1):
            cx, cy = snap_to_mask(*at(s.u(), s.u() * 0.6))
            for _ in range(5):
                x, y = cx + int(round((s.u() * 5 - 2) * k)), cy + int(round((s.u() * 3 - 1) * k))
                if 0 <= x < W and 0 <= y < W and m[y, x] and cv.light[y, x] > -0.3:
                    cv.mat[y, x] = ALT
    elif kind == "facets":
        step = 4 + (v % 3)
        for off in range(-64, 64, step):
            ln = m & (np.abs(((cv.xx - x0) - (cv.yy - y0) * (0.6 + 0.1 * (v % 4))) - off * k) < 0.55)
            cv.light[ln] += 0.9
    elif kind == "plates":
        for yy in np.arange(y0 + 3, y1, (4 + (v % 3)) * max(k, 0.7)):
            cv.light[m & (cv.yy == int(yy))] -= 1.2
        rivets = m & ((cv.xx.astype(int) + v) % 7 == 0) & ((cv.yy.astype(int)) % 5 == 2)
        cv.mat[rivets] = WHITE
    elif kind in ("cracks", "circuits"):
        for _ in range(4 + (v % 3)):
            x, y = map(float, snap_to_mask(*at(s.u(), 0.15 + 0.7 * s.u())))
            steps = int((6 + 6 * s.u()) * (0.5 + 0.5 * k))
            dirn = 0
            for st in range(steps):
                xi, yi = int(x), int(y)
                if 0 <= xi < W and 0 <= yi < W and m[yi, xi]:
                    cv.mat[yi, xi] = GLOW
                    cv.flat[yi, xi] = True
                if kind == "circuits":
                    dirn = int(s.u() * 4) if st % 3 == 0 else dirn
                    x += (1, -1, 0, 0)[dirn]
                    y += (0, 0, 1, -1)[dirn]
                else:
                    x = round(x + s.u() * 2 - 1)
                    y += 1 if s.u() < 0.6 else 0
    elif kind == "stars":
        for _ in range(5 + (v % 6)):
            x, y = snap_to_mask(*at(s.u(), s.u()))
            cv.mat[y, x] = GLOW
            cv.flat[y, x] = True
        wing = cv.mat == ACCENT
        if wing.any():
            wy, wx = np.nonzero(wing)
            for _ in range(int(4 + 2 * stage)):
                i = int(s.u() * len(wx))
                cv.mat[wy[i], wx[i]] = WHITE
    # quantum glyph: 5 bits of the pattern variant as a tiny chest mark, at EVERY stage (identity anchor)
    bel = np.nonzero(cv.mat == BELLY)
    if len(bel[0]) > 10:
        cy, cx = int(np.median(bel[0])), int(np.median(bel[1]))
    else:
        cx, cy = int((x0 + x1) / 2), int(y0 + 0.6 * (y1 - y0))
    for b in range(5):
        if (v >> b) & 1:
            x, y = cx - 2 + b, cy - (1 if b in (1, 3) else 0)
            if 0 <= x < W and 0 <= y < W and cv.mat[y, x] in (BELLY, BASE):
                cv.overlay.append((x, y, "glow"))


def sparkles(cv, gen, stage, px):
    s = Stream(gen["seed"], f"sparkle{stage}")
    filled = cv.mat > 0
    ys, xs = np.nonzero(filled)
    x0, x1, y0, y1 = xs.min() - 3, xs.max() + 3, ys.min() - 3, ys.max() + 1
    placed = 0
    for _ in range(60):
        if placed >= (6 if stage == 3 else 2):
            break
        x, y = int(x0 + s.u() * (x1 - x0)), int(y0 + s.u() * (y1 - y0))
        if 2 <= x < W - 2 and 2 <= y < W - 4 and not filled[max(0, y - 2):y + 3, max(0, x - 2):x + 3].any():
            big = s.u() < 0.4
            px.append((x, y, "spark"))
            if big:
                px += [(x - 1, y, "spark_dim"), (x + 1, y, "spark_dim"), (x, y - 1, "spark_dim"), (x, y + 1, "spark_dim")]
            placed += 1


BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


def _shift(a, dx, dy, fill=0):
    out = np.full_like(a, fill)
    ys = slice(max(0, -dy), W - max(0, dy)), slice(max(0, dy), W - max(0, -dy))
    xs = slice(max(0, -dx), W - max(0, dx)), slice(max(0, dx), W - max(0, -dx))
    out[ys[1], xs[1]] = a[ys[0], xs[0]]
    return out


def render(gen, stage, layer="all", eyes=None, shadow=True) -> Image.Image:
    """layer: 'all' | 'back' (wings+tail only) | 'main' (everything else). eyes: override eye style.
    Contact shadow is only drawn for layer='all' (the live page draws its own moving shadow)."""
    if eyes:
        gen = dict(gen, eye_style=eyes)
    cv, px = build(gen, stage, layer=layer)
    pal = palette(gen)
    mat, part, light, flat = cv.mat, cv.part, cv.light, cv.flat
    yy, xx = cv.yy.astype(int), cv.xx.astype(int)
    th = BAYER4[yy % 4, xx % 4]
    tone = np.full((W, W), MID, np.int8)
    tone[light > 0.36 + 0.24 * th] = LIGHT
    tone[light > 0.80 + 0.30 * th] = HI
    tone[light < -0.46 - 0.24 * th] = SHADOW
    tone[light < -1.02 - 0.30 * th] = DEEP
    tone[flat] = np.where(light[flat] > 0.1, LIGHT, MID)
    special = np.isin(mat, (EYE, IRIS, WHITE))
    # selective inner outline: back part pixel touching a front part
    inner = np.zeros((W, W), bool)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nm, npart = _shift(mat, dx, dy), _shift(part, dx, dy)
        inner |= (nm > 0) & (npart > part) & ~np.isin(nm, (EYE, IRIS, WHITE))
    inner &= (mat > 0) & ~np.isin(mat, (EYE, IRIS))
    tone[inner] = LINE
    lut = np.zeros((16, 6, 3), np.uint8)
    for key, rp in pal.items():
        if isinstance(key, int):
            lut[key] = rp
    img = np.zeros((W, W, 4), np.uint8)
    filled = mat > 0
    img[..., :3] = lut[mat, tone]
    img[mat == EYE, :3] = NAVY
    img[mat == IRIS, :3] = pal["iris"]
    img[mat == WHITE, :3] = (248, 248, 248)
    img[filled, 3] = 255
    # rim light: shadow-side silhouette pixels (exterior to the right / below) pick up a cool/gold rim
    ext_r = _shift(filled.astype(np.int8), -1, 0) == 0
    ext_d = _shift(filled.astype(np.int8), 0, -1) == 0
    rim = filled & (ext_r | ext_d) & (light < 0.15) & ~special & ~flat & ~inner
    rc = np.array(pal["rim"], np.float32)
    img[rim, :3] = np.array([snap(tuple(int(0.55 * a + 0.45 * b) for a, b in zip(c, rc))) for c in img[rim, :3]], np.uint8).reshape(-1, 3) if rim.any() else img[rim, :3]
    # exterior outline
    out = np.zeros_like(filled)
    out[1:, :] |= filled[:-1, :]
    out[:-1, :] |= filled[1:, :]
    out[:, 1:] |= filled[:, :-1]
    out[:, :-1] |= filled[:, 1:]
    out &= ~filled
    img[out] = (*pal["outline"], 255)
    cols = {"white": (248, 248, 248), "cheek": pal[CHEEK][MID], "line": pal[DARK][LINE], "mouth": pal[CHEEK][SHADOW],
            "nose": pal[NOSE][MID], "glow": pal[GLOW][LIGHT], "glow_hi": (248, 248, 248),
            "spark": pal[GLOW][LIGHT], "spark_dim": pal[GLOW][MID]}
    for x, y, kind in cv.overlay + px:
        if 0 <= x < W and 0 <= y < W:
            if kind.startswith("spark") and img[y, x, 3] > 0:
                continue
            if kind == "cheek" and mat[y, x] in (EYE, IRIS, 0):
                continue
            img[y, x] = (*cols[kind], 255)
    if shadow and layer == "all":  # soft contact shadow on the ground line
        occ = img[..., 3] > 0
        rows = np.nonzero(occ[: G + 1].any(axis=1))[0]
        if len(rows):
            low = occ[max(0, rows.max() - 3): rows.max() + 1].any(axis=0)
            cols_ = np.nonzero(low)[0]
            cx = (cols_.min() + cols_.max()) / 2
            half = max(5.0, (cols_.max() - cols_.min()) / 2 + 2) * (0.7 if cv.float_h else 1.0)
            for gy, frac in ((G + 1, 1.0), (G + 2, 0.82)):
                if gy >= W:
                    continue
                for gx in range(int(cx - half * frac), int(cx + half * frac) + 1):
                    if 0 <= gx < W and img[gy, gx, 3] == 0:
                        img[gy, gx] = (10, 14, 36, 150 if gy == G + 1 else 90)
    im = Image.fromarray(img, "RGBA")
    if gen.get("facing") == "left":
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return im


def upscale(im: Image.Image, f: int = 4) -> Image.Image:
    return im.resize((im.width * f, im.height * f), Image.NEAREST)
