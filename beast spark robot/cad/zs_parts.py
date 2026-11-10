"""ZEREF SPARK — parametric part builders (CadQuery).
DESIGN TARGET — not printed or test-fitted. All dimensions are ESTIMATES unless a
datasheet value is cited in BOM.csv. Units mm. Z up, front = -Y, robot centreline x=0.
Every part is modelled in its ASSEMBLED position; build.py exports STEP in assembly
coordinates and STL re-seated on the print bed."""
import math
from zs_lib import *

# ---------------------------------------------------------------- parameters
P = dict(
    wall=2.4,            # shell wall
    clr=0.4,             # sliding clearance on pegs / holes
    # torso: ellipsoid semi-axes + centre
    t_a=44.0, t_b=38.0, t_c=50.0, t_z=95.0,
    # head: rounded box half extents, edge radius, centre z
    h_x=75.0, h_y=64.0, h_z=59.0, h_r=48.0, h_cz=205.0,
    # visor window (outer)
    v_x=62.0, v_z0=172.0, v_z1=238.0, v_r=20.0,
    # floating gap and pedestal
    foot_z=12.0, ped_R=95.0, ped_h=45.0,
    st_y=-46.0,          # crystal station centre (x=0, y=st_y) on the pedestal top
    tube_od=12.0, tube_id=8.0,
    leg_x=22.0, arm_z=112.0, pod_z=220.0,
)
W = P["wall"]; C = P["clr"]


# ---------------------------------------------------------------- envelopes
def torso_outer(off=0.0):
    return ellipsoid(P["t_a"] + off, P["t_b"] + off, P["t_c"] + off, (0, 0, P["t_z"]))


def head_outer(off=0.0):
    return rounded_box(P["h_x"] + off, P["h_y"] + off, P["h_z"] + off, P["h_r"] + off,
                       (0, 0, P["h_cz"]))


def visor_window(grow=0.0):
    return rrect_prism_y(-P["v_x"] - grow, P["v_x"] + grow, P["v_z0"] - grow,
                         P["v_z1"] + grow, P["v_r"] + grow, -200, -20)


def pod_outer(sx, off=0.0):
    d = 46 + 2 * off
    return cyl(d, (sx * 55, 0, P["pod_z"]), (sx * (88 + off), 0, P["pod_z"]))


# ---------------------------------------------------------------- split-plane boss
def split_boss(pt, web_dir, outer, side):
    """M3 boss on the y=0 split plane, with a web to the shell wall.
    front half: y -8..-1.5 (heat-set insert), back half: y 1.5..8 (clearance)."""
    x, z = pt
    y0, y1 = (-8, -1.5) if side == "front" else (1.5, 8)
    b = cyl(8, (x, y0, z), (x, y1, z))
    wx = web_dir[0] * 40; wz = web_dir[1] * 40
    web = box(min(x, x + wx), max(x, x + wx), y0, y1, z - 2, z + 2) if wx else \
        box(x - 2, x + 2, y0, y1, min(z, z + wz), max(z, z + wz))
    s = b.fuse(web).intersect(outer)
    hole_d = 4.0 if side == "front" else 3.4   # 4.0 = M3 heat-set insert pilot (ESTIMATE)
    return s.cut(cyl(hole_d, (x, -9, z), (x, 9, z)))


TORSO_BOSSES = [((30, 92), (1, 0)), ((-30, 92), (-1, 0)), ((26, 70), (1, 0)), ((-26, 70), (-1, 0))]
HEAD_BOSSES = [((55, 180), (1, 0)), ((-55, 180), (-1, 0)), ((40, 250), (1, 0)), ((-40, 250), (-1, 0))]


# ---------------------------------------------------------------- appendage pegs
def leg_peg_zone(sx, grow=0.0):
    x = sx * P["leg_x"]
    return union(cyl(8 + 2 * grow, (x, 0, 44), (x, 0, 60)),
                 cyl(10 + 2 * grow, (x, 0, 60 - grow), (x, 0, 62 + grow)))


def arm_peg_zone(sx, grow=0.0):
    z = P["arm_z"]
    return union(cyl(7 + 2 * grow, (sx * 35.5, 0, z), (sx * 43, 0, z)),
                 cyl(10 + 2 * grow, (sx * (33.5 - grow), 0, z), (sx * 35.5, 0, z)))


def neck_zone(grow=0.0):
    return union(cyl(26 + 2 * grow, (0, 0, 135), (0, 0, 150)),
                 cyl(34 + 2 * grow, (0, 0, 132 - grow), (0, 0, 135)),
                 cyl(34 + 2 * grow, (0, 0, 150), (0, 0, 153 + grow)))


def pod_peg_zone(sx, grow=0.0):
    z = P["pod_z"]
    return union(cyl(12 + 2 * grow, (sx * 68, 0, z), (sx * 76, 0, z)),
                 cyl(16 + 2 * grow, (sx * (66 - grow), 0, z), (sx * 68, 0, z)))


def tube_socket():
    return cyl(20, (0, 0, 38), (0, 0, 52))


# ================================================================ TORSO
def torso_shell(side):
    o = torso_outer()
    s = o.cut(torso_outer(-W))
    s = s.fuse(tube_socket().intersect(torso_outer(5)))     # bottom socket boss
    # holes
    for sx in (-1, 1):
        s = s.cut(cyl(8 + 2 * C, (sx * P["leg_x"], 0, 40), (sx * P["leg_x"], 0, 62)))
        s = s.cut(cyl(7 + 2 * C, (sx * 30, 0, P["arm_z"]), (sx * 46, 0, P["arm_z"])))
    s = s.cut(cyl(26 + 2 * C, (0, 0, 130), (0, 0, 150)))                  # neck
    s = s.cut(cyl(41.0, (0, -50, 105), (0, -20, 105)))                     # chest core
    s = s.cut(cyl(P["tube_od"] + 0.3, (0, 0, 37), (0, 0, 50)))           # tube bore
    s = s.cut(cyl(8.5, (0, 0, 49), (0, 0, 60)))                           # wire pass
    if side == "front":
        for z in (64, 69, 74):                                           # BME280 vents
            s = s.cut(rrect_prism_y(-8, 8, z - 1.2, z + 1.2, 1.1, -50, -20))
    else:
        for i, z in enumerate((80, 88, 96, 104, 112, 120)):                # rear ESP32 vents
            s = s.cut(rrect_prism_y(-6, 6, z - 1.2, z + 1.2, 1.1, 20, 50))
    s = half(s, side)
    for pt, d in TORSO_BOSSES:
        s = s.fuse(split_boss(pt, d, torso_outer(-0.5), side))
    return s.clean()


def torso_bulkhead():
    sec = torso_outer(-W - 0.3).intersect(box(-60, 60, -1.5, 1.5, 0, 200))
    cut = union(
        box(-13, 13, -2, 2, 128, 150),                         # neck flange clearance
        box(-19, 19, -2, 2, 130, 150),
        box(-12, 12, -2, 2, 36, 57),                           # tube socket + wires
        *[box(sx * 13 if sx > 0 else -30, 30 if sx > 0 else -13, -2, 2, 50, 64) for sx in (-1, 1)],
        *[box(32 if sx > 0 else -60, 60 if sx > 0 else -32, -2, 2, 104, 120) for sx in (-1, 1)],
    )
    s = sec.cut(cut)
    for (x, z), _ in TORSO_BOSSES:
        s = s.cut(cyl(3.4, (x, -3, z), (x, 3, z)))
        # local clearance around the boss webs
    s = s.cut(rrect_prism_y(-8, 8, 112, 124, 3, -3, 3))           # harness pass-through
    # ESP32 cradle rails on the back face
    for sx in (-1, 1):
        s = s.fuse(box(13.4 if sx > 0 else -15.4, 15.4 if sx > 0 else -13.4, 1.5, 10, 64, 126))
    # sensor-sled screw bosses on the front face (M2 self-tap)
    for sx in (-1, 1):                                            # zip-tie slots for the DevKit
        for z in (82, 116):
            s = s.cut(box(sx * 16 - 1.5, sx * 16 + 1.5, -3, 3, z - 3, z + 3))
    for x, z in ((16, 66), (-16, 110)):
        s = s.cut(cyl(1.8, (x, -3, z), (x, 3, z)))
    return s.clean()


def sensor_sled():
    s = box(-18, 18, -4.5, -1.5, 62, 114)
    s = cq.Workplane().add(s).edges("|Y").fillet(3).val()
    for x, z in ((16, 66), (-16, 110)):
        s = s.cut(cyl(2.4, (x, -6, z), (x, 0, z)))
    s = s.cut(box(-3, 3, -6, 0, 84, 88))   # harness slot
    return s


def chest_core_housing():
    """Cup: body + flange + back wall + central optical baffle. LED ring and diffuser load from the front."""
    s = union(cyl(46, (0, -25, 105), (0, -22, 105)),
              cyl(40.6, (0, -40, 105), (0, -22, 105)))
    s = s.cut(cyl(37.6, (0, -41, 105), (0, -24.1, 105)))         # LED-ring / diffuser bore
    s = s.fuse(cyl(21, (0, -40, 105), (0, -24.1, 105)))          # central baffle (joins back wall)
    s = s.cut(cyl(17, (0, -41, 105), (0, -20, 105)))             # optical path to MAX30102 / centre LED
    for k in range(2):                                           # ring harness holes
        a = math.radians(90 + 180 * k)
        s = s.cut(cyl(3.5, (15 * math.cos(a), -25, 105 + 15 * math.sin(a)), (15 * math.cos(a), -21, 105 + 15 * math.sin(a))))
    return s.clean()


def chest_ring_diffuser():
    return cyl(37.2, (0, -40, 105), (0, -27.5, 105)).cut(cyl(21.6, (0, -41, 105), (0, -27, 105))).clean()


def chest_center_lens():
    return cyl(16.6, (0, -41, 105), (0, -28, 105)).fuse(sphere(16.6, (0, -41, 105)).intersect(
        box(-10, 10, -44, -41, 95, 115))).clean()


# ================================================================ HEAD
def head_shell(side):
    s = head_outer().cut(head_outer(-W))
    if side == "front":
        s = s.cut(visor_window())
        ledge = head_outer(-W).cut(head_outer(-W - 2.0)).intersect(visor_window(2).cut(visor_window(-4)))
        ledge = ledge.intersect(box(-200, 200, -200, -20, 0, 400))
        s = s.fuse(ledge)
        for sx in (-1, 1):                                       # magenta accent pipes
            s = s.cut(cyl(5.4, (sx * 14, -36, 240), (sx * 14, -36, 270)))
    else:
        for r in (0, 6, 12):                                     # speaker grille
            n = 1 if r == 0 else 6 * (r // 6)
            for k in range(n):
                a = 2 * math.pi * k / n
                s = s.cut(cyl(3.0, (r * math.cos(a), 50, 205 + r * math.sin(a)),
                              (r * math.cos(a), 70, 205 + r * math.sin(a))))
    for sx in (-1, 1):
        s = s.cut(cyl(12 + 2 * C, (sx * 60, 0, P["pod_z"]), (sx * 80, 0, P["pod_z"])))
    s = s.cut(cyl(26 + 2 * C, (0, 0, 140), (0, 0, 156)))
    s = half(s, side)
    for pt, d in HEAD_BOSSES:
        s = s.fuse(split_boss(pt, d, head_outer(-0.5), side))
    if side == "back":   # battery EN slide-switch slot
        s = s.cut(rrect_prism_y(26.5, 33.5, 174.5, 177.5, 1.0, 45, 75))
    if side == "back":   # speaker retaining ring (28 mm speaker, ESTIMATE)
        ring = cyl(33, (0, 53.5, 205), (0, 70, 205)).cut(cyl(28.6, (0, 53, 205), (0, 71, 205)))
        s = s.fuse(ring.intersect(head_outer(-1.0)))
    return s.clean()


def head_bulkhead():
    sec = head_outer(-W - 0.3).intersect(box(-100, 100, -1.5, 1.5, 0, 400))
    cuts = [neck_zone(1.0), box(-19, 19, -2, 2, 140, 156)]
    for sx in (-1, 1):
        cuts.append(box(min(sx * 63, sx * 90), max(sx * 63, sx * 90), -2, 2, 209, 231))
    s = sec.cut(union(*cuts))
    for (x, z), _ in HEAD_BOSSES:
        s = s.cut(cyl(3.4, (x, -3, z), (x, 3, z)))
    s = s.cut(rrect_prism_y(-10, 10, 158, 172, 3, -3, 3))       # harness
    for sx in (-1, 1):
        s = s.cut(cyl(1.8, (sx * 30.5, -3, 207), (sx * 30.5, 3, 207)))          # battery-tray M2
    for x, z in ((14.5, 160.5), (45.5, 178.5)):
        s = s.cut(cyl(1.8, (x, -3, z), (x, 3, z)))                             # PowerBoost M2
    for sx in (-1, 1):
        s = s.cut(rrect_prism_y(sx * 50 - 5, sx * 50 + 5, 214, 226, 3, -3, 3))  # pod harness
        s = s.cut(cyl(2.4, (sx * 35, -3, 190), (sx * 35, 3, 190)))             # face-carrier screws
    return s.clean()


def face_carrier():
    plate = rrect_prism_y(-50, 50, 182, 228, 14, -48, -45)
    for sx in (-1, 1):
        plate = plate.fuse(cyl(7, (sx * 35, -45, 190), (sx * 35, -1.5, 190)))
        plate = plate.cut(cyl(2.4, (sx * 35, -50, 190), (sx * 35, 0, 190)))
    plate = plate.cut(rrect_prism_y(-6, 6, 186, 196, 2, -50, -40))  # wire pass
    return plate.clean()


def eye_lightpipe(sx):
    cx, cz = sx * 28, 204.0
    band = cyl(28, (cx, -58.5, cz), (cx, -50, cz)).cut(cyl(20, (cx, -59, cz), (cx, -49, cz)))
    band = band.intersect(box(cx - 20, cx + 20, -60, -49, cz + 3, cz + 20))
    caps = union(*[cyl(4, (cx + sgn * 12 * math.cos(math.radians(14)), -58.5, cz + 3.0),
                       (cx + sgn * 12 * math.cos(math.radians(14)), -50, cz + 3.0)) for sgn in (-1, 1)])
    return band.fuse(caps).clean()


def accent_lightpipe(sx):
    return union(cyl(5.0, (sx * 14, -36, 248), (sx * 14, -36, 262)),
                 cyl(8.0, (sx * 14, -36, 245), (sx * 14, -36, 248)))


def visor():
    v = head_outer(1.2).cut(head_outer(-W)).intersect(visor_window(-0.15))
    return v.intersect(box(-200, 200, -200, -20, 0, 400)).clean()


def neck_coupler():
    s = neck_zone(0.0)
    return s.cut(cyl(14, (0, 0, 120), (0, 0, 170))).clean()


# ================================================================ EAR PODS + EARS
def ear_pod(sx):
    z = P["pod_z"]
    s = pod_outer(sx).cut(head_outer(0.3))
    s = s.intersect(cyl(46, (sx * 50, 0, z), (sx * 84, 0, z)))
    s = s.cut(cyl(38.4, (sx * 76, 0, z), (sx * 85, 0, z)))       # cavity (LED ring + sensor)
    s = s.fuse(pod_peg_zone(sx).cut(cyl(7, (sx * 60, 0, z), (sx * 80, 0, z))))
    s = s.cut(cyl(7, (sx * 60, 0, z), (sx * 80, 0, z)))
    s = s.cut(cyl(3.4, (sx * 78, 0, 236), (sx * 78, 0, 246)))   # ear screw
    return s.clean()


def pod_rim_diffuser(sx):
    z = P["pod_z"]
    return cyl(46, (sx * 84, 0, z), (sx * 88, 0, z)).cut(cyl(37, (sx * 83, 0, z), (sx * 89, 0, z)))


def pod_cap(sx, kind):
    z = P["pod_z"]
    c = cyl(36.6, (sx * 84, 0, z), (sx * 88.6, 0, z))
    dome = ellipsoid(2.4, 18.3, 18.3, (sx * 88.6, 0, z)).intersect(
        box(88.6 if sx > 0 else -92, 92 if sx > 0 else -88.6, -20, 20, z - 20, z + 20))
    c = c.fuse(dome).clean()
    if kind == "mic":
        for dy, dz in ((0, 0), (3.5, 0), (-3.5, 0), (0, 3.5), (0, -3.5)):
            c = c.cut(cyl(1.6, (sx * 80, dy, z + dz), (sx * 95, dy, z + dz)))
    else:
        c = c.cut(cyl(8.0, (sx * 80, 0, z), (sx * 95, 0, z)))   # BH1750 window (clear insert / open)
    return c


def ear(sx):
    base = (sx * 74, 0, 236.0)
    L, w, t = 100.0, 26.0, 14.0
    wp = (cq.Workplane("XY").slot2D(L, w, angle=90).extrude(t / 2, both=True))
    e = wp.val().rotate(V(0, 0, 0), V(1, 0, 0), 90)          # slot now in XZ, thickness along Y
    try:
        e = cq.Workplane().add(e).edges().fillet(5.5).val()
    except Exception:
        pass
    e = e.translate(V(0, 0, L / 2 - w / 2 + 4))               # bottom of slot near z=+4-w/2... base
    # inner-face (front, -Y) recessed panel + row of holes
    panel = cq.Workplane().add(box(-8, 8, -t / 2 - 1, -t / 2 + 1.2, 22, 78)).edges("|Y").fillet(7.9).val()
    e = e.cut(panel)
    for k in range(6):
        e = e.cut(cyl(3.0, (0, -t / 2 - 2, 28 + k * 9.6), (0, -t / 2 + 4.5, 28 + k * 9.6)))
    e = e.rotate(V(0, 0, 0), V(0, 1, 0), sx * 8.0)            # splay outward
    e = e.translate(V(*base))
    e = e.cut(box(-200, 200, -50, 50, 0, 232)).cut(pod_outer(sx, 0.3)).cut(head_outer(0.5))
    e = e.cut(cyl(2.6, (sx * 78, 0, 230), (sx * 78, 0, 252)))   # M3 self-tap / insert pilot
    return e.clean()


# ================================================================ LIMBS
def arm(sx):
    z = P["arm_z"]
    a = union(capsule(20, (sx * 41, 0, z + 2), (sx * 50, -3, 84)),
              ellipsoid(11, 12, 13, (sx * 52, -4, 74)),
              ellipsoid(4.5, 5, 6, (sx * 44, -10, 80)))        # mitten thumb
    a = a.cut(torso_outer(C))
    a = a.fuse(arm_peg_zone(sx))
    return a.clean()


def leg(sx):
    x = sx * P["leg_x"]
    l = union(cyl(20, (x, 0, 20), (x, 0, 58)),
              ellipsoid(13, 17, 8, (x, -4, P["foot_z"] + 8)))
    l = l.cut(torso_outer(C))
    l = l.fuse(leg_peg_zone(sx))
    return l.clean()


# ================================================================ PEDESTAL
def pedestal():
    """Faceted hex 'rock' with the crystal-reading station built into the front."""
    import random
    R, H = P["ped_R"], P["ped_h"]
    hex_full = cq.Workplane("XY").polygon(6, 2 * R).extrude(H).translate((0, 0, -H)).val()
    hexw = hex_full
    rnd = random.Random(1210)          # fixed seed -> repeatable "rock" facets
    for k in range(6):
        a = math.radians(k * 60 + rnd.uniform(-12, 12))
        tilt = rnd.uniform(28, 48)
        depth = rnd.uniform(7, 14)
        cut = box(-200, 200, -200, 200, 0, 200)
        cut = cut.rotate(V(0, 0, 0), V(0, 1, 0), tilt)
        cut = cut.translate(V(R * 0.86 - depth, 0, -depth * 0.6))
        cut = cut.rotate(V(0, 0, 0), V(0, 0, 1), math.degrees(a))
        hexw = hexw.cut(cut)
    for k in range(5):                                     # shallow top facets
        a = rnd.uniform(0, 360); tilt = rnd.uniform(3, 7)
        cut = box(-300, 300, -300, 300, 0, 200).rotate(V(0, 0, 0), V(0, 1, 0), tilt)
        cut = cut.translate(V(rnd.uniform(25, 45), 0, -rnd.uniform(0.5, 2.5))).rotate(V(0, 0, 0), V(0, 0, 1), a)
        hexw = hexw.cut(cut)
    sy = P["st_y"]
    # flat "altar" stone for the crystal station (kept inside the hex outline)
    hexw = hexw.fuse(cyl(74, (0, sy, -10), (0, sy, 0)).intersect(hex_full))
    # --- robot float tube + USB
    hexw = hexw.cut(cyl(P["tube_od"] + 0.3, (0, 0, -25), (0, 0, 5)))      # tube socket
    hexw = hexw.cut(cyl(8, (0, 0, -34), (0, 0, -20)))
    hexw = hexw.cut(cyl(8, (0, -2, -26), (0, 100, -26)))                   # USB cable channel
    hexw = hexw.cut(box(-8, 8, 64, 100, -32, -20))                         # USB-C breakout pocket
    # --- crystal station (ZS-6xx)
    hexw = hexw.cut(cyl(26, (0, sy, -12), (0, sy, 1)))                     # crystal cup
    hexw = hexw.cut(cyl(30, (0, sy, -14), (0, sy, -12)))                   # window seat
    hexw = hexw.cut(cyl(32, (0, sy, -46), (0, sy, -14)))                   # LED-plug access bore
    hexw = hexw.cut(cyl(44.6, (0, sy, -46), (0, sy, -42)))                 # plug flange recess
    for sx in (-1, 1):
        hexw = hexw.cut(cyl(2.6, (sx * 19.5, sy, -46), (sx * 19.5, sy, -34)))   # M3 self-tap
    ring = cyl(51, (0, sy, -5), (0, sy, 1)).cut(cyl(47, (0, sy, -6), (0, sy, 2)))
    hexw = hexw.cut(ring)                                                 # light-trap groove
    hexw = hexw.cut(box(28.8, 34.2, sy - 4.2, sy + 4.2, -8.2, 1))          # pogo receptacle pocket
    hexw = hexw.cut(cyl(5, (31.5, sy, -8), (31.5, sy, -30)))
    hexw = hexw.cut(cyl(6, (31.5, sy, -30), (2, -4, -30)))                 # pogo harness channel
    hexw = hexw.cut(box(-36.2, -27.8, sy - 1.3, sy + 1.3, -3.7, 1))        # reed-switch slot
    hexw = hexw.cut(cyl(4, (-32, sy, -3.7), (-32, sy, -30)))
    hexw = hexw.cut(cyl(6, (-32, sy, -30), (-2, -4, -30)))                 # reed harness channel
    hexw = hexw.cut(cyl(8, (0, sy + 15, -30), (0, -2, -30)))                # LED harness channel
    # --- LED driver bay (bottom, with cover ZS-604)
    hexw = hexw.cut(box(-12, 12, 10, 36, -43.2, -36))
    hexw = hexw.cut(box(-16.2, 16.2, 5.8, 40.2, -46, -43))
    for sx in (-1, 1):
        hexw = hexw.cut(cyl(2.0, (sx * 14, 23, -46), (sx * 14, 23, -37)))
    hexw = hexw.cut(cyl(6, (0, 20, -37), (0, 20, -26)))
    for k in range(3):                                                     # felt-pad recesses
        a = math.radians(90 + k * 120)
        hexw = hexw.cut(cyl(16, (50 * math.cos(a), 50 * math.sin(a), -H - 1), (50 * math.cos(a), 50 * math.sin(a), -H + 1)))
    sols = hexw.Solids()
    if len(sols) == 1:
        hexw = sols[0]
    if not hexw.isValid():
        hexw = hexw.fix()
    return hexw


# ================================================================ CRYSTAL STATION
def station_led_plug():
    """ZS-601: plugs up from under the pedestal; LED board (white / 365 nm UV / 940 nm IR) faces up
    through the window into the crystal. Mixing cavity should be white-painted or PTFE-lined."""
    sy = P["st_y"]
    s = union(cyl(31.6, (0, sy, -42), (0, sy, -14)), cyl(44, (0, sy, -45), (0, sy, -42)))
    s = s.cut(cyl(22, (0, sy, -20), (0, sy, -13)))                        # mixing cavity
    s = s.cut(box(-10.2, 10.2, sy - 10.2, sy + 10.2, -22.4, -19.9))       # LED PCB pocket
    s = s.cut(cyl(5, (0, sy, -33), (0, sy, -22)))                         # wire down
    s = s.cut(cyl(5, (0, sy, -30), (0, sy + 17, -30)))                    # wire out to channel
    for sx in (-1, 1):
        s = s.cut(cyl(3.4, (sx * 19.5, sy, -46), (sx * 19.5, sy, -41)))
    return s.clean()


def light_shield():
    """ZS-602: removable light-tight shield. Flange + skirt drop into the groove (light trap);
    AS7341 rides in the top on ZS-603; 4 pogo pads + reed magnet under the flange."""
    sy = P["st_y"]
    s = union(cyl(50, (0, sy, 0), (0, sy, 40)), cyl(50, (0, sy, 40), (0, sy, 43)),
              cyl(72, (0, sy, 0), (0, sy, 3)),
              cyl(50.4, (0, sy, -4.6), (0, sy, 0)),
              box(24.5, 32, sy - 3.5, sy + 3.5, 3, 40))                     # harness rib
    s = s.cut(cyl(47.6, (0, sy, -5), (0, sy, 0)))                         # skirt ID
    s = s.cut(cyl(44, (0, sy, -1), (0, sy, 40)))                          # interior
    s = s.cut(cyl(2.5, (29.5, sy, -0.1), (29.5, sy, 38)))                 # harness bore
    s = s.cut(cyl(2.5, (21, sy, 37), (30, sy, 37)))
    s = s.cut(box(28.8, 34.2, sy - 4.7, sy + 4.7, -0.1, 1.2))             # pogo pad pocket
    s = s.cut(cyl(6.3, (-32, sy, -0.1), (-32, sy, 2.1)))                  # reed magnet pocket
    for k in range(3):                                                    # finger grips
        a = math.radians(60 + 120 * k)
        s = s.cut(sphere(10, (29.0 * math.cos(a), sy + 29.0 * math.sin(a), 24)))
    return s.clean()


def sensor_mount():
    """ZS-603: disc in the shield top. AS7341 board on top, chip looking down through a 12 mm
    aperture; optional 20 mm UV-cut filter in the recess below (fluorescence mode)."""
    sy = P["st_y"]
    s = cyl(43.6, (0, sy, 31), (0, sy, 34))
    s = s.cut(cyl(12, (0, sy, 30), (0, sy, 35)))
    s = s.cut(cyl(20.4, (0, sy, 30.9), (0, sy, 33)))
    s = s.cut(box(17, 23, sy - 3, sy + 3, 30, 35))                        # harness notch
    for sx in (-1, 1):
        s = s.cut(cyl(2.2, (sx * 10.2, sy, 30), (sx * 10.2, sy, 35)))     # M2 screws to board (ESTIMATE spacing)
    return s.clean()


def driver_bay_cover():
    s = box(-16, 16, 6, 40, -45, -43)
    for sx in (-1, 1):
        s = s.cut(cyl(2.4, (sx * 14, 23, -46), (sx * 14, 23, -42)))
    return s


def dark_reference_plug():
    """ZS-605: opaque black plug that fills the cup – stray-light / dark-reference check."""
    sy = P["st_y"]
    return union(cyl(25.4, (0, sy, -12), (0, sy, 0)), cyl(12, (0, sy, 0), (0, sy, 8)))


def crystal_proxy():
    sy = P["st_y"]
    body = cq.Workplane("XY").polygon(6, 18).extrude(24).val().translate(V(0, sy, -12))
    tip = (cq.Workplane("XY").polygon(6, 18).workplane(offset=9).polygon(6, 1.5).loft().val()
           .translate(V(0, sy, 12)))
    return body.fuse(tip).clean().rotate(V(0, sy, 0), V(0, sy, 1), 15)


# ================================================================ BATTERY BAY (head)
def battery_tray():
    """ZS-109: 503450-class protected 1S LiPo slides in from the top; 2 lips hold it to the bulkhead."""
    s = box(-27.6, 27.6, 1.5, 9, 188.4, 226.6)
    s = s.cut(box(-25.3, 25.3, 1.4, 10, 190.2, 227))
    for x in (-15, 15):
        s = s.fuse(box(x - 2, x + 2, 8, 9, 188.4, 226.6))
    for sx in (-1, 1):
        tab = box(27.6 if sx > 0 else -33, 33 if sx > 0 else -27.6, 1.5, 4, 203, 211)
        s = s.fuse(tab).cut(cyl(2.4, (sx * 30.5, 1, 207), (sx * 30.5, 5, 207)))
    return s.clean()


def support_tube():
    return cyl(P["tube_od"], (0, 0, -25), (0, 0, 50)).cut(cyl(P["tube_id"], (0, 0, -26), (0, 0, 51)))


# ================================================================ PURCHASED-PART PROXIES (visual + fit only)
def proxies():
    z = P["pod_z"]
    pr = {
        "PX_RB-001_esp32s3_devkitc1": box(-13, 13, 3.5, 17.5, 60.5, 129.5),     # ~69x26 (ESTIMATE incl. headers)
        "PX_RB-002_icm42688_imu": box(-11.5, 11.5, -8.6, -4.6, 91, 109),
        "PX_RB-004_bme280": box(-9, 9, -8.6, -4.6, 64, 80),
        "PX_RB-005_max30102": box(-11, 11, -21.9, -16.9, 96, 114),
        "PX_RB-006_inmp441_podL": box(-80.2, -76.2, -11.5, 11.5, z - 7.5, z + 7.5),
        "PX_RB-003_bh1750_podR": box(76.2, 80.2, -9, 9, z - 8, z + 8),
        "PX_RB-007_gnss_head": box(-15, 15, 2, 8, 235, 260),
        "PX_led_ring12_chest": cyl(37, (0, -27.3, 105), (0, -24.3, 105)).cut(cyl(23, (0, -28, 105), (0, -24, 105))),
        "PX_led_ring12_podL": cyl(37, (-80.5, 0, z), (-83.5, 0, z)).cut(cyl(23, (-80, 0, z), (-84, 0, z))),
        "PX_led_ring12_podR": cyl(37, (80.5, 0, z), (83.5, 0, z)).cut(cyl(23, (80, 0, z), (84, 0, z))),
        "PX_led_eyeL": box(-42, -14, -50, -48, 207, 222),
        "PX_led_eyeR": box(14, 42, -50, -48, 207, 222),
        "PX_led_accent_pcb": box(-20, 20, -40, -32, 241.5, 244.5),
        "PX_speaker28": cyl(28, (0, 53.6, 205), (0, 59.6, 205)),
        "PX_max98357a_amp": box(-9, 9, 2, 5, 170, 188),
        "PX_lipo_503450_protected": box(-25, 25, 1.6, 7.6, 190.5, 224.5),
        "PX_powerboost_1000c": box(12, 48, 1.6, 7.6, 158, 181),
        "PX_slide_switch_EN": union(box(25.5, 34.5, 51.5, 55.5, 174, 178), box(29, 31.5, 55.5, 59.5, 175, 177)),
        "PX_usbc_breakout_pedestal": box(-6, 6, 70, 82, -30, -22),
        "PX_crystal_window_borosilicate": cyl(29.6, (0, P["st_y"], -14), (0, P["st_y"], -12)),
        "PX_station_led_board": box(-10, 10, P["st_y"] - 10, P["st_y"] + 10, -22, -20.4),
        "PX_led_white": box(-7.75, -4.25, P["st_y"] - 1.75, P["st_y"] + 1.75, -20.4, -19.0),
        "PX_led_uv365": box(-1.75, 1.75, P["st_y"] - 1.75, P["st_y"] + 1.75, -20.4, -19.0),
        "PX_led_ir940": box(4.25, 7.75, P["st_y"] - 1.75, P["st_y"] + 1.75, -20.4, -19.0),
        "PX_AS7341_breakout": union(box(-12.8, 12.8, P["st_y"] - 8.9, P["st_y"] + 8.9, 34, 38),
                                    box(-1.6, 1.6, P["st_y"] - 1.6, P["st_y"] + 1.6, 33, 34)),
        "PX_uv_cut_filter_optional": cyl(20, (0, P["st_y"], 31), (0, P["st_y"], 33)),
        "PX_pogo_receptacle_4p": box(29, 34, P["st_y"] - 4, P["st_y"] + 4, -8, 0),
        "PX_pogo_pads_4p": box(29, 34, P["st_y"] - 4.5, P["st_y"] + 4.5, 0, 1.2),
        "PX_reed_switch": box(-36, -28, P["st_y"] - 1.1, P["st_y"] + 1.1, -3.5, -1.3),
        "PX_magnet_6x2": cyl(6, (-32, P["st_y"], 0), (-32, P["st_y"], 2)),
        "PX_station_driver_board": box(-11, 11, 12, 34, -42.5, -38.5),
        "PX_crystal_sample": crystal_proxy(),
    }
    return pr


def all_parts():
    parts = {
        "ZS-101_head_shell_front": head_shell("front"),
        "ZS-102_head_shell_back": head_shell("back"),
        "ZS-103_head_bulkhead": head_bulkhead(),
        "ZS-104_visor": visor(),
        "ZS-105_face_carrier": face_carrier(),
        "ZS-106_eye_lightpipe_L": eye_lightpipe(-1),
        "ZS-106_eye_lightpipe_R": eye_lightpipe(1),
        "ZS-107_accent_lightpipe_L": accent_lightpipe(-1),
        "ZS-107_accent_lightpipe_R": accent_lightpipe(1),
        "ZS-108_neck_coupler": neck_coupler(),
        "ZS-109_battery_tray": battery_tray(),
        "ZS-201_ear_pod_L_mic": ear_pod(-1),
        "ZS-202_ear_pod_R_light": ear_pod(1),
        "ZS-203_pod_rim_diffuser_L": pod_rim_diffuser(-1),
        "ZS-203_pod_rim_diffuser_R": pod_rim_diffuser(1),
        "ZS-204_pod_cap_L_mic": pod_cap(-1, "mic"),
        "ZS-205_pod_cap_R_light": pod_cap(1, "light"),
        "ZS-206_ear_L": ear(-1),
        "ZS-206_ear_R": ear(1),
        "ZS-301_torso_shell_front": torso_shell("front"),
        "ZS-302_torso_shell_back": torso_shell("back"),
        "ZS-303_torso_bulkhead_esp32_cradle": torso_bulkhead(),
        "ZS-304_sensor_sled": sensor_sled(),
        "ZS-305_chest_core_housing": chest_core_housing(),
        "ZS-306_chest_ring_diffuser": chest_ring_diffuser(),
        "ZS-307_chest_center_lens": chest_center_lens(),
        "ZS-401_arm_L": arm(-1),
        "ZS-401_arm_R": arm(1),
        "ZS-402_leg_L": leg(-1),
        "ZS-402_leg_R": leg(1),
        "ZS-501_pedestal": pedestal(),
        "ZS-601_station_led_plug": station_led_plug(),
        "ZS-602_light_shield": light_shield(),
        "ZS-603_sensor_mount": sensor_mount(),
        "ZS-604_driver_bay_cover": driver_bay_cover(),
        "ZS-502_support_tube_acrylic": support_tube(),
    }
    return parts


def alternates():
    """Parts that occupy the cup INSTEAD of the crystal (checked separately)."""
    sy = P["st_y"]
    return {"ZS-605_dark_reference_plug": dark_reference_plug(),
            "PX_ptfe_white_reference_25x3": cyl(25.4, (0, sy, -12), (0, sy, -9))}
