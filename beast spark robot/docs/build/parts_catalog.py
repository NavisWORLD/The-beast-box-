import sys, json, textwrap
sys.path.insert(0, "/workspace/zeref-spark/docs/build")
from rlib import *
from partmeta import M
meta = json.load(open(f"{ROOT}/out/parts_meta.json"))
OUT = f"{ROOT}/docs/parts"
stems = all_stems()
missing = [s for s in stems if s not in M]
print("missing meta:", missing)
done = []
for s in stems:
    name, mat, orient, qty, fast, grp = M[s]
    img, _ = render_scene([s], "iso_fit", 900, 820)
    C = Image.new("RGB", (1600, 1000), "white")
    C.paste(img, (0, 100))
    d = ImageDraw.Draw(C)
    d.rectangle([0, 0, 1600, 92], fill="#101633")
    pn = s.split("_")[0] if s.startswith("ZS") else "PX (third-party proxy)"
    d.text((24, 12), f"{pn}", fill="#7ff6ff", font=font(40, True))
    d.text((24, 58), name, fill="#ffffff", font=font(24, True))
    kind = "PRINTED / MADE PART — AI-generated CAD geometry" if s.startswith("ZS") else "THIRD-PARTY MODULE — simplified proxy, not the real part geometry"
    if "502" in s: kind = "BOUGHT STOCK (cut to length) — CAD geometry AI-generated"
    x0 = 930; y = 120
    rows = [("Type", kind), ("File", s), ("Material / colour", mat), ("Print orientation / settings", orient),
            ("Qty (this file)", str(qty)), ("Fasteners / fixing", fast), ("Sub-assembly", grp)]
    if s in meta:
        z = meta[s]["size"]
        rows.append(("Envelope W x D x H", f"{z[0]} x {z[1]} x {z[2]} mm (ESTIMATE, CAD)"))
        if s.startswith("ZS"):
            rows.append(("Solid volume", f"{meta[s]['volume_mm3']/1000:.1f} cm3 (CAD, before infill)"))
    for k, v in rows:
        d.text((x0, y), k.upper(), fill="#5b6785", font=font(17, True)); y += 24
        for ln in textwrap.wrap(v, 44):
            d.text((x0, y), ln, fill="#101828", font=font(21)); y += 27
        y += 12
    d.rectangle([0, 930, 1600, 1000], fill="#101633")
    d.text((24, 938), LABEL, fill="#ff9ae8", font=font(19, True))
    d.text((24, 966), CREDIT, fill="#c9d3ff", font=font(16))
    C.save(f"{OUT}/{s}.png"); done.append(s)
print(len(done), "cards")
