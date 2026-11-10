"""ZEREF SPARK — CadQuery helper primitives.
DESIGN TARGET — not printed or test-fitted. Units: mm. Z up, front = -Y."""
import cadquery as cq
from cadquery import Vector as V
from OCP.gp import gp_GTrsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_GTransform


def ellipsoid(a, b, c, center=(0, 0, 0)):
    s = cq.Solid.makeSphere(1.0, V(0, 0, 0), V(0, 0, 1), -90, 90, 360)
    g = gp_GTrsf()
    g.SetValue(1, 1, a); g.SetValue(2, 2, b); g.SetValue(3, 3, c)
    t = BRepBuilderAPI_GTransform(s.wrapped, g, True)
    return cq.Shape.cast(t.Shape()).translate(V(*center))


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(d, p0, p1):
    p0, p1 = V(*p0), V(*p1)
    axis = p1 - p0
    return cq.Solid.makeCylinder(d / 2, axis.Length, p0, axis.normalized())


def sphere(d, c):
    return cq.Solid.makeSphere(d / 2, V(*c), V(0, 0, 1), -90, 90, 360)


def capsule(d, p0, p1):
    return cyl(d, p0, p1).fuse(sphere(d, p0)).fuse(sphere(d, p1)).clean()


def rounded_box(hx, hy, hz, r, center=(0, 0, 0)):
    """Exact Minkowski rounded box (half extents hx,hy,hz; edge radius r)."""
    ix, iy, iz = hx - r, hy - r, hz - r
    s = box(-hx, hx, -iy, iy, -iz, iz)
    s = s.fuse(box(-ix, ix, -hy, hy, -iz, iz)).fuse(box(-ix, ix, -iy, iy, -hz, hz))
    for sx in (-1, 1):
        for sy in (-1, 1):
            s = s.fuse(cyl(2 * r, (sx * ix, sy * iy, -iz), (sx * ix, sy * iy, iz)))
        for sz in (-1, 1):
            s = s.fuse(cyl(2 * r, (sx * ix, -iy, sz * iz), (sx * ix, iy, sz * iz)))
    for sy in (-1, 1):
        for sz in (-1, 1):
            s = s.fuse(cyl(2 * r, (-ix, sy * iy, sz * iz), (ix, sy * iy, sz * iz)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                s = s.fuse(sphere(2 * r, (sx * ix, sy * iy, sz * iz)))
    return s.clean().translate(V(*center))


def rrect_prism_y(x0, x1, z0, z1, r, y0, y1):
    """Rounded rectangle in XZ, extruded along Y from y0 to y1."""
    b = box(x0, x1, min(y0, y1), max(y0, y1), z0, z1)
    return cq.Workplane().add(b).edges("|Y").fillet(r).val()


def union(*shapes):
    s = shapes[0]
    for o in shapes[1:]:
        s = s.fuse(o)
    return s.clean()


def half(shape, side):
    """Split at y=0. side='front' keeps y<0, 'back' keeps y>0."""
    big = 2000
    cutter = box(-big, big, -big, 0, -big, big) if side == "front" else box(-big, big, 0, big, -big, big)
    return shape.intersect(cutter).clean()
