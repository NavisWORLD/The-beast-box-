"""ZEREF SPARK interference / fit check (assembled state, nominal geometry).
DESIGN TARGET — not printed or test-fitted. Checks CAD intent only."""
import sys, os, json, itertools
sys.path.insert(0, os.path.dirname(__file__))
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
import zs_parts as zp

parts = zp.all_parts(); parts.update(zp.proxies())
names = list(parts)
bbs = {n: parts[n].BoundingBox() for n in names}
TOL = 0.5  # mm^3 — anything above is flagged
hits, near, checked = [], [], 0
def bb_overlap(a, b, m=1.0):
    return not (a.xmax + m < b.xmin or b.xmax + m < a.xmin or a.ymax + m < b.ymin or b.ymax + m < a.ymin
                or a.zmax + m < b.zmin or b.zmax + m < a.zmin)
for a, b in itertools.combinations(names, 2):
    if not bb_overlap(bbs[a], bbs[b]):
        continue
    checked += 1
    v = parts[a].intersect(parts[b]).Volume()
    if v > TOL:
        hits.append((a, b, round(v, 2)))
        print("INTERFERENCE", a, b, round(v, 2), flush=True)
    else:
        d = BRepExtrema_DistShapeShape(parts[a].wrapped, parts[b].wrapped)
        dist = d.Value() if d.IsDone() else -1
        near.append((a, b, round(dist, 3)))
# alternates (dark plug, PTFE reference) sit in the cup instead of the crystal
alt = zp.alternates()
for an, ash in alt.items():
    abb = ash.BoundingBox()
    for n in names:
        if n == "PX_crystal_sample" or not bb_overlap(abb, bbs[n]):
            continue
        checked += 1
        v = ash.intersect(parts[n]).Volume()
        if v > TOL:
            hits.append((an, n, round(v, 2))); print("INTERFERENCE", an, n, round(v, 2), flush=True)
        else:
            d = BRepExtrema_DistShapeShape(ash.wrapped, parts[n].wrapped)
            near.append((an, n, round(d.Value(), 3)))
names_all = names + list(alt)
res = dict(n_shapes=len(names_all), pairs_total=len(names) * (len(names) - 1) // 2 + len(alt) * (len(names) - 1), pairs_bbox_checked=checked,
           interference_threshold_mm3=TOL, interferences=hits,
           close_pairs_min_gap_mm=sorted(near, key=lambda t: t[2]))
json.dump(res, open(os.path.join(os.path.dirname(__file__), "..", "out", "fit_check.json"), "w"), indent=1)
print("checked", checked, "pairs;", len(hits), "interferences")
for a, b, d in sorted(near, key=lambda t: t[2])[:60]:
    print(f"gap {d:7.3f}  {a}  <->  {b}")
