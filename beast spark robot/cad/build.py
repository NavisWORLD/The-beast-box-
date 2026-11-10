"""Build every ZEREF SPARK part -> STEP (assembly coords) + STL (seated on bed).
DESIGN TARGET — not printed or test-fitted."""
import sys, json, time, os
sys.path.insert(0, os.path.dirname(__file__))
import cadquery as cq
from cadquery import Vector as V
import zs_parts as zp

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
only = sys.argv[1:]
meta = {}
parts = {}
builders = zp.all_parts.__code__  # not used; build lazily below
t0 = time.time()
allp = zp.all_parts()
allp.update(zp.proxies())
allp.update(zp.alternates())
for name, shp in allp.items():
    if only and name not in only:
        continue
    bb = shp.BoundingBox()
    meta[name] = dict(valid=bool(shp.isValid()), n_solids=len(shp.Solids()), volume_mm3=round(shp.Volume(), 1),
                      bbox=[round(v, 1) for v in (bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax)],
                      size=[round(bb.xlen, 1), round(bb.ylen, 1), round(bb.zlen, 1)])
    sub = "proxy" if name.startswith("PX_") else ""
    cq.exporters.export(shp, os.path.join(OUT, "step", sub, name + ".step"))
    cq.exporters.export(shp, os.path.join(OUT, "stl", "assembly_coords", sub, name + ".stl"),
                        tolerance=0.08, angularTolerance=0.15)
    if not sub:
        bed = shp.translate(V(-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))
        cq.exporters.export(bed, os.path.join(OUT, "stl", name + ".stl"), tolerance=0.08, angularTolerance=0.15)
    print(f"{name:45s} ok vol={meta[name]['volume_mm3']:>10} size={meta[name]['size']} valid={meta[name]['valid']}", flush=True)
json.dump(meta, open(os.path.join(OUT, "parts_meta.json"), "w"), indent=1)
# full assembly STEP
asm = cq.Assembly(name="ZEREF_SPARK_DESIGN_TARGET")
for name, shp in allp.items():
    asm.add(shp, name=name)
asm.save(os.path.join(OUT, "ZEREF_SPARK_assembly.step"))
print("done", round(time.time() - t0, 1), "s")
