"""Isolated virtual arena and physically-derived *simulated* sensor raster.

No animal camera or environmental hardware. The camera is generated from the
rendered virtual scene and then segmented; reward labels are inaccessible until
terminal contact. Sensory tuning and locomotion are computational assumptions.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
import numpy as np

STATION_RGB = ((35, 222, 248), (255, 188, 37))
STONE_RGB = (117, 125, 139)
SKY_RGB = (18, 43, 57)
WIDTH, HEIGHT = 96, 64
FOV = math.radians(114)
RANGE = 5.15
BOUNDS = (-3.9, 3.9, -2.8, 2.8)
OBSTACLES = ((-.65, .3, .53), (.75, .46, .58), (0.0, 1.76, .32))


def wrap(r: float) -> float:
    return (r + math.pi) % (2 * math.pi) - math.pi


def los(a: tuple[float, float], b: tuple[float, float], obstacles=OBSTACLES) -> bool:
    """Segment/circle occlusion, not an oracle for target reward."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d2 = dx*dx + dy*dy
    if d2 < 1e-12:
        return True
    for ox, oy, radius in obstacles:
        t = max(0.0, min(1.0, ((ox-a[0])*dx + (oy-a[1])*dy)/d2))
        px, py = a[0] + t*dx, a[1] + t*dy
        if math.hypot(px-ox, py-oy) < radius * .87:
            return False
    return True


def in_view(pos, heading, other, obstacles=OBSTACLES):
    dx, dy = other[0]-pos[0], other[1]-pos[1]
    dist = math.hypot(dx, dy)
    bearing = wrap(math.atan2(dy, dx)-heading)
    return dist <= RANGE and abs(bearing) < FOV/2 and los(pos, other, obstacles), bearing, dist


def camera(pos, heading, stations, obstacles=OBSTACLES) -> np.ndarray:
    """96x64 RGB egocentric pixel sensor. Station color does not encode reward."""
    im = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    im[:] = SKY_RGB
    # Fine horizon provides a visible orientation reference independent of reward.
    im[HEIGHT//2:] = (26, 65, 59)
    for ob in obstacles:
        visible, b, dist = in_view(pos, heading, ob, ())
        if visible and dist >= .01:
            cx = round((.5 + b/FOV)*WIDTH)
            base = round(HEIGHT*.79)
            radius = max(2, round(ob[2]*24/max(.6, dist)))
            yy, xx = np.ogrid[:HEIGHT, :WIDTH]
            mask = (xx-cx)**2 + (yy-base)**2 < radius*radius
            im[mask] = STONE_RGB
    for k, station in enumerate(stations):
        visible, b, dist = in_view(pos, heading, station, obstacles)
        if visible:
            cx = round((.5 + b/FOV)*WIDTH)
            cy = round(HEIGHT*(.51 + .23*(1-dist/RANGE)))
            radius = max(2, round(12/max(1., dist)))
            yy, xx = np.ogrid[:HEIGHT, :WIDTH]
            mask = (xx-cx)**2 + (yy-cy)**2 <= radius*radius
            im[mask] = STATION_RGB[k]
    return im


def interpret_camera(rgb: np.ndarray) -> list[dict]:
    """Inference by reading color-coded camera pixels, not the stations array."""
    result=[]
    for c in STATION_RGB:
        mask = np.all(rgb == c, axis=2)
        ys, xs = np.where(mask)
        if not len(xs):
            result.append({'seen': False, 'pixel_count':0, 'bearing': None, 'confidence':0.0})
            continue
        centre = float(xs.mean())
        bearing = (centre/WIDTH - .5)*FOV
        result.append({'seen':True, 'pixel_count':int(len(xs)),
                       'bearing':round(bearing, 5), 'confidence':round(min(1., len(xs)/40),4)})
    return result


def odor(pos, heading, stations):
    """Two non-reward-bearing simulated station odors, left/right antenna samples."""
    result=[]
    for x,y in stations:
        dx,dy=x-pos[0],y-pos[1]
        d=math.hypot(dx,dy)
        main=math.exp(-d/2.25)
        lateral=(-math.sin(heading)*dx + math.cos(heading)*dy)/max(d,.01)
        result.append((round(main,5),round(main*(1-.12*lateral),5),
                       round(main*(1+.12*lateral),5)))
    return result


def collision(pos, next_pos, obstacles=OBSTACLES, radius=.17):
    xmin,xmax,ymin,ymax=BOUNDS
    if not xmin+radius<next_pos[0]<xmax-radius or not ymin+radius<next_pos[1]<ymax-radius:
        return True
    # Check the whole movement segment in small steps (no tunneling).
    delta=math.dist(pos,next_pos)
    for k in range(max(1,math.ceil(delta/.06))+1):
        t=k/max(1,math.ceil(delta/.06))
        x=pos[0]+t*(next_pos[0]-pos[0]);y=pos[1]+t*(next_pos[1]-pos[1])
        if any(math.hypot(x-ox,y-oy)<r+radius for ox,oy,r in obstacles):
            return True
    return False
