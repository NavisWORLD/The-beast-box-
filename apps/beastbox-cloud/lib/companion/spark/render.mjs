/**
 * 64x64 pixel-art sprite renderer.
 * Faithful port of beastgen/render.py (parts, stage-stable patterns, 5-tone
 * ramp, 4x4 Bayer dither, inner outlines, rim, navy outline, face, contact
 * shadow, sparkles, left-facing mirror). Colours snap to GBA BGR555.
 *
 * Ellipse, polygon, and thick-line masks follow Pillow 12's integer fill
 * (Draw.c): filled ellipses, scanline polygons, Bresenham width-1 strokes,
 * and wide-line quads, plus the endpoint circles render.py adds.
 * An inverted ellipse box is drawn as the absolute ellipse (Pillow 12 raises).
 */
import { PALETTES, Stream } from './genome.mjs';

const W = 64;

const trunc = Math.trunc;

function roundTiesEven(x) {
  const sign = x < 0 ? -1 : 1;
  const ax = Math.abs(x);
  const fl = Math.floor(ax);
  const diff = ax - fl;
  let r;
  if (diff > 0.5) r = fl + 1;
  else if (diff < 0.5) r = fl;
  else r = (fl % 2 === 0) ? fl : fl + 1;
  return sign * r;
}

function roundUp(f) {
  if (f >= 0) return Math.floor(f + 0.5);
  return -Math.floor(Math.abs(f) + 0.5);
}
function roundDown(f) {
  if (f >= 0) return Math.ceil(f - 0.5);
  return -Math.ceil(Math.abs(f) - 0.5);
}
function f32(x) { return Math.fround(x); }

function hline(mask, x0, y, x1, w) {
  if (y < 0 || y >= w) return;
  if (x0 < 0) x0 = 0;
  else if (x0 >= w) return;
  if (x1 < 0) return;
  else if (x1 >= w) x1 = w - 1;
  for (let x = x0; x <= x1; x++) mask[y * w + x] = 1;
}

function quarterInit(a, b) {
  if (a < 0 || b < 0) return { finished: 1 };
  return {
    a, b, cx: a, cy: b % 2, ex: a % 2, ey: b,
    a2: a * a, b2: b * b, a2b2: a * a * b * b, finished: 0,
  };
}
function quarterDelta(s, x, y) {
  return Math.abs(s.a2 * y * y + s.b2 * x * x - s.a2b2);
}
function quarterNext(s) {
  if (s.finished) return null;
  const retx = s.cx, rety = s.cy;
  if (s.cx === s.ex && s.cy === s.ey) s.finished = 1;
  else {
    let nx = s.cx, ny = s.cy + 2;
    let ndelta = quarterDelta(s, nx, ny);
    if (nx > 1) {
      let nd = quarterDelta(s, s.cx - 2, s.cy + 2);
      if (ndelta > nd) { nx = s.cx - 2; ny = s.cy + 2; ndelta = nd; }
      nd = quarterDelta(s, s.cx - 2, s.cy);
      if (ndelta > nd) { nx = s.cx - 2; ny = s.cy; }
    }
    s.cx = nx; s.cy = ny;
  }
  return [retx, rety];
}

function ellipseInit(a, b, width) {
  const s = { stO: quarterInit(a, b), leftmost: a % 2, buf: [], finished: 0, pl: 0, pr: 0, py: 0 };
  const first = quarterNext(s.stO);
  if (width < 1 || !first) s.finished = 1;
  else {
    s.pr = first[0]; s.py = first[1];
    s.stI = quarterInit(a - 2 * (width - 1), b - 2 * (width - 1));
    s.pl = s.leftmost;
  }
  return s;
}

function ellipseNext(s) {
  if (s.buf.length === 0) {
    if (s.finished) return null;
    const y = s.py;
    let l = s.pl;
    const r = s.pr;
    let nx = quarterNext(s.stO);
    while (nx && nx[1] <= y) nx = quarterNext(s.stO);
    if (!nx) s.finished = 1;
    else { s.pr = nx[0]; s.py = nx[1]; }
    nx = quarterNext(s.stI);
    while (nx && nx[1] <= y) { l = nx[0]; nx = quarterNext(s.stI); }
    s.pl = !nx ? s.leftmost : nx[0];
    if ((l > 0 || l < r) && y > 0) s.buf.push([l === 0 ? 2 : l, y, r]);
    if (y > 0) s.buf.push([-r, y, -l]);
    if (l > 0 || l < r) s.buf.push([l === 0 ? 2 : l, -y, r]);
    s.buf.push([-r, -y, -l]);
    s.buf.reverse();
  }
  return s.buf.pop();
}

function fillEllipse(mask, x0, y0, x1, y1, w = W) {
  x0 = trunc(x0); y0 = trunc(y0); x1 = trunc(x1); y1 = trunc(y1);
  if (x1 < x0) { const t = x0; x0 = x1; x1 = t; }
  if (y1 < y0) { const t = y0; y0 = y1; y1 = t; }
  const a = x1 - x0, b = y1 - y0;
  const st = ellipseInit(a, b, a + b);
  for (;;) {
    const seg = ellipseNext(st);
    if (!seg) break;
    const [X0, Y, X1] = seg;
    hline(mask, x0 + trunc((X0 + a) / 2), y0 + trunc((Y + b) / 2), x0 + trunc((X1 + a) / 2), w);
  }
}

function addEdge(x0, y0, x1, y1) {
  const e = { x0, y0, xmin: Math.min(x0, x1), xmax: Math.max(x0, x1), ymin: Math.min(y0, y1), ymax: Math.max(y0, y1) };
  if (y0 === y1) { e.dx = 0; e.d = 0; }
  else {
    e.dx = f32(f32(x1 - x0) / (y1 - y0));
    e.d = y0 === e.ymin ? 1 : -1;
  }
  return e;
}

function edgeX(e, y) {
  // C float: (int_diff * float_dx) rounds, then + x0 rounds again.
  const diff = y - e.y0;
  return f32(f32(f32(diff) * e.dx) + e.x0);
}

function polygonGeneric(mask, edges, w) {
  const n = edges.length;
  if (n <= 0) return;
  let ymin = w - 1, ymax = 0;
  const table = [];
  for (const e of edges) {
    if (e.ymin < ymin) ymin = e.ymin;
    if (e.ymax > ymax) ymax = e.ymax;
    if (e.ymin === e.ymax) {
      hline(mask, e.xmin, e.ymin, e.xmax, w);
      continue;
    }
    table.push(e);
  }
  if (ymin < 0) ymin = 0;
  if (ymax > w) ymax = w;
  const edgeCount = table.length;
  for (let y = ymin; y <= ymax; y++) {
    const xx = [];
    for (let i = 0; i < edgeCount; i++) {
      const current = table[i];
      if (y >= current.ymin && y <= current.ymax) {
        xx.push(edgeX(current, y));
        const j = xx.length - 1;
        if (y === current.ymax && y < ymax) {
          xx.push(xx[j]);
        } else if ((y === current.ymin || y === current.ymax) && current.dx !== 0) {
          for (let k = 0; k < i; k++) {
            const other = table[k];
            if ((y !== other.ymin && y !== other.ymax) || other.dx === 0) continue;
            if (roundTiesEven(xx[j]) === roundTiesEven(edgeX(other, y))) {
              const offset = y === current.ymax ? -1 : 1;
              const adjacent = edgeX(current, y + offset);
              if (y + offset >= other.ymin && y + offset <= other.ymax) {
                const adjacentOther = edgeX(other, y + offset);
                if (xx[j] > adjacent + 1 && xx[j] > adjacentOther + 1) {
                  xx[j] = f32(roundTiesEven(Math.max(adjacent, adjacentOther)) + 1);
                } else if (xx[j] < adjacent - 1 && xx[j] < adjacentOther - 1) {
                  xx[j] = f32(roundTiesEven(Math.min(adjacent, adjacentOther)) - 1);
                }
                break;
              }
            }
          }
        }
      }
    }
    xx.sort((a, b) => a - b);
    for (let i = 1; i < xx.length; i += 2) {
      hline(mask, roundUp(xx[i - 1]), y, roundDown(xx[i]), w);
    }
  }
}

function fillPolygon(mask, pts, w = W) {
  const xy = [];
  for (const p of pts) { xy.push(trunc(p[0]), trunc(p[1])); }
  const count = pts.length;
  if (count < 2) return;
  const edges = [];
  let i = 0;
  for (; i < count - 1; i++) {
    const x0 = xy[i * 2], y0 = xy[i * 2 + 1], x1 = xy[i * 2 + 2], y1 = xy[i * 2 + 3];
    if (y0 === y1 && i !== 0 && y0 === xy[i * 2 - 1]) {
      const last = edges[edges.length - 1];
      if (x1 > x0 && x0 > xy[i * 2 - 2]) { last.xmax = x1; continue; }
      if (x1 < x0 && x0 < xy[i * 2 - 2]) { last.xmin = x1; continue; }
    }
    edges.push(addEdge(x0, y0, x1, y1));
  }
  if (xy[i * 2] !== xy[0] || xy[i * 2 + 1] !== xy[1]) {
    edges.push(addEdge(xy[i * 2], xy[i * 2 + 1], xy[0], xy[1]));
  }
  polygonGeneric(mask, edges, w);
}

function bresenham(mask, x0, y0, x1, y1, w) {
  let dx = x1 - x0, dy = y1 - y0;
  let xs = 1, ys = 1;
  if (dx < 0) { dx = -dx; xs = -1; }
  if (dy < 0) { dy = -dy; ys = -1; }
  const plot = (x, y) => { if (x >= 0 && x < w && y >= 0 && y < w) mask[y * w + x] = 1; };
  if (dx === 0) {
    for (let i = 0; i < dy; i++) { plot(x0, y0); y0 += ys; }
  } else if (dy === 0) {
    for (let i = 0; i < dx; i++) { plot(x0, y0); x0 += xs; }
  } else if (dx > dy) {
    const n = dx;
    dy += dy;
    let e = dy - dx;
    dx += dx;
    for (let i = 0; i < n; i++) {
      plot(x0, y0);
      if (e >= 0) { y0 += ys; e -= dx; }
      e += dy;
      x0 += xs;
    }
  } else {
    const n = dy;
    dx += dx;
    let e = dx - dy;
    dy += dy;
    for (let i = 0; i < n; i++) {
      plot(x0, y0);
      if (e >= 0) { x0 += xs; e -= dy; }
      e += dx;
      y0 += ys;
    }
  }
}

function wideLine(mask, x0, y0, x1, y1, width, w) {
  const dx = x1 - x0, dy = y1 - y0;
  if (dx === 0 && dy === 0) {
    if (x0 >= 0 && x0 < w && y0 >= 0 && y0 < w) mask[y0 * w + x0] = 1;
    return;
  }
  const big = Math.hypot(dx, dy);
  const small = (width - 1) / 2;
  const ratioMax = roundUp(small) / big;
  const ratioMin = roundDown(small) / big;
  const dxmin = roundDown(ratioMin * dy);
  const dxmax = roundDown(ratioMax * dy);
  const dymin = roundDown(ratioMin * dx);
  const dymax = roundDown(ratioMax * dx);
  const v = [
    [x0 - dxmin, y0 + dymax],
    [x1 - dxmin, y1 + dymax],
    [x1 + dxmax, y1 - dymin],
    [x0 + dxmax, y0 - dymin],
  ];
  const edges = [];
  for (let i = 0; i < 4; i++) {
    const a = v[i], b = v[(i + 1) % 4];
    edges.push(addEdge(a[0], a[1], b[0], b[1]));
  }
  polygonGeneric(mask, edges, w);
}

function pyRound(x) {
  const sign = x < 0 ? -1 : 1;
  const ax = Math.abs(x);
  const fl = Math.floor(ax);
  const diff = ax - fl;
  let r;
  if (diff > 0.5) r = fl + 1;
  else if (diff < 0.5) r = fl;
  else r = (fl % 2 === 0) ? fl : fl + 1;
  return sign * r;
}

/** render.py Canvas.line: stroke plus a circle of radius w/2 at each vertex. */
function fillLine(mask, pts, width, w = W) {
  const iw = Math.max(1, trunc(pyRound(width)));
  const n = pts.length;
  if (iw === 1) {
    let last = null;
    for (let i = 0; i < n - 1; i++) {
      const x0 = trunc(pts[i][0]), y0 = trunc(pts[i][1]);
      const x1 = trunc(pts[i + 1][0]), y1 = trunc(pts[i + 1][1]);
      bresenham(mask, x0, y0, x1, y1, w);
      last = [x1, y1];
    }
    if (last && last[0] >= 0 && last[0] < w && last[1] >= 0 && last[1] < w) mask[last[1] * w + last[0]] = 1;
  } else {
    for (let i = 0; i < n - 1; i++) {
      wideLine(mask, trunc(pts[i][0]), trunc(pts[i][1]), trunc(pts[i + 1][0]), trunc(pts[i + 1][1]), iw, w);
    }
  }
  const rr = width / 2;
  for (const [x, y] of pts) fillEllipse(mask, x - rr, y - rr, x + rr, y + rr, w);
}

function blank(w = W) { return new Uint8Array(w * w); }

const CX = 31.5;
const G = 61;
const BASE = 1, ALT = 2, BELLY = 3, ACCENT = 4, DARK = 5, GLOW = 6, CHEEK = 7;
const EYE = 8, IRIS = 9, WHITE = 10, NOSE = 11, BEAK = 12;
const STAGE_K = { 1: 0.60, 2: 0.80, 3: 1.0 };
const NAVY = [14, 20, 44];
const DEEP = 0, SHADOW = 1, MID = 2, LIGHT = 3, HI = 4, LINE = 5;
const GLOW_HSV = { gold: [46, 0.85, 1], cyan: [184, 0.80, 1] };
const FRONT_EARS = new Set(["crown", "leaf"]);
const PI = Math.PI;

function pyMod(a, b) { return ((a % b) + b) % b; }
function yn(flag) { return flag ? 1 : 0; }
// Numpy compares float32 light to a Python float by casting the threshold to float32.
function f32gt(a, b) { return Math.fround(a) > Math.fround(b); }
function f32lt(a, b) { return Math.fround(a) < Math.fround(b); }

function hsv(h, s, v) {
  const hh = pyMod(h, 360) / 360;
  s = Math.max(0, Math.min(1, s));
  v = Math.max(0, Math.min(1, v));
  let r, g, b;
  if (s === 0) r = g = b = v;
  else {
    let i = trunc(hh * 6);
    const f = hh * 6 - i;
    const p = v * (1 - s);
    const q = v * (1 - s * f);
    const t = v * (1 - s * (1 - f));
    i = pyMod(i, 6);
    if (i === 0) { r = v; g = t; b = p; }
    else if (i === 1) { r = q; g = v; b = p; }
    else if (i === 2) { r = p; g = v; b = t; }
    else if (i === 3) { r = p; g = q; b = v; }
    else if (i === 4) { r = t; g = p; b = v; }
    else { r = v; g = p; b = q; }
  }
  return [trunc(r * 255), trunc(g * 255), trunc(b * 255)];
}

function snap(rgb) {
  return rgb.map((c) => Math.min(248, pyRound(c / 255 * 31) * 8));
}

function mixInt(a, b, wa, wb) {
  return a.map((v, i) => trunc(wa * v + wb * b[i]));
}

function ramp(h, s, v) {
  const cool = (60 < pyMod(h, 360) && pyMod(h, 360) < 240) ? 12 : -14;
  const warm = -((60 < pyMod(h, 360) && pyMod(h, 360) < 240) ? 8 : -6);
  const deep = mixInt(hsv(h + 1.8 * cool, s * 1.1 + 0.16, v * 0.46), NAVY, 0.8, 0.2);
  const sh = hsv(h + cool, s * 1.05 + 0.08, v * 0.68);
  const mid = hsv(h, s, v);
  const li = hsv(h + warm, s * 0.80, Math.min(1, v * 1.16 + 0.05));
  const hi = hsv(h + 1.6 * warm, s * 0.45, Math.min(1, v * 1.32 + 0.16));
  const ln = mixInt(hsv(h + 15, s * 1.1 + 0.15, v * 0.34), NAVY, 0.45, 0.55);
  return [snap(deep), snap(sh), snap(mid), snap(li), snap(hi), snap(ln)];
}

function palette(gen) {
  const p = PALETTES[gen.island];
  const gg = gen.genes;
  const dh = (gg.hue - 0.5) * 30;
  const ds = (gg.sat - 0.5) * 0.25;
  const dv = (gg.val - 0.5) * 0.18;
  const adj = (t) => [t[0] + dh, t[1] + ds, t[2] + dv];
  const glow = gen.glow === "native" ? p.glow : GLOW_HSV[gen.glow];
  const pal = {
    [BASE]: ramp(...adj(p.base)),
    [ALT]: ramp(...adj(p.alt)),
    [BELLY]: ramp(...adj(p.belly)),
    [ACCENT]: ramp(...adj(p.accent)),
    [GLOW]: ramp(glow[0], glow[1] * 0.85, glow[2]),
    [CHEEK]: ramp(350, 0.45, 1),
    [DARK]: ramp(p.base[0] + 20, 0.5, 0.32),
    [NOSE]: ramp(240, 0.3, 0.2),
    [BEAK]: ramp(40, 0.72, 0.97),
    [WHITE]: ramp(220, 0.04, 0.97),
  };
  const gl = hsv(...glow);
  pal[GLOW] = [
    snap(hsv(glow[0], glow[1], 0.7)),
    snap(hsv(glow[0], glow[1], 0.85)),
    snap(gl),
    snap(hsv(glow[0], glow[1] * 0.35, 1)),
    [248, 248, 248],
    snap(hsv(glow[0], glow[1], 0.45)),
  ];
  pal.outline = snap(mixInt(pal[BASE][LINE], NAVY, 0.5, 0.5));
  const rim = gen.glow !== "gold" ? GLOW_HSV.cyan : GLOW_HSV.gold;
  pal.rim = hsv(rim[0], rim[1] * 0.7, 1);
  pal.iris = (gen.glow === "native" && gen.island === "Cinder Drift")
    ? snap(hsv(40, 0.9, 1))
    : snap(gl);
  return pal;
}

function any(m) {
  for (let i = 0; i < m.length; i++) if (m[i]) return true;
  return false;
}
function maskAnd(a, b) {
  const o = blank();
  for (let i = 0; i < o.length; i++) if (a[i] && b[i]) o[i] = 1;
  return o;
}
function maskOr(a, b) {
  const o = blank();
  for (let i = 0; i < o.length; i++) if (a[i] || b[i]) o[i] = 1;
  return o;
}
function maskAndNot(a, b) {
  const o = blank();
  for (let i = 0; i < o.length; i++) if (a[i] && !b[i]) o[i] = 1;
  return o;
}
function maskWhere(a, pred) {
  const o = blank();
  for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x;
    if (a[i] && pred(x, y, i)) o[i] = 1;
  }
  return o;
}
function rollY(mask) {
  const o = blank();
  for (let y = 0; y < W; y++) {
    const src = (y - 1 + W) % W;
    o.set(mask.subarray(src * W, src * W + W), y * W);
  }
  return o;
}

function linspace(start, stop, num) {
  if (num <= 0) return [];
  if (num === 1) return [start];
  const step = (stop - start) / (num - 1);
  const out = new Array(num);
  for (let i = 0; i < num; i++) out[i] = i * step + start;
  out[num - 1] = stop;
  return out;
}
function arange(start, stop, step) {
  // numpy.arange: length = ceil((stop-start)/step), then
  // y[0]=start, y[1]=start+step, y[i]=y[0]+i*(y[1]-y[0]).
  if (!(step > 0)) return [];
  const n = Math.ceil((stop - start) / step);
  if (!Number.isFinite(n) || n <= 0) return [];
  const out = new Array(n);
  out[0] = start;
  if (n === 1) return out;
  out[1] = start + step;
  const delta = out[1] - out[0];
  for (let i = 2; i < n; i++) out[i] = out[0] + i * delta;
  return out;
}
function bezier(ctrl, n) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    let q = ctrl.map((p) => [p[0], p[1]]);
    while (q.length > 1) {
      const nxt = [];
      for (let j = 0; j < q.length - 1; j++) {
        nxt.push([
          (1 - t) * q[j][0] + t * q[j + 1][0],
          (1 - t) * q[j][1] + t * q[j + 1][1],
        ]);
      }
      q = nxt;
    }
    pts.push(q[0]);
  }
  return pts;
}
function flamePts(x, y, w, h, lean = 0, tongues = 3) {
  const pts = [[x - w / 2, y]];
  for (let i = 0; i < tongues; i++) {
    const t0 = (i + 0.5) / tongues;
    const tx = x - w / 2 + w * t0 + lean * h * 0.35;
    const th = h * (0.6 + 0.4 * Math.sin(PI * t0));
    pts.push([x - w / 2 + w * (i / tongues) + (w / tongues) * 0.15, y - th * 0.45]);
    pts.push([tx, y - th]);
  }
  pts.push([x + w / 2, y], [x, y + w * 0.25]);
  return pts;
}

class Canvas {
  constructor() {
    this.mat = new Int16Array(W * W);
    this.part = new Int16Array(W * W);
    this.light = new Float32Array(W * W);
    this.flat = new Uint8Array(W * W);
    this.layer = new Int8Array(W * W);
    this.n = 0;
    this.overlay = [];
    this.cur = "main";
    this.skipMain = false;
    this.bias = 0;
    this.chainDy = new Float32Array(W * W);
    this.floatH = 0;
  }
  ell(cx, cy, rx, ry) {
    const m = blank();
    fillEllipse(m, cx - rx, cy - ry, cx + rx, cy + ry);
    return m;
  }
  poly(pts) {
    const m = blank();
    fillPolygon(m, pts);
    return m;
  }
  line(pts, w) {
    const m = blank();
    fillLine(m, pts, w);
    return m;
  }
  chain(ptsR) {
    const m = blank();
    const best = new Float32Array(W * W);
    best.fill(1e9);
    const light = new Float32Array(W * W);
    this.chainDy = new Float32Array(W * W);
    for (const [cx, cy, r0] of ptsR) {
      const c = this.ell(cx, cy, r0, r0);
      const rr = Math.max(r0, 1);
      const rr2 = rr * rr;
      for (let i = 0; i < W * W; i++) {
        if (!c[i]) continue;
        m[i] = 1;
        const x = i % W;
        const y = (i / W) | 0;
        const d = ((x - cx) ** 2 + (y - cy) ** 2) / rr2;
        if (d < best[i]) {
          const dx = (x - cx) / rr;
          const dy = (y - cy) / rr;
          light[i] = -(0.55 * dx + 0.85 * dy) - 0.25 * (dx * dx + dy * dy);
          this.chainDy[i] = dy;
          best[i] = d;
        }
      }
    }
    return [m, light];
  }
  add(m, material, opt = {}) {
    if (!any(m) || (this.skipMain && this.cur === "main")) return m;
    const lay = this.cur === "back" ? 1 : 2;
    this.n += 1;
    const id = this.n;
    let centre = opt.centre ?? null;
    let r = opt.r ?? null;
    const flat = opt.flat ? 1 : 0;
    const light = opt.light ?? null;
    const outline = opt.outline !== false;
    const extra = (opt.bias ?? 0) + this.bias;
    if (light == null && centre == null) {
      let n = 0, sx = 0, sy = 0;
      let minx = 1e9, maxx = -1e9, miny = 1e9, maxy = -1e9;
      for (let i = 0; i < W * W; i++) if (m[i]) {
        const x = i % W, y = (i / W) | 0;
        n++; sx += x; sy += y;
        if (x < minx) minx = x;
        if (x > maxx) maxx = x;
        if (y < miny) miny = y;
        if (y > maxy) maxy = y;
      }
      centre = [sx / n, sy / n];
      r = Math.max(2, 0.5 * Math.max(maxx - minx + 1, maxy - miny + 1));
    }
    for (let i = 0; i < W * W; i++) if (m[i]) {
      this.layer[i] = lay;
      this.mat[i] = material;
      if (outline || this.part[i] === 0) this.part[i] = id;
      let L;
      if (light == null) {
        const x = i % W, y = (i / W) | 0;
        const dx = (x - centre[0]) / r;
        const dy = (y - centre[1]) / r;
        L = -(0.55 * dx + 0.85 * dy) - 0.25 * (dx * dx + dy * dy);
      } else if (typeof light === "number") L = light;
      else L = light[i];
      this.light[i] = L + extra;
      this.flat[i] = flat;
    }
    return m;
  }
  paint(mask, material) {
    for (let i = 0; i < W * W; i++) if (mask[i]) this.mat[i] = material;
  }
  setFlat(mask, v) {
    for (let i = 0; i < W * W; i++) if (mask[i]) this.flat[i] = v ? 1 : 0;
  }
  setLight(mask, v) {
    for (let i = 0; i < W * W; i++) if (mask[i]) this.light[i] = v;
  }
  bumpLight(mask, delta) {
    for (let i = 0; i < W * W; i++) if (mask[i]) this.light[i] = this.light[i] + delta;
  }
}

function leaf(cv, x, y, length, ang, width, mat = ACCENT) {
  const ca = Math.cos(ang), sa = Math.sin(ang);
  const pts = [];
  for (let i = 0; i < 13; i++) {
    const t = i / 12;
    const ww = width * Math.sin(PI * t);
    pts.push([x + ca * length * t - sa * ww, y + sa * length * t + ca * ww]);
  }
  for (let i = 12; i >= 0; i--) {
    const t = i / 12;
    const ww = width * Math.sin(PI * t) * 0.9;
    pts.push([x + ca * length * t + sa * ww, y + sa * length * t - ca * ww]);
  }
  const m = cv.poly(pts);
  cv.add(m, mat);
  const vein = maskAnd(cv.line([[x, y], [x + ca * length * 0.8, y + sa * length * 0.8]], 1), m);
  cv.bumpLight(vein, -0.8);
}

function crystal(cv, x, y, h, w, ang, mat = ACCENT) {
  const ca = Math.cos(ang), sa = Math.sin(ang);
  const tip = [x + ca * h, y + sa * h];
  const l = [x - sa * w, y + ca * w];
  const r = [x + sa * w, y - ca * w];
  const m = cv.poly([l, tip, r]);
  cv.add(m, mat);
  cv.bumpLight(maskAnd(cv.poly([[x, y], tip, r]), m), 0.7);
  return m;
}

function ears(cv, gen, hx, hy, hr, k, stage, layer = "back") {
  const kind = gen.ears;
  const size = gen.genes.ear_size;
  if ((FRONT_EARS.has(kind)) !== (layer === "front")) return;
  const eh = (4 + 6 * size) * k * (stage === 1 ? 0.8 : 1.0 + 0.15 * yn(stage === 3));
  for (const side of [-1, 1]) {
    const bx = hx + side * hr * 0.55;
    const by = hy - hr * 0.62;
    if (kind === "pointy") {
      cv.add(cv.poly([
        [bx - side * eh * 0.45, by + 2],
        [bx + side * eh * 0.25, by - eh],
        [bx + side * eh * 0.55, by + 1.5],
      ]), BASE);
      cv.add(cv.poly([
        [bx - side * eh * 0.15, by + 1],
        [bx + side * eh * 0.22, by - eh * 0.6],
        [bx + side * eh * 0.35, by + 1],
      ]), stage < 3 ? CHEEK : DARK, { outline: false });
    } else if (kind === "round") {
      const r = eh * 0.45;
      cv.add(cv.ell(bx + side * 1, by - r * 0.5, r, r), BASE);
      cv.add(cv.ell(bx + side * 1, by - r * 0.4, r * 0.5, r * 0.5), CHEEK, { outline: false });
    } else if (kind === "crystal") {
      crystal(cv, bx, by + 1, eh * 1.2, Math.max(1.6, eh * 0.28), -PI / 2 + side * 0.45);
      if (stage >= 2) crystal(cv, bx - side * 2.5, by - 0.5, eh * 0.8, Math.max(1.3, eh * 0.2), -PI / 2 + side * 0.15);
    } else if (kind === "flame") {
      cv.add(cv.poly(flamePts(bx + side * 1, by + 1, eh * 0.9, eh * 1.3, side * 0.6, 2)), GLOW, { flat: true });
      cv.add(cv.poly([
        [bx - side * eh * 0.3, by + 2],
        [bx + side * eh * 0.2, by - eh * 0.7],
        [bx + side * eh * 0.5, by + 1.5],
      ]), BASE);
    } else if (kind === "horns" || kind === "crown") {
      if (kind === "crown" && side === 1) {
        const n = stage < 3 ? 3 : 5;
        const cw = hr * 0.9;
        const pts = [[hx - cw, hy - hr * 0.78]];
        for (let i = 0; i < n; i++) {
          const t = (i + 0.5) / n;
          pts.push([hx - cw + 2 * cw * t, hy - hr * 0.78 - eh * (i === (n / 2 | 0) ? 0.9 : 0.6)]);
          pts.push([hx - cw + 2 * cw * (i + 1) / n, hy - hr * 0.78]);
        }
        pts.push([hx + cw * 0.8, hy - hr * 0.6], [hx - cw * 0.8, hy - hr * 0.6]);
        cv.add(cv.poly(pts), GLOW);
        cv.overlay.push([trunc(hx), trunc(hy - hr * 0.78 - eh * 0.5), "glow_hi"]);
      } else if (kind === "horns") {
        const pts = linspace(0, 1, 6).map((t) => [
          bx + side * t * eh * 0.7 + side * Math.sin(t * 2.2) * eh * 0.15,
          by - t * eh * 1.1,
        ]);
        cv.add(cv.line(pts, Math.max(1.5, 2.6 * k * (1.2 - 0.6 * 0))), ACCENT);
      }
    } else if (kind === "leaf") {
      if (side === 1) {
        leaf(cv, hx, hy - hr * 0.85, eh * 1.4, -PI / 2 - 0.7, eh * 0.4);
        leaf(cv, hx, hy - hr * 0.85, eh * 1.2, -PI / 2 + 0.75, eh * 0.35);
        cv.add(cv.line([[hx, hy - hr * 0.7], [hx, hy - hr * 0.95]], 1), ALT);
      }
    } else if (kind === "antlers") {
      cv.add(cv.line([
        [bx, by + 1],
        [bx + side * eh * 0.3, by - eh * 0.5],
        [bx + side * eh * 0.4, by - eh * 1.2],
      ], Math.max(1.2, 1.8 * k)), ALT);
      cv.add(cv.line([
        [bx + side * eh * 0.3, by - eh * 0.5],
        [bx + side * eh * 0.9, by - eh * 0.9],
      ], Math.max(1, 1.4 * k)), ALT);
      if (stage >= 2) leaf(cv, bx + side * eh * 0.4, by - eh * 1.2, eh * 0.7, -PI / 2 + side * 0.9, eh * 0.25);
      if (stage === 3) {
        cv.add(cv.line([
          [bx + side * eh * 0.36, by - eh * 0.9],
          [bx - side * eh * 0.1, by - eh * 1.4],
        ], 1.2), ALT);
      }
    } else if (kind === "antenna" || kind === "feelers") {
      const tip = [bx + side * eh * 0.6, by - eh * 1.3];
      const mid = [bx + side * eh * 0.1, by - eh * 0.8];
      cv.add(cv.line([[bx, by + 1], mid, tip], 1), kind === "antenna" ? DARK : ACCENT);
      if (kind === "antenna") {
        cv.add(cv.ell(tip[0], tip[1], 1.6 * Math.max(k, 0.8), 1.6 * Math.max(k, 0.8)), GLOW, { flat: true });
      } else {
        for (const t of [0.45, 0.65, 0.85]) {
          const px = mid[0] + (tip[0] - mid[0]) * t;
          const py = mid[1] + (tip[1] - mid[1]) * t;
          cv.add(cv.line([[px, py], [px + side * 1.5 * k + side, py + 1.5]], 1), ACCENT);
        }
        cv.add(cv.ell(tip[0], tip[1], 1.2, 1.2), GLOW, { flat: true });
      }
    } else if (kind === "bolts") {
      cv.add(cv.ell(bx, by + 1, eh * 0.35, eh * 0.35), ALT);
      cv.add(cv.line([[bx, by], [bx + side * eh * 0.3, by - eh * 0.9]], 1), DARK);
      cv.add(cv.ell(bx + side * eh * 0.3, by - eh * 0.9, 1.3, 1.3), GLOW, { flat: true });
    } else if (kind === "gills") {
      for (let j = 0; j < 3; j++) {
        const a = [-0.55, -0.05, 0.45][j];
        const ang = side < 0 ? PI + a : -a;
        const x0 = hx + side * hr * 1.05;
        const y0 = hy - hr * 0.1;
        const ln = eh * (1.0 - 0.15 * Math.abs(j - 1));
        const ex = x0 + Math.cos(ang) * ln;
        const ey = y0 + Math.sin(ang) * ln * 0.9 - 1;
        cv.add(cv.line([[x0, y0], [ex, ey]], Math.max(1.6, 2.2 * k)), ACCENT);
        for (const t of [0.35, 0.7]) {
          const fx = x0 + (ex - x0) * t;
          const fy = y0 + (ey - y0) * t;
          cv.add(cv.line([[fx, fy], [fx + side * 1.0, fy - 1.6]], 1), ACCENT, { outline: false });
        }
      }
    }
  }
}

function _tail(cv, gen, x, y, k, stage, side = 1) {
  const kind = gen.tail;
  const size = gen.genes.tail_size;
  const L = (8 + 7 * size) * k * (stage === 1 ? 0.7 : 1.0 + 0.2 * yn(stage === 3));
  if (kind === "none" || kind === "fishtail" || kind === "tip") return;
  if (kind === "spade") {
    const pts = linspace(0, 1, 9).map((t) => [
      x + side * L * 0.55 * t,
      y - L * 0.75 * Math.sin(t * 2.0) + L * 0.15 * t,
      (1.9 - 0.9 * t) * k + 0.6,
    ]);
    const [m, l] = cv.chain(pts);
    cv.add(m, BASE, { light: l });
    const ex = pts[pts.length - 1][0], ey = pts[pts.length - 1][1];
    const s2 = (2.6 + 2.2 * (stage - 1)) * k + 1;
    cv.add(cv.poly([
      [ex - side * s2 * 0.2, ey + s2 * 0.4],
      [ex + side * s2 * 0.9, ey - s2 * 0.9],
      [ex + side * s2 * 1.3, ey + s2 * 0.5],
      [ex + side * s2 * 0.4, ey + s2 * 0.9],
    ]), ACCENT);
    return;
  }
  if (kind === "fluffy" || kind === "plume") {
    const pts = [];
    for (let i = 0; i < 7; i++) {
      const t = i / 6;
      const ang = -0.2 - 1.9 * t;
      pts.push([
        x + side * (Math.cos(ang) * L * 0.55 + L * 0.25 * t),
        y + Math.sin(ang) * L * 0.9,
        (1.6 + 3.2 * Math.sin(PI * (0.2 + 0.7 * t))) * k * (kind === "plume" ? 1.25 : 1.05),
      ]);
    }
    const [m, l] = cv.chain(pts);
    cv.add(m, BASE, { light: l });
    const last = pts[pts.length - 1];
    const prev = pts[pts.length - 2];
    const [tip, l2] = cv.chain([[last[0], last[1], last[2] * 0.9], [prev[0], prev[1], prev[2] * 0.5]]);
    cv.add(maskAnd(tip, m), kind === "fluffy" ? BELLY : GLOW, { light: l2 });
  } else if (kind === "leaf") {
    cv.add(cv.line([[x, y], [x + side * L * 0.4, y - L * 0.3]], Math.max(1.2, 1.6 * k)), ALT);
    leaf(cv, x + side * L * 0.3, y - L * 0.2, L * 0.9, -PI / 2 + side * 0.55, L * 0.28);
  } else if (kind === "flame") {
    const pts = [0, 0.33, 0.66].map((t) => [
      x + side * L * 0.15 * t * 3,
      y - L * 0.25 * t * 3,
      (2.4 - t) * k * 1.4,
    ]);
    const [m, l] = cv.chain(pts);
    cv.add(m, BASE, { light: l });
    const fx = x + side * L * 0.5, fy = y - L * 0.55;
    cv.add(cv.poly(flamePts(fx, fy + L * 0.3, L * 0.7, L * 1.0, side * 0.8, 3)), GLOW, { flat: true });
    cv.add(cv.poly(flamePts(fx, fy + L * 0.3, L * 0.35, L * 0.55, side * 0.8, 2)), WHITE, { flat: true, outline: false });
  } else if (kind === "crystal" || kind === "fin") {
    const pts = linspace(0, 1, 5).map((t) => [
      x + side * L * 0.35 * t,
      y - L * 0.15 * t + L * 0.1 * Math.sin(t * 3),
      (2.6 - 1.2 * t) * k * 1.3,
    ]);
    const [m, l] = cv.chain(pts);
    cv.add(m, BASE, { light: l });
    const ex = pts[pts.length - 1][0], ey = pts[pts.length - 1][1];
    if (kind === "fin") {
      cv.add(cv.poly([
        [ex - side * 2, ey - 1],
        [ex + side * L * 0.55, ey - L * 0.55],
        [ex + side * L * 0.45, ey + L * 0.25],
        [ex - side * 1, ey + 2],
      ]), ACCENT);
    } else {
      crystal(cv, ex, ey, L * 0.7, Math.max(1.5, L * 0.18), -PI / 2 + side * 0.6);
      crystal(cv, ex - side * 1.5, ey, L * 0.45, Math.max(1.2, L * 0.12), -PI / 2 + side * 1.2);
    }
  } else if (kind === "cable" || kind === "gear") {
    const pts = linspace(0, 1, 8).map((t) => [
      x + side * L * 0.5 * t,
      y - L * 0.6 * Math.sin(t * 2.0),
      1.2 * k + 0.6,
    ]);
    const [m, l] = cv.chain(pts);
    cv.add(m, ALT, { light: l });
    const ex = pts[pts.length - 1][0], ey = pts[pts.length - 1][1];
    if (kind === "gear") {
      const gr = 2.5 * k + 1.5;
      const angs = linspace(0, 2 * PI, 17).slice(0, -1);
      const teeth = angs.map((a, i) => {
        const s = i % 2 === 0 ? 1.35 : 1.0;
        return [ex + Math.cos(a) * gr * s, ey + Math.sin(a) * gr * s];
      });
      cv.add(cv.poly(teeth), ALT);
      cv.add(cv.ell(ex, ey, gr * 0.4, gr * 0.4), GLOW, { flat: true, outline: false });
    } else {
      cv.add(cv.ell(ex, ey, 1.6 * k + 0.8, 1.6 * k + 0.8), GLOW, { flat: true });
    }
  }
}

function featherWing(cv, x, y, sw, side, tilt, stage, k) {
  const a0 = -PI / 2 + side * (0.95 - tilt);
  const la = sw * 0.52;
  const wx = x + Math.cos(a0) * la, wy = y + Math.sin(a0) * la;
  const nP = 3 + yn(stage >= 2) + yn(stage === 3);
  const fw = Math.max(1.6, 1.25 * k + 0.9);
  for (let j = 0; j < nP; j++) {
    const ang = a0 - side * 0.15 + side * 1.25 * j / Math.max(1, nP - 1);
    leaf(cv, wx, wy, sw * (0.78 - 0.08 * j), ang, fw, ALT);
  }
  const secs = [0.35, 0.62, 0.88].slice(0, 2 + yn(stage >= 2));
  secs.forEach((t) => {
    const sx = x + (wx - x) * t, sy = y + (wy - y) * t;
    leaf(cv, sx, sy, sw * (0.42 + 0.1 * t), a0 + side * 1.75, fw * 0.95, BASE);
  });
  const cov = linspace(0.05, 1.0, 5).map((t) => [
    x + (wx - x) * t,
    y + (wy - y) * t + 0.6,
    (1.3 + 1.1 * (1 - t)) * k + 0.7,
  ]);
  const [m, l] = cv.chain(cov);
  cv.add(m, BELLY, { light: l });
}

function batWing(cv, x, y, sw, side, tilt, stage, k) {
  const a0 = -PI / 2 + side * (0.75 - tilt);
  const wx = x + Math.cos(a0) * sw * 0.5, wy = y + Math.sin(a0) * sw * 0.5;
  const nf = stage === 1 ? 2 : 3;
  const tips = [];
  for (let j = 0; j < nf; j++) {
    const ang = a0 - side * 0.25 + side * (nf === 3 ? 1.45 : 1.1) * j / Math.max(1, nf - 1);
    const ln = sw * (0.62 + 0.18 * yn(j === 1) - 0.06 * j);
    tips.push([wx + Math.cos(ang) * ln, wy + Math.sin(ang) * ln]);
  }
  const base = [x + side * sw * 0.08, y + sw * 0.32];
  const poly = [[x, y], [wx, wy], tips[0]];
  const seq = tips.concat([base]);
  for (let i = 0; i < tips.length; i++) {
    const a = seq[i], b = seq[i + 1];
    const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
    poly.push([mx + (wx - mx) * 0.28, my + (wy - my) * 0.28], b);
  }
  const mem = cv.poly(poly);
  cv.add(mem, ACCENT, { centre: [wx, wy], r: sw * 0.9, bias: 0.25 });
  for (const [tx, ty] of tips) {
    cv.add(maskAnd(cv.line([[wx, wy], [tx, ty]], 1), mem), ALT, { outline: false, bias: -0.2 });
  }
  cv.add(cv.line([[x, y], [wx, wy]], Math.max(1.6, 1.8 * k + 0.6)), ALT);
  cv.overlay.push([pyRound(wx), pyRound(wy - 1), "white"]);
}

function oneWing(cv, gen, kind, x, y, sw, side, tilt, stage, k) {
  if (kind === "feather") featherWing(cv, x, y, sw, side, tilt, stage, k);
  else if (kind === "bat") batWing(cv, x, y, sw, side, tilt, stage, k);
  else if (kind === "moth") {
    sw *= 1.25;
    const ux = x + side * sw * 0.66, uy = y - sw * 0.42;
    const up = cv.ell(ux, uy, sw * 0.62, sw * 0.52);
    cv.add(up, ACCENT, { centre: [ux - side * sw * 0.2, uy - sw * 0.2], r: sw * 0.8 });
    const lx = x + side * sw * 0.45, ly = y + sw * 0.25;
    const lo = cv.ell(lx, ly, sw * 0.42, sw * 0.38);
    cv.add(lo, ACCENT, { centre: [lx, ly - sw * 0.2], r: sw * 0.6 });
    const band = maskAndNot(up, cv.ell(ux - side * 1, uy + 1, sw * 0.62 - 2, sw * 0.52 - 2));
    cv.paint(band, ALT);
    const er = Math.max(1.2, sw * 0.14);
    cv.paint(maskAnd(cv.ell(ux + side * sw * 0.12, uy, er + 1, er + 1), up), DARK);
    const spot = maskAnd(cv.ell(ux + side * sw * 0.12, uy, er, er), up);
    cv.paint(spot, GLOW);
    cv.setFlat(spot, 1);
  } else if (kind === "leaf") {
    leaf(cv, x, y, sw * 1.1, -PI / 2 + side * (1.15 - tilt), sw * 0.38);
    leaf(cv, x, y + 2, sw * 0.8, -PI / 2 + side * (1.65 - tilt), sw * 0.3);
  } else if (kind === "crystal") {
    crystal(cv, x + side * 1, y, sw * 1.1, Math.max(2, sw * 0.22), -PI / 2 + side * (0.85 - tilt));
    crystal(cv, x + side * 1, y + 2, sw * 0.8, Math.max(1.6, sw * 0.17), -PI / 2 + side * (1.3 - tilt));
  } else if (kind === "flame") {
    cv.add(cv.poly(flamePts(x + side * sw * 0.5, y + 2, sw * 0.9, sw * 1.2, side * 1.0, 3)), GLOW, { flat: true });
  } else if (kind === "vanes") {
    for (let j = 0; j < 3; j++) {
      const ang = -PI / 2 + side * (0.7 - tilt + 0.35 * j);
      const ex = x + Math.cos(ang) * sw, ey = y + Math.sin(ang) * sw;
      cv.add(cv.line([[x, y], [ex, ey]], Math.max(1.5, 2.2 * k)), ALT);
      cv.add(cv.ell(ex, ey, 1.2, 1.2), GLOW, { flat: true, outline: false });
    }
  }
}

function _wings(cv, gen, x, y, k, stage, spanScale = 1, off = 0, pose = "front") {
  const kind = gen.wings;
  if (kind === "none" || (stage === 1 && kind !== "moth" && kind !== "bat" && gen.genes.wing_size < 0.6)) return;
  const size = gen.genes.wing_size;
  let sw = (9 + 8 * size) * k * spanScale * (stage === 1 ? 0.55 : stage === 2 ? 1.0 : 1.3);
  if (kind === "bat") sw *= 1.5;
  let plan;
  if (pose === "front") plan = [[-1, 1, 0, 0, -off], [1, 1, 0, 0, off]];
  else if (pose === "three_quarter") plan = [[1, 0.68, 0.35, -0.45, off * 0.4], [-1, 1, 0.1, 0, -off * 0.3]];
  else plan = [[-1, 0.8, 0.55, -0.5, 2.5], [-1, 1, 0.3, 0, 0]];
  for (const [side, sc, tilt, bias, dx] of plan) {
    cv.bias = bias;
    oneWing(cv, gen, kind, x + dx, y, sw * sc, side, tilt, stage, k);
  }
  cv.bias = 0;
}

function withBack(cv, fn) {
  const prev = cv.cur;
  cv.cur = "back";
  try { return fn(); }
  finally { cv.cur = prev; }
}
function tail(cv, gen, x, y, k, stage, side = 1) {
  return withBack(cv, () => _tail(cv, gen, x, y, k, stage, side));
}
function wings(cv, gen, x, y, k, stage, spanScale = 1, off = 0, pose = "front") {
  return withBack(cv, () => _wings(cv, gen, x, y, k, stage, spanScale, off, pose));
}
function backPart(cv, fn) { return withBack(cv, fn); }

function face(cv, gen, hx, hy, hr, k, stage, pxList, pose = "front", mouthXy = null, eyeY = null) {
  const gg = gen.genes;
  const big = { 1: 1.12, 2: 1.0, 3: 0.86 }[stage];
  const ew = Math.max(2.0, hr * (0.19 + 0.07 * gg.eye_size) * big);
  const eh = ew * 1.3;
  const gap = Math.max(ew + 1.6, hr * (0.44 + 0.10 * gg.eye_gap));
  const ey = eyeY != null ? eyeY : hy + hr * (stage < 3 ? 0.10 : 0.02);
  let eyes;
  if (pose === "front") eyes = [[hx - gap, ew, -1, true], [hx + gap, ew, 1, true]];
  else if (pose === "three_quarter") {
    const farW = Math.max(1.6, ew * 0.74);
    const fx = Math.min(hx + gap * 0.95, hx + hr * 0.92 - farW);
    eyes = [[hx - gap * 0.5, ew * 1.04, -1, true], [fx, farW, 1, false]];
  } else eyes = [[hx + hr * 0.25, ew * 1.08, 1, true]];
  const style = gen.eye_style;
  const fierce = stage === 3 && (gen.temperament === "Fierce" || gen.temperament === "Bold");
  for (const [ex, w, side, near] of eyes) {
    const h = near ? w * 1.3 : eh * 0.95;
    const m = cv.ell(ex, ey, w, h);
    cv.paint(m, EYE);
    cv.setFlat(m, 1);
    const iris = maskAnd(m, cv.ell(ex + (pose !== "front" ? 0.25 * w : 0), ey + h * 0.32, w * 0.78, h * 0.55));
    cv.paint(iris, IRIS);
    let lid = null;
    if (style === "closed") lid = m.slice();
    else if (style === "sleepy") lid = maskWhere(m, (_x, y) => y < ey - h * 0.1);
    else if (fierce) {
      lid = maskWhere(m, (x, y) => {
        const inner = (x - ex) * (-side) / Math.max(w, 1);
        return y < ey - h * 0.75 + (inner + 1) * h * 0.32;
      });
    }
    if (lid) {
      cv.paint(lid, BASE);
      cv.setFlat(lid, 0);
      cv.setLight(lid, 0);
      cv.paint(maskAnd(maskAndNot(m, lid), rollY(lid)), EYE);
    }
    if (style === "closed") {
      const q0 = -trunc(w * 0.8);
      const q1 = trunc(w * 0.8);
      for (let q = q0; q <= q1; q++) {
        const yy = pyRound(ey + h * 0.2 - (Math.abs(q) >= w * 0.6 ? 1 : 0));
        pxList.push([pyRound(ex + q), yy, "line"]);
      }
      continue;
    }
    const hlx = pyRound(ex - w * 0.45);
    const hly = pyRound(ey - h * (lid == null ? 0.45 : 0.0));
    pxList.push([hlx, hly, "white"]);
    if (w >= 3.0 && lid == null) {
      pxList.push([hlx + 1, hly, "white"], [hlx, hly + 1, "white"], [hlx + 1, hly + 1, "white"]);
    }
    pxList.push([pyRound(ex + w * 0.4), pyRound(ey + h * 0.45), "white"]);
    if (style === "sparkle") pxList.push([pyRound(ex + w * 0.15), pyRound(ey - h * 0.1), "white"]);
    if (near && (stage < 3 || gen.temperament === "Playful" || gen.temperament === "Gentle" || gen.temperament === "Serene")) {
      const cs = pose === "front" ? side : -1;
      for (const q of [0, cs]) pxList.push([pyRound(ex + cs * w * 0.9 + q), pyRound(ey + h * 1.05), "cheek"]);
    }
  }
  let mx, my;
  if (mouthXy == null) {
    my = pyRound(ey + eh * 1.05 + (stage === 3 ? 1 : 0));
    mx = pyRound(hx - 0.5 + (pose === "three_quarter" ? gap * 0.25 : 0));
  } else {
    mx = pyRound(mouthXy[0]);
    my = pyRound(mouthXy[1]);
  }
  const mouth = gen.mouth;
  if (pose === "side") {
    pxList.push([mx, my, "line"], [mx - 1, my, "line"], [mx - 2, my - 1, "line"]);
    if (mouth === "fang") pxList.push([mx - 1, my + 1, "white"]);
    else if (mouth === "open") pxList.push([mx - 1, my + 1, "mouth"], [mx, my + 1, "line"]);
    return;
  }
  if (mouth === "w") {
    pxList.push([mx - 1, my, "line"], [mx, my + 1, "line"], [mx + 1, my + 1, "line"], [mx + 2, my, "line"]);
  } else if (mouth === "fang") {
    pxList.push([mx, my, "line"], [mx + 1, my, "line"], [mx - 1, my - 1, "line"], [mx + 2, my - 1, "line"], [mx + 1, my + 1, "white"]);
  } else if (mouth === "open") {
    pxList.push([mx, my, "line"], [mx + 1, my, "line"], [mx, my + 1, "mouth"], [mx + 1, my + 1, "mouth"], [mx - 1, my, "line"], [mx + 2, my, "line"]);
  } else if (stage < 3) {
    pxList.push([mx - 1, my, "line"], [mx, my + 1, "line"], [mx + 1, my + 1, "line"], [mx + 2, my, "line"]);
  } else {
    pxList.push([mx, my, "line"], [mx + 1, my, "line"]);
  }
}

function quadruped(cv, gen, stage, k, hr0, chub, legf, pose, px) {
  const body = gen.body;
  const drag = body === "dragonling";
  const legH = (drag ? 5.5 : 7.5) * k * legf;
  const brx = (drag ? 12.0 : 13.0) * k * chub;
  const bry = (drag ? 7.6 : 6.2) * k * chub;
  const bcx = CX - 6.0 * k;
  const bcy = G - legH - bry * 0.6;
  const hr = hr0 * (drag ? 0.98 : 0.9);
  const hx = bcx + brx * (pose === "three_quarter" ? 0.8 : 0.95);
  let hy = bcy - bry * 0.85 - hr * 0.45;
  const earLift = ["pointy", "horns", "flame", "crystal", "antlers"].includes(gen.ears) ? 2 : 0;
  hy = Math.max(hy, hr + 6 * k + earLift);
  wings(cv, gen, bcx + brx * 0.05, bcy - bry * 0.7, k, stage, 1, brx * 0.25, pose);
  tail(cv, gen, bcx - brx * 0.85, bcy - bry * 0.15, k, stage, -1);
  const lw = (drag ? 3.0 : 2.5) * k * chub + 0.6;
  const pawMat = (gen.element === "ember" || gen.element === "machine" || drag) ? ALT : BELLY;
  cv.bias = -0.5;
  for (const lx of [bcx - brx * 0.5 + 2.5, bcx + brx * 0.55 + 2.5]) {
    cv.add(cv.ell(lx, G - legH * 0.5 - 1, lw, legH * 0.55 + 1.5), BASE);
    cv.add(cv.ell(lx + 0.8, G - 1.3, lw + 0.5, 1.3 + k), pawMat);
  }
  cv.bias = 0;
  if (drag && stage >= 2 && gen.wings === "none") {
    for (const t of linspace(-0.55, 0.45, 3 + stage)) {
      const sx = bcx + brx * t;
      const sy = bcy - bry * Math.sqrt(Math.max(0, 1 - t * t)) + 1;
      const s = (1.8 + 0.8 * stage) * k;
      cv.add(cv.poly([[sx - s * 0.6, sy + 1], [sx - s * 0.1, sy - s * 1.2], [sx + s * 0.6, sy + 1]]), ALT);
    }
  }
  cv.add(cv.ell(bcx, bcy, brx, bry), BASE);
  const neck = [
    [bcx + brx * 0.55, bcy - bry * 0.2, bry * 0.8],
    [hx - hr * 0.15, hy + hr * 0.45, hr * 0.5],
  ];
  {
    const [m, l] = cv.chain(neck);
    cv.add(m, BASE, { light: l, outline: false });
  }
  const bodyM = cv.ell(bcx, bcy, brx, bry);
  const bm = maskAnd(cv.ell(bcx + brx * 0.12, bcy + bry * 0.45, brx * 0.62, bry * 0.5), bodyM);
  cv.add(bm, BELLY, { outline: false });
  if (drag) {
    const yA = trunc(bcy + bry * 0.2), yB = trunc(bcy + bry);
    for (let yy = yA; yy < yB; yy += 2) cv.bumpLight(maskWhere(bm, (_x, y) => y === yy), -0.7);
  } else {
    const ruff = [];
    for (let i = 0; i < 4; i++) {
      ruff.push([
        hx - hr * 0.35 + i * 1.4 * k,
        hy + hr * 0.75 + (i % 2) * 1.2,
        (2.0 + 0.6 * (stage - 1)) * k + 0.4,
      ]);
    }
    const [m, l] = cv.chain(ruff);
    cv.add(m, BELLY, { light: l });
  }
  for (const lx of [bcx - brx * 0.58, bcx + brx * 0.45]) {
    cv.add(cv.ell(lx, G - legH * 0.5 - 1, lw, legH * 0.55 + 1.5), BASE);
    cv.add(cv.ell(lx + 0.8, G - 1.3, lw + 0.6, 1.4 + k), pawMat);
  }
  const ehShift = hr * (pose === "three_quarter" ? 0.18 : 0.38);
  const earR = hr * (pose === "three_quarter" ? 0.85 : 0.55);
  ears(cv, gen, hx - ehShift, hy, earR, k, stage);
  cv.add(cv.ell(hx, hy, hr, hr * 0.88), BASE);
  const sx = hx + hr * (pose === "three_quarter" ? 0.72 : 0.88);
  const sy = hy + hr * 0.32;
  const srx = hr * (drag ? 0.52 : 0.46);
  const sry = hr * (drag ? 0.36 : 0.32);
  cv.add(cv.ell(sx, sy, srx, sry), BASE);
  cv.add(maskAnd(cv.ell(sx, sy + sry * 0.45, srx * 0.85, sry * 0.55), cv.ell(sx, sy, srx, sry)), BELLY, { outline: false });
  ears(cv, gen, hx - ehShift, hy, earR, k, stage, "front");
  const nx = pyRound(sx + srx - 1);
  px.push([nx, pyRound(sy - sry * 0.4), "nose"], [nx - 1, pyRound(sy - sry * 0.4), "nose"]);
  face(cv, gen, hx - hr * 0.08, hy - hr * 0.05, hr, k, stage, px, pose, [sx + srx * 0.25, sy + sry * 0.35]);
  return [hx, hy, hr];
}

function bird(cv, gen, stage, k, hr0, chub, legf, pose, px) {
  const gg = gen.genes;
  const legH = 4.5 * k * legf + 1;
  const brx = (9.5 + 1.5 * gg.chub) * k * (stage === 1 ? 1.15 : 1.0);
  const bry = brx * (stage === 1 ? 1.0 : 1.12);
  const bcx = CX - 1.5;
  const bcy = G - legH - bry;
  const q = pose === "three_quarter";
  let hr, hx, hy;
  if (stage === 1) { hr = brx * 0.92; hx = bcx + (q ? 1.5 : 0); hy = bcy - bry * 0.2; }
  else { hr = hr0 * 0.85; hx = bcx + (q ? brx * 0.32 : 0); hy = bcy - bry * 0.82; }
  backPart(cv, () => {
    const tx = q ? bcx - brx * 0.75 : bcx;
    const ty = q ? bcy + bry * 0.25 : bcy + bry * 0.5;
    const n = 3 + yn(stage >= 2) + yn(stage === 3);
    for (let j = 0; j < n; j++) {
      const a = q
        ? PI * (0.85 + 0.35 * (j / Math.max(1, n - 1)))
        : PI / 2 + (j - (n - 1) / 2) * 0.32;
      const L = (7 + 5 * gg.tail_size) * k * (1.0 + 0.25 * yn(stage === 3)) * (q ? 1.0 : 0.75);
      leaf(cv, tx, ty, L, a, Math.max(1.5, 1.3 * k + 0.6), j % 2 === 0 ? ALT : ACCENT);
    }
  });
  if (stage >= 2 && gen.wings !== "none") {
    wings(cv, gen, bcx - (q ? 1 : 0), bcy - bry * 0.45, k, stage, 1.3, brx * 0.5, pose);
  }
  for (const side of (q ? [-0.35, 0.55] : [-1, 1])) {
    const lx = bcx + side * brx * 0.38;
    cv.add(cv.line([[lx, bcy + bry * 0.8], [lx, G - 1]], Math.max(1.0, 1.1 * k + 0.2)), BEAK);
    cv.add(cv.line([[lx - 1.5, G - 0.5], [lx + 2.0, G - 0.5]], 1), BEAK);
  }
  cv.add(cv.ell(bcx, bcy, brx, bry), BASE);
  cv.add(maskAnd(
    cv.ell(bcx + (q ? brx * 0.25 : 0), bcy + bry * 0.35, brx * 0.58, bry * 0.55),
    cv.ell(bcx, bcy, brx, bry),
  ), BELLY, { outline: false });
  const fx = q ? bcx - brx * 0.15 : bcx - brx * 0.78;
  const fy = q ? bcy - bry * 0.15 : bcy - bry * 0.05;
  const mats = [BASE, ALT, ACCENT];
  for (let j = 0; j < 2 + yn(stage >= 2); j++) {
    const ang = q ? PI * (0.62 + 0.07 * j) : PI * (0.55 + 0.05 * j);
    leaf(cv, fx, fy + j * 1.2, brx * (0.95 - 0.12 * j), ang, Math.max(1.8, brx * 0.24), mats[j % 3]);
  }
  if (!q) {
    for (let j = 0; j < 2 + yn(stage >= 2); j++) {
      leaf(cv, bcx + brx * 0.78, bcy - bry * 0.05 + j * 1.2, brx * (0.95 - 0.12 * j), PI * (0.45 - 0.05 * j), Math.max(1.8, brx * 0.24), mats[j % 3]);
    }
  }
  if (stage >= 2) cv.add(cv.ell(hx, hy, hr, hr * 0.92), BASE);
  const kind = gen.ears;
  if (["pointy", "round", "leaf", "flame", "crystal", "feelers", "antlers"].includes(kind)) {
    const n = stage < 3 ? 3 : 4;
    for (let j = 0; j < n; j++) {
      const a = -PI / 2 - 0.5 + (0.9 * j / (n - 1)) - (q ? 0.4 : 0);
      if (kind === "flame") {
        cv.add(cv.poly(flamePts(hx - 2 + j * 1.5, hy - hr * 0.8, 3, 5 * k + 2, -0.6, 1)), GLOW, { flat: true });
      } else {
        leaf(cv, hx - (q ? 2 : 0), hy - hr * 0.8, (4 + 3 * gg.ear_size) * k + 1.5 * yn(stage === 3), a, Math.max(1.2, 1.0 * k + 0.4), ACCENT);
      }
    }
  } else {
    ears(cv, gen, hx, hy, hr, k, stage);
    ears(cv, gen, hx, hy, hr, k, stage, "front");
  }
  const by = hy + hr * (stage === 1 ? 0.18 : 0.12);
  if (q) {
    const bx = hx + hr * 0.78;
    const bl = (2.0 + 1.1 * stage) * k + 1;
    cv.add(cv.poly([[bx - 1, by - bl * 0.38], [bx + bl, by + bl * 0.08], [bx - 1, by + bl * 0.42]]), BEAK);
    face(cv, gen, hx - hr * 0.1, hy - hr * 0.05, hr, k, stage, px, pose, [bx + 2, by + 3], hy - hr * 0.02);
  } else {
    const bl = (1.8 + 0.8 * stage) * k + 1;
    cv.add(cv.poly([[hx - bl, by + 1], [hx + 0.5, by - bl * 0.3], [hx + bl + 1, by + 1], [hx + 0.5, by + bl * 1.1]]), BEAK);
    face(cv, gen, hx, hy - hr * 0.08, hr, k, stage, px, pose, [hx, by + bl * 1.2 + 1], hy - hr * 0.1);
  }
  return [hx, hy, hr];
}

function fish(cv, gen, stage, k, hr0, chub, legf, pose, px) {
  const gg = gen.genes;
  const brx = (13 + 2 * gg.chub) * k * (stage === 1 ? 1.08 : 1.0);
  const bry = (8.0 + 2.5 * gg.chub) * k * (stage === 1 ? 1.1 : 1.0);
  const bcx = CX + 1;
  const bcy = G - 5 - 5 * k - bry;
  const finL = (6 + 6 * gg.tail_size) * k * (1 + 0.3 * yn(stage === 3));
  backPart(cv, () => {
    const tx = bcx - brx * 0.98;
    cv.add(cv.poly([
      [tx + 2, bcy - 1],
      [tx - finL * 0.9, bcy - finL * 0.95],
      [tx - finL * 0.55, bcy],
      [tx - finL * 0.9, bcy + finL * 0.85],
      [tx + 2, bcy + 1],
    ]), ACCENT, { centre: [tx, bcy - finL * 0.3], r: finL });
    for (const s of [-1, 1]) {
      cv.add(cv.line([[tx + 1, bcy], [tx - finL * 0.75, bcy + s * finL * 0.7]], 1), ACCENT, { outline: false, bias: 0.6 });
    }
    const dh = bry * (0.65 + 0.25 * stage) + 2;
    const d0 = bcx - brx * 0.45, d1 = bcx + brx * 0.3;
    cv.add(cv.poly([[d0, bcy - bry * 0.7], [d0 + (d1 - d0) * 0.2, bcy - bry * 0.8 - dh], [d1, bcy - bry * 0.75]]), ACCENT, { centre: [d0, bcy - bry - dh * 0.5], r: dh });
    for (const t of [0.25, 0.5, 0.75]) {
      cv.add(cv.line([
        [d0 + (d1 - d0) * t, bcy - bry * 0.75],
        [d0 + (d1 - d0) * 0.2 * (1 - t) + (d1 - d0) * t * 0.6, bcy - bry * 0.8 - dh * (1 - 0.6 * t)],
      ], 1), ACCENT, { outline: false, bias: 0.6 });
    }
    cv.add(cv.poly([
      [bcx - brx * 0.35, bcy + bry * 0.75],
      [bcx - brx * 0.6, bcy + bry * 0.75 + finL * 0.55],
      [bcx - brx * 0.05, bcy + bry * 0.85],
    ]), ACCENT);
  });
  const body = maskOr(
    cv.ell(bcx, bcy, brx, bry),
    cv.poly([
      [bcx - brx * 0.55, bcy - bry * 0.55],
      [bcx - brx * 1.0, bcy - bry * 0.2],
      [bcx - brx * 1.0, bcy + bry * 0.2],
      [bcx - brx * 0.55, bcy + bry * 0.55],
    ]),
  );
  cv.add(body, BASE, { centre: [bcx, bcy], r: Math.max(brx, bry) });
  cv.paint(maskWhere(body, (_x, y) => y > bcy + bry * 0.22), BELLY);
  const gx = bcx + brx * 0.22;
  cv.bumpLight(maskAnd(cv.line([[gx, bcy - bry * 0.55], [gx - 1.5, bcy], [gx, bcy + bry * 0.55]], 1), body), -1.1);
  if (stage >= 2 && gen.element === "crystal") {
    for (const t of [-0.45, -0.1, 0.25].slice(0, stage)) {
      crystal(cv, bcx + brx * t, bcy - bry * 0.8, (3 + 2 * stage) * k, 1.6, -PI / 2 - 0.3);
    }
  }
  if (stage >= 2 && (gen.element === "umbral" || gen.element === "machine")) {
    const ax = bcx + brx * 0.55, ay = bcy - bry * 0.7;
    const tip = [ax + 6 * k, ay - 7 * k];
    cv.add(cv.line([[ax, ay], [ax + 4 * k, ay - 7 * k], tip], 1), DARK);
    cv.add(cv.ell(tip[0], tip[1] + 1, 1.8 * k + 0.5, 1.8 * k + 0.5), GLOW, { flat: true });
  }
  const hx = bcx + brx * 0.48, hy = bcy - bry * 0.12, hr = bry * 0.95;
  leaf(cv, bcx + brx * 0.05, bcy + bry * 0.3, finL * 0.75, PI * 0.82, Math.max(1.6, finL * 0.22), ACCENT);
  face(cv, gen, hx, hy, hr, k, stage, px, "side", [bcx + brx * 0.93, bcy + bry * 0.18], hy - hr * 0.05);
  cv.floatH = 5 + 5 * k;
  return [hx, hy, hr];
}

function serpent(cv, gen, stage, k, hr0, chub, legf, pose, px) {
  const gg = gen.genes;
  const br = (5.0 + 2 * gg.chub) * k * 1.1;
  const j = gg.tail_size - 0.5;
  const span = { 1: 14, 2: 21, 3: 26 }[stage];
  const ctrl = [
    [CX - span, G - br * 0.6 - 1],
    [CX - span * 0.45, G - br - 9 * k * (1 + j)],
    [CX - span * 0.05, G - br * 0.5],
    [CX + span * 0.45, G - br * 0.6],
    [CX + span * 0.5, G - 16 * k - 4],
  ];
  const n = { 1: 14, 2: 22, 3: 30 }[stage];
  const pts = bezier(ctrl, n).map((p, i) => {
    const t = i / (n - 1);
    return [p[0], p[1], br * (0.35 + 0.65 * (t ** 0.6))];
  });
  const hr = hr0 * 0.9;
  const last = pts[pts.length - 1];
  const hx = last[0] + 1.5 * k;
  let hy = last[1] - hr * 0.55;
  hy = Math.max(hy, hr + 6);
  tail(cv, gen, pts[0][0], pts[0][1], k * 0.8, stage, -1);
  if ((gen.wings === "crystal" || gen.wings === "flame" || gen.wings === "bat") && stage >= 2) {
    for (let i = 3; i < n - 3; i += 4) {
      const [x, y, r] = pts[i];
      if (gen.wings === "crystal") crystal(cv, x, y - r * 0.6, r * 1.3 + 1, Math.max(1.3, r * 0.3), -PI / 2 - 0.25);
      else {
        backPart(cv, () => cv.add(cv.poly([
          [x - r, y - r * 0.4],
          [x - r * 0.2, y - r * 1.9],
          [x + r * 0.7, y - r * 0.5],
        ]), ACCENT));
      }
    }
  }
  const [m, l] = cv.chain(pts);
  cv.add(m, BASE, { light: l });
  cv.paint(maskWhere(m, (_x, _y, i) => f32gt(cv.chainDy[i], 0.4)), BELLY);
  if (stage >= 2) {
    for (let i = 2; i < n - 2; i += 3) {
      const [x, y, r] = pts[i];
      cv.bumpLight(maskWhere(m, (px, py) => Math.abs((px - x) + 0.3 * (py - y)) < 0.5 && (px - x) ** 2 + (py - y) ** 2 < r * r), -0.6);
    }
  }
  ears(cv, gen, hx - hr * 0.45, hy, hr * 0.6, k, stage);
  cv.add(cv.ell(hx, hy, hr * 1.0, hr * 0.85), BASE);
  const sx = hx + hr * 0.82, sy = hy + hr * 0.25;
  cv.add(cv.ell(sx, sy, hr * 0.5, hr * 0.34), BASE);
  cv.add(maskAnd(cv.ell(sx, sy + hr * 0.18, hr * 0.42, hr * 0.17), cv.ell(sx, sy, hr * 0.5, hr * 0.34)), BELLY, { outline: false });
  ears(cv, gen, hx - hr * 0.45, hy, hr * 0.6, k, stage, "front");
  px.push([pyRound(sx + hr * 0.38), pyRound(sy - hr * 0.15), "nose"]);
  face(cv, gen, hx - hr * 0.1, hy - hr * 0.05, hr, k, stage, px, "side", [sx + hr * 0.35, sy + hr * 0.15]);
  return [hx, hy, hr];
}

function biped(cv, gen, stage, k, hr0, chub, legf, pose, px) {
  const gg = gen.genes;
  const q = pose === "three_quarter";
  const legH = (3.5 + 3 * (stage - 1)) * k * (0.8 + 0.4 * gg.legs);
  const bw = (8.0 + 2 * gg.chub) * k;
  const bh = (7.5 + 2.0 * (stage - 1)) * k;
  const bcx = CX;
  const bcy = G - legH - bh * 0.85;
  const hr = hr0 * 1.02;
  const hx = bcx + (q ? hr * 0.1 : 0);
  let hy = bcy - bh * 0.7 - hr * 0.62;
  hy = Math.max(hy, hr + 7 * k);
  if (stage === 3) {
    backPart(cv, () => cv.add(cv.poly([
      [bcx - bw * 0.8, bcy - bh * 0.6],
      [bcx + bw * 0.8, bcy - bh * 0.6],
      [bcx + bw * 1.45, G - 1],
      [bcx - bw * 1.45, G - 1],
    ]), ACCENT));
  }
  wings(cv, gen, bcx, bcy - bh * 0.4, k, stage, 1, bw * 0.5, pose);
  tail(cv, gen, bcx + bw * 0.6, bcy + bh * 0.3, k, stage, 1);
  for (const side of [-1, 1]) {
    const lx = bcx + side * bw * 0.45;
    cv.add(cv.ell(lx, G - legH * 0.5 - 1, 2.6 * k + 0.7, legH * 0.5 + 1.5), BASE);
    cv.add(cv.ell(lx + side * 0.6 + (q ? 1 : 0), G - 1.3, 3.0 * k + 0.8, 1.4 + k), ALT);
  }
  cv.add(cv.ell(bcx, bcy, bw, bh), BASE);
  cv.add(maskAnd(cv.ell(bcx + (q ? 1 : 0), bcy + bh * 0.15, bw * 0.55, bh * 0.65), cv.ell(bcx, bcy, bw, bh)), BELLY, { outline: false });
  for (const side of [-1, 1]) {
    const ax = bcx + side * (bw + 0.8 * k);
    const ar = (2.2 + 0.8 * (stage - 1)) * k + 0.6;
    cv.add(cv.ell(ax, bcy + bh * 0.05, ar, bh * 0.55), BASE, { bias: (q && side > 0) ? -0.3 : 0 });
    cv.add(cv.ell(ax, bcy + bh * 0.5, ar + 0.4, ar + 0.2), (gen.element !== "machine" && gen.element !== "ember") ? BELLY : ALT);
  }
  if (stage >= 2) cv.add(cv.ell(bcx, bcy - bh * 0.8, bw * 0.75, 2.0 * k + 0.6), ALT);
  ears(cv, gen, hx, hy, hr, k, stage);
  cv.add(cv.ell(hx, hy, hr, hr * 0.9), BASE);
  ears(cv, gen, hx, hy, hr, k, stage, "front");
  face(cv, gen, hx, hy, hr, k, stage, px, pose);
  return [hx, hy, hr];
}

const PLANS = { fox: quadruped, dragonling: quadruped, bird, fish, serpent, biped };

function build(gen, stage, layer = "all", sparkle = true) {
  const cv = new Canvas();
  cv.skipMain = layer === "back";
  cv.floatH = 0;
  const k = STAGE_K[stage];
  const gg = gen.genes;
  const body = gen.body;
  const pose = gen.pose ?? "front";
  const px = [];
  const headboost = { 1: 1.28, 2: 1.06, 3: 0.92 }[stage];
  let hr = (10.5 + 3 * gg.head) * k * headboost;
  const chub = 0.85 + 0.35 * gg.chub;
  const legf = { 1: 0.45, 2: 1.0, 3: 1.25 }[stage] * (0.7 + 0.6 * gg.legs);
  const didFace = Object.prototype.hasOwnProperty.call(PLANS, body);
  let hx, hy;
  if (didFace) {
    [hx, hy, hr] = PLANS[body](cv, gen, stage, k, hr, chub, legf, pose, px);
  } else if (body === "pup") {
    const legH = 6 * k * legf;
    const brx = 13 * k * chub, bry = 8.5 * k * chub;
    const bcy = G - legH - bry * 0.55;
    hx = CX;
    hy = bcy - bry * 0.45 - hr * 0.55;
    if (hy - hr < 9 * k) hy = hr + 9 * k;
    wings(cv, gen, CX, bcy - bry * 0.5, k, stage, 1, brx * 0.55);
    tail(cv, gen, CX + brx * 0.75, bcy - bry * 0.1, k, stage, 1);
    for (const side of [-1, 1]) {
      const lx = CX + side * brx * 0.78;
      cv.add(cv.ell(lx, G - legH * 0.45 - 1, 3.0 * k * chub + 0.5, legH * 0.5 + 2), BASE);
      cv.add(cv.ell(lx + side * 0.5, G - 1.2, 3.0 * k + 0.6, 1.6 + k), (gen.element === "ember" || gen.element === "machine") ? ALT : BASE);
    }
    cv.add(cv.ell(CX, bcy, brx, bry), BASE);
    if (stage === 3) {
      const mane = linspace(0.1, PI - 0.1, 7).map((a) => [
        CX + Math.cos(a) * hr * 0.95,
        hy + hr * 0.55 + Math.sin(a) * hr * 0.45,
        hr * 0.32,
      ]);
      const [m, l] = cv.chain(mane);
      cv.add(m, gen.element === "ember" ? GLOW : ALT, { light: l, flat: gen.element === "ember" });
    }
    cv.add(cv.ell(CX, bcy + bry * 0.25, brx * 0.42, bry * 0.65), BELLY, { outline: false });
    for (const side of [-1, 1]) {
      const lx = CX + side * hr * 0.42;
      cv.add(cv.ell(lx, G - legH * 0.5 - 1, 2.6 * k * chub + 0.7, legH * 0.55 + 1.5), BASE);
      cv.add(cv.ell(lx, G - 1.4, 3.0 * k + 0.7, 1.4 + k), (gen.element !== "ember" && gen.element !== "machine") ? BELLY : ALT);
    }
    ears(cv, gen, hx, hy, hr, k, stage);
    cv.add(cv.ell(hx, hy, hr, hr * 0.9), BASE);
    ears(cv, gen, hx, hy, hr, k, stage, "front");
    cv.add(cv.ell(hx, hy + hr * 0.5, hr * 0.42, hr * 0.3), BELLY, { outline: false });
    px.push([pyRound(hx - 0.5), pyRound(hy + hr * 0.35), "nose"]);
    px.push([pyRound(hx + 0.5), pyRound(hy + hr * 0.35), "nose"]);
  } else if (body === "sprout") {
    const brx = (12.5 + 2 * gg.chub) * k * (stage === 1 ? 1.15 : 1.0) * (stage === 3 ? 1.08 : 1);
    const bry = brx * 0.88;
    const bcy = G - 2 * k - bry;
    hx = CX; hy = bcy - bry * 0.18; hr = brx;
    wings(cv, gen, CX, bcy - bry * 0.1, k, stage, 1, brx * 0.6);
    tail(cv, gen, CX + brx * 0.7, bcy + bry * 0.4, k, stage);
    for (const side of [-1, 1]) {
      cv.add(cv.ell(CX + side * brx * 0.5, G - 2.2 * k - 0.5, 3.4 * k + 0.6, 2.2 * k + 0.8), stage > 1 ? ALT : BASE);
    }
    if (stage >= 2) {
      for (const side of [-1, 1]) {
        const ax = CX + side * brx * 0.95;
        const ar = (2.4 + 1.6 * yn(stage === 3)) * k + 0.6;
        cv.add(cv.ell(ax, bcy + bry * 0.25, ar, ar * 1.3), BASE);
      }
    }
    ears(cv, gen, hx, hy - hr * 0.05, hr * 0.85, k, stage);
    cv.add(cv.ell(CX, bcy, brx, bry), BASE);
    cv.add(cv.ell(CX, bcy + bry * 0.5, brx * 0.55, bry * 0.42), BELLY, { outline: false });
    ears(cv, gen, hx, hy - hr * 0.05, hr * 0.85, k, stage, "front");
    if (stage === 3) {
      for (const side of [-1, 1]) {
        const ax = CX + side * brx * 0.95;
        if (gen.element === "verdant" || gen.element === "grove") leaf(cv, ax, bcy - bry * 0.1, 6 * k, -PI / 2 + side * 0.6, 2);
        else if (gen.element === "crystal" || gen.element === "frost") crystal(cv, ax, bcy, 6, 1.6, -PI / 2 + side * 0.5);
        else if (gen.element === "ember") cv.add(cv.poly(flamePts(ax, bcy, 5, 7, side, 2)), GLOW, { flat: true });
      }
    }
    hy = bcy - bry * 0.2;
    hr = brx * 0.95;
  } else if (body === "moth") {
    const brx = (9 + 2 * gg.chub) * k * (stage === 1 ? 1.2 : 1.0);
    const bry = brx * (stage === 1 ? 1.05 : 1.15);
    const bcy = G - 3 * k - bry;
    wings(cv, gen, CX, bcy - bry * 0.1, k, stage, 1.15);
    for (const side of [-1, 1]) cv.add(cv.ell(CX + side * brx * 0.45, G - 2, 2 * k + 0.5, 2 * k + 0.6), ALT);
    cv.add(cv.ell(CX, bcy, brx, bry), BASE);
    const ruff = linspace(0.15, PI - 0.15, 7).map((a) => [
      CX + Math.cos(a) * brx * 0.8,
      bcy + bry * 0.05 + Math.sin(a) * bry * 0.3,
      brx * 0.32,
    ]);
    {
      const [m, l] = cv.chain(ruff);
      cv.add(m, BELLY, { light: l });
    }
    hr = brx * 0.95;
    hx = CX; hy = bcy - bry * 0.4;
    const g2 = { ...gen, ears: (gen.ears !== "horns" && gen.ears !== "round") ? "feelers" : gen.ears };
    ears(cv, g2, hx, hy, hr, k, stage);
    cv.add(cv.ell(hx, hy, hr, hr * 0.82), BASE);
    tail(cv, gen, CX + brx * 0.6, bcy + bry * 0.6, k * 0.8, stage);
  } else if (body === "axolotl") {
    hr = (10 + 3 * gg.head) * k * headboost * 0.95;
    const br = (6.0 + 2 * gg.chub) * k * (stage < 3 ? 1.0 : 1.1);
    let ctrl;
    if (stage < 3) {
      ctrl = [[CX - 1, G - br - 3 * k], [CX + 8 * k, G - br * 0.9], [CX + 16 * k, G - br * 0.6], [CX + 22 * k, G - 9 * k]];
    } else {
      const j1 = gg.tail_size - 0.5, j2 = gg.legs - 0.5;
      ctrl = [[CX - 3, 38], [CX + 2 + 6 * j2, 58], [CX + 22 + 4 * j1, 60], [CX + 26 - 8 * j2, 34 + 10 * j1], [CX + 18 + 10 * j1, 14 + 8 * j2]];
    }
    const n = { 1: 10, 2: 16, 3: 30 }[stage];
    const rad = (p, i) => {
      const t = i / (n - 1);
      return [p[0], p[1], br * (1 - 0.72 * t) + 0.9];
    };
    let pts = bezier(ctrl, n).map(rad);
    hx = CX - (stage < 3 ? 3 : 4) * k;
    hy = stage < 3 ? (pts[0][1] - br * 0.6 - hr * 0.55) : 20;
    hy = Math.max(hy, hr + 6);
    if (stage === 3) {
      ctrl = [[hx + 1, hy + hr * 0.4], ...ctrl.slice(1)];
      pts = bezier(ctrl, n).map(rad);
      for (const idx of [trunc(n * 0.3), trunc(n * 0.5)]) {
        const [x, y, r] = pts[idx];
        cv.add(cv.ell(x - 1, y + r * 0.8, 2.6, 2.4), BASE);
      }
      for (let i = 6; i < n - 2; i += 4) {
        const [x, y, r] = pts[i];
        crystal(cv, x, y - r * 0.6, r * 1.4, Math.max(1.4, r * 0.35), -PI / 2 + 0.25 * Math.sin(i));
      }
    }
    const [m, l] = cv.chain(pts.slice().reverse());
    cv.add(m, BASE, { light: l });
    cv.paint(maskWhere(m, (_x, _y, i) => f32gt(cv.chainDy[i], 0.35)), BELLY);
    tail(cv, { ...gen }, pts[pts.length - 1][0], pts[pts.length - 1][1], k * 0.8, stage);
    if (stage < 3) {
      const [m2, l2] = cv.chain([[hx + 2, hy + hr * 0.6, br * 0.9], [pts[0][0], pts[0][1], br]]);
      cv.add(m2, BASE, { light: l2 });
      for (const side of [-1, 1]) {
        const lx = hx + side * hr * 0.5 + 2;
        cv.add(cv.ell(lx, G - 2.2 * k, 2.4 * k + 0.6, 2.4 * k + 0.7), BASE);
      }
    }
    ears(cv, gen, hx, hy, hr, k, stage);
    cv.add(cv.ell(hx, hy, hr * 1.12, hr * 0.85), BASE);
  } else {
    const tw = (12 + 3 * gg.chub) * k;
    const th = (13 + 2 * gg.legs) * k;
    const legH = 5 * k * legf;
    const ty1 = G - legH;
    const ty0 = ty1 - th;
    hr = (8.5 + 2.5 * gg.head) * k * headboost;
    hx = CX; hy = ty0 - hr * 0.55;
    wings(cv, gen, CX, ty0 + 3, k, stage, 1, tw * 0.6);
    tail(cv, gen, CX + tw * 0.7, ty1 - th * 0.2, k, stage);
    for (const side of [-1, 1]) {
      cv.add(cv.poly([
        [CX + side * tw * 0.25, ty1 - 2],
        [CX + side * tw * 0.75, ty1 - 2],
        [CX + side * tw * 0.8, G],
        [CX + side * tw * 0.2, G],
      ]), ALT);
    }
    let torso = cv.poly([
      [CX - tw * 0.85, ty0 + 2],
      [CX + tw * 0.85, ty0 + 2],
      [CX + tw, ty0 + th * 0.55],
      [CX + tw * 0.7, ty1],
      [CX - tw * 0.7, ty1],
      [CX - tw, ty0 + th * 0.55],
    ]);
    torso = maskOr(torso, cv.ell(CX, ty0 + th * 0.45, tw * 0.98, th * 0.55));
    cv.add(torso, BASE);
    cv.add(cv.ell(CX, ty0 + th * 0.55, tw * 0.45, th * 0.32), gen.element !== "machine" ? BELLY : ALT, { outline: true });
    if (gen.element === "machine") cv.add(cv.ell(CX, ty0 + th * 0.55, tw * 0.18 + 0.5, tw * 0.18 + 0.5), GLOW, { flat: true });
    for (const side of [-1, 1]) {
      const ax = CX + side * (tw + 2.5 * k);
      const ar = (3 + 1.5 * yn(stage === 3)) * k + 0.8;
      cv.add(cv.ell(ax, ty0 + th * 0.45, ar, th * 0.42), BASE);
      cv.add(cv.ell(ax, ty0 + th * 0.85, ar + 0.6, ar + 0.3), ALT);
      cv.add(cv.ell(CX + side * tw * 0.8, ty0 + 2, ar + 0.8, ar * 0.8), ALT);
    }
    ears(cv, gen, hx, hy, hr, k, stage);
    cv.add(cv.ell(hx, hy, hr * 1.05, hr * 0.92), BASE);
    ears(cv, gen, hx, hy, hr, k, stage, "front");
  }

  if (body === "moth") cv.floatH = 0;
  if (layer === "back") {
    for (let i = 0; i < W * W; i++) if (cv.layer[i] !== 1) cv.mat[i] = 0;
    return [cv, []];
  }
  pattern(cv, gen, stage);
  if (!didFace) face(cv, gen, hx, hy, hr, k, stage, px, "front");
  if (layer === "main") {
    for (let i = 0; i < W * W; i++) if (cv.layer[i] !== 2) cv.mat[i] = 0;
    cv.overlay = cv.overlay.filter((o) => o[0] >= 0 && o[0] < W && o[1] >= 0 && o[1] < W && cv.layer[o[1] * W + o[0]] === 2);
  }
  if (sparkle && layer === "all" && (stage === 3 || gen.genes.glow_amount > 0.8)) sparkles(cv, gen, stage, px);
  return [cv, px];
}

function nonzeroMat(cv, pred) {
  const xs = [], ys = [];
  for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) {
    if (pred(cv.mat[y * W + x], x, y)) { xs.push(x); ys.push(y); }
  }
  return [xs, ys];
}
function median(vals) {
  const s = vals.slice().sort((a, b) => a - b);
  const n = s.length;
  if (n % 2) return s[(n - 1) >> 1];
  return (s[n / 2 - 1] + s[n / 2]) / 2;
}

function pattern(cv, gen, stage) {
  const kind = gen.pattern;
  const v = gen.pattern_variant;
  const s = new Stream(gen.seed, "pattern");
  const [xs, ys] = nonzeroMat(cv, (mat) => mat === BASE);
  if (!xs.length) return;
  let x0 = xs[0], x1 = xs[0], y0 = ys[0], y1 = ys[0];
  for (let i = 1; i < xs.length; i++) {
    if (xs[i] < x0) x0 = xs[i];
    if (xs[i] > x1) x1 = xs[i];
    if (ys[i] < y0) y0 = ys[i];
    if (ys[i] > y1) y1 = ys[i];
  }
  const k = STAGE_K[stage];
  const dens = 0.5 + gen.genes.pattern_density;
  const at = (u, w) => [x0 + u * (x1 - x0), y0 + w * (y1 - y0)];
  const snapTo = (x, y) => {
    let best = Infinity, bi = 0;
    for (let i = 0; i < xs.length; i++) {
      const d = (xs[i] - x) ** 2 + (ys[i] - y) ** 2;
      if (d < best) { best = d; bi = i; }
    }
    return [xs[bi], ys[bi]];
  };
  const baseMask = blank();
  for (let i = 0; i < xs.length; i++) baseMask[ys[i] * W + xs[i]] = 1;

  if (kind === "spots") {
    const n = trunc((3 + (v % 4)) * dens * 1.3) + 1;
    for (let i = 0; i < n; i++) {
      const [x, y] = snapTo(...at(s.u(), s.u()));
      const r = (0.9 + s.u() * 1.9) * k + 0.25;
      cv.paint(maskAnd(cv.ell(x, y, r, r), baseMask), ALT);
    }
  } else if (kind === "stripes") {
    const period = 3 + (v % 3);
    const tilt = (((v >> 2) % 3) - 1) * 0.4;
    const span = Math.max(1, y1 - y0);
    const denom = Math.max(k, 0.6);
    for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) {
      const i = y * W + x;
      if (cv.mat[i] !== BASE) continue;
      const rel = (y - y0) / span;
      const raw = (y - y0) / denom + (x - x0) * tilt;
      const q = Math.floor(trunc(raw) / 2);
      if (pyMod(q, period) === 0 && f32gt(cv.light[i], -0.2) && rel < 0.62) cv.mat[i] = ALT;
    }
  } else if (kind === "moss") {
    const n = trunc((4 + (v % 5)) * dens) + 1;
    for (let i = 0; i < n; i++) {
      const [cx, cy] = snapTo(...at(s.u(), s.u() * 0.6));
      for (let j = 0; j < 5; j++) {
        const x = cx + pyRound((s.u() * 5 - 2) * k);
        const y = cy + pyRound((s.u() * 3 - 1) * k);
        if (x >= 0 && x < W && y >= 0 && y < W && cv.mat[y * W + x] === BASE && f32gt(cv.light[y * W + x], -0.3)) {
          cv.mat[y * W + x] = ALT;
        }
      }
    }
  } else if (kind === "facets") {
    const step = 4 + (v % 3);
    const slope = 0.6 + 0.1 * (v % 4);
    for (let off = -64; off < 64; off += step) {
      for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) {
        const i = y * W + x;
        if (cv.mat[i] !== BASE) continue;
        if (Math.abs((x - x0) - (y - y0) * slope - off * k) < 0.55) cv.light[i] = cv.light[i] + 0.9;
      }
    }
  } else if (kind === "plates") {
    for (const yy of arange(y0 + 3, y1, (4 + (v % 3)) * Math.max(k, 0.7))) {
      const row = trunc(yy);
      for (let x = 0; x < W; x++) {
        const i = row * W + x;
        if (row >= 0 && row < W && cv.mat[i] === BASE) cv.light[i] = cv.light[i] - 1.2;
      }
    }
    for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) {
      if (cv.mat[y * W + x] === BASE && pyMod(x + v, 7) === 0 && pyMod(y, 5) === 2) cv.mat[y * W + x] = WHITE;
    }
  } else if (kind === "cracks" || kind === "circuits") {
    const dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    const n = 4 + (v % 3);
    for (let c = 0; c < n; c++) {
      let [x, y] = snapTo(...at(s.u(), 0.15 + 0.7 * s.u())).map(Number);
      const steps = trunc((6 + 6 * s.u()) * (0.5 + 0.5 * k));
      let dirn = 0;
      for (let st = 0; st < steps; st++) {
        const xi = trunc(x), yi = trunc(y);
        if (xi >= 0 && xi < W && yi >= 0 && yi < W && cv.mat[yi * W + xi] === BASE) {
          cv.mat[yi * W + xi] = GLOW;
          cv.flat[yi * W + xi] = 1;
        }
        if (kind === "circuits") {
          if (st % 3 === 0) dirn = trunc(s.u() * 4);
          x += dirs[dirn][0];
          y += dirs[dirn][1];
        } else {
          x = pyRound(x + s.u() * 2 - 1);
          y += s.u() < 0.6 ? 1 : 0;
        }
      }
    }
  } else if (kind === "stars") {
    for (let i = 0; i < 5 + (v % 6); i++) {
      const [x, y] = snapTo(...at(s.u(), s.u()));
      cv.mat[y * W + x] = GLOW;
      cv.flat[y * W + x] = 1;
    }
    const [wx, wy] = nonzeroMat(cv, (mat) => mat === ACCENT);
    if (wx.length) {
      for (let i = 0; i < trunc(4 + 2 * stage); i++) {
        const idx = trunc(s.u() * wx.length);
        cv.mat[wy[idx] * W + wx[idx]] = WHITE;
      }
    }
  }
  const [bxs, bys] = nonzeroMat(cv, (mat) => mat === BELLY);
  let cx, cy;
  if (bys.length > 10) {
    cy = trunc(median(bys));
    cx = trunc(median(bxs));
  } else {
    cx = trunc((x0 + x1) / 2);
    cy = trunc(y0 + 0.6 * (y1 - y0));
  }
  for (let b = 0; b < 5; b++) {
    if ((v >> b) & 1) {
      const x = cx - 2 + b;
      const y = cy - (b === 1 || b === 3 ? 1 : 0);
      if (x >= 0 && x < W && y >= 0 && y < W && (cv.mat[y * W + x] === BELLY || cv.mat[y * W + x] === BASE)) {
        cv.overlay.push([x, y, "glow"]);
      }
    }
  }
}

function sparkles(cv, gen, stage, px) {
  const s = new Stream(gen.seed, `sparkle${stage}`);
  const filled = new Uint8Array(W * W);
  let minx = W, maxx = -1, miny = W, maxy = -1, n = 0;
  for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) if (cv.mat[y * W + x] > 0) {
    filled[y * W + x] = 1; n++;
    if (x < minx) minx = x; if (x > maxx) maxx = x;
    if (y < miny) miny = y; if (y > maxy) maxy = y;
  }
  if (!n) return;
  const x0 = minx - 3, x1 = maxx + 3, y0 = miny - 3, y1 = maxy + 1;
  let placed = 0;
  const cap = stage === 3 ? 6 : 2;
  for (let attempt = 0; attempt < 60 && placed < cap; attempt++) {
    const x = trunc(x0 + s.u() * (x1 - x0));
    const y = trunc(y0 + s.u() * (y1 - y0));
    if (x >= 2 && x < W - 2 && y >= 2 && y < W - 4) {
      let hit = false;
      for (let yy = Math.max(0, y - 2); yy < Math.min(W, y + 3) && !hit; yy++) {
        for (let xx = Math.max(0, x - 2); xx < Math.min(W, x + 3); xx++) if (filled[yy * W + xx]) { hit = true; break; }
      }
      if (!hit) {
        const big = s.u() < 0.4;
        px.push([x, y, "spark"]);
        if (big) px.push([x - 1, y, "spark_dim"], [x + 1, y, "spark_dim"], [x, y - 1, "spark_dim"], [x, y + 1, "spark_dim"]);
        placed++;
      }
    }
  }
}

function shiftOf(src, dx, dy) {
  const out = new src.constructor(W * W);
  for (let y = 0; y < W; y++) {
    const sy = y - dy;
    if (sy < 0 || sy >= W) continue;
    for (let x = 0; x < W; x++) {
      const sx = x - dx;
      if (sx < 0 || sx >= W) continue;
      out[y * W + x] = src[sy * W + sx];
    }
  }
  return out;
}

function shade(cv, gen, px, layer, shadow) {
  const pal = palette(gen);
  const { mat, part, light, flat } = cv;
  const tone = new Int8Array(W * W);
  tone.fill(MID);
  const inner = new Uint8Array(W * W);
  for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    const nm = shiftOf(mat, dx, dy);
    const np = shiftOf(part, dx, dy);
    for (let i = 0; i < W * W; i++) {
      if (nm[i] > 0 && np[i] > part[i] && nm[i] !== EYE && nm[i] !== IRIS && nm[i] !== WHITE) inner[i] = 1;
    }
  }
  for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x;
    const th = BAYER[y % 4][x % 4];
    const L = light[i];
    let t = MID;
    // Threshold arrays are float64, so numpy promotes light before comparing.
    if (L > 0.36 + 0.24 * th) t = LIGHT;
    if (L > 0.80 + 0.30 * th) t = HI;
    if (L < -0.46 - 0.24 * th) t = SHADOW;
    if (L < -1.02 - 0.30 * th) t = DEEP;
    // A bare Python float is cast to float32 to match the light array.
    if (flat[i]) t = f32gt(L, 0.1) ? LIGHT : MID;
    if (inner[i] && mat[i] > 0 && mat[i] !== EYE && mat[i] !== IRIS) t = LINE;
    else inner[i] = 0;
    if (!(mat[i] > 0 && mat[i] !== EYE && mat[i] !== IRIS)) inner[i] = 0;
    tone[i] = t;
  }
  const lut = Array.from({ length: 16 }, () => Array.from({ length: 6 }, () => [0, 0, 0]));
  for (const key of [BASE, ALT, BELLY, ACCENT, DARK, GLOW, CHEEK, EYE, IRIS, WHITE, NOSE, BEAK]) {
    if (pal[key]) lut[key] = pal[key];
  }
  const img = new Uint8ClampedArray(W * W * 4);
  const filled = new Uint8Array(W * W);
  for (let i = 0; i < W * W; i++) {
    if (!(mat[i] > 0)) continue;
    filled[i] = 1;
    let c;
    if (mat[i] === EYE) c = NAVY;
    else if (mat[i] === IRIS) c = pal.iris;
    else if (mat[i] === WHITE) c = [248, 248, 248];
    else c = lut[mat[i]][tone[i]];
    const o = i * 4;
    img[o] = c[0]; img[o + 1] = c[1]; img[o + 2] = c[2]; img[o + 3] = 255;
  }
  const extR = shiftOf(filled, -1, 0);
  const extD = shiftOf(filled, 0, -1);
  const rc = pal.rim;
  for (let i = 0; i < W * W; i++) {
    const special = mat[i] === EYE || mat[i] === IRIS || mat[i] === WHITE;
    if (filled[i] && (extR[i] === 0 || extD[i] === 0) && f32lt(light[i], 0.15) && !special && !flat[i] && !inner[i]) {
      const o = i * 4;
      // Numpy casts 0.45 to float32 because the rim colour is a float32 scalar.
      const k = Math.fround(0.45);
      const blended = snap([
        trunc(0.55 * img[o] + k * Math.fround(rc[0])),
        trunc(0.55 * img[o + 1] + k * Math.fround(rc[1])),
        trunc(0.55 * img[o + 2] + k * Math.fround(rc[2])),
      ]);
      img[o] = blended[0]; img[o + 1] = blended[1]; img[o + 2] = blended[2];
    }
  }
  const oc = pal.outline;
  for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x;
    if (filled[i]) continue;
    const touch = (y > 0 && filled[i - W]) || (y + 1 < W && filled[i + W]) || (x > 0 && filled[i - 1]) || (x + 1 < W && filled[i + 1]);
    if (touch) {
      const o = i * 4;
      img[o] = oc[0]; img[o + 1] = oc[1]; img[o + 2] = oc[2]; img[o + 3] = 255;
    }
  }
  const cols = {
    white: [248, 248, 248],
    cheek: pal[CHEEK][MID],
    line: pal[DARK][LINE],
    mouth: pal[CHEEK][SHADOW],
    nose: pal[NOSE][MID],
    glow: pal[GLOW][LIGHT],
    glow_hi: [248, 248, 248],
    spark: pal[GLOW][LIGHT],
    spark_dim: pal[GLOW][MID],
  };
  for (const [x, y, kind] of cv.overlay.concat(px)) {
    if (x < 0 || x >= W || y < 0 || y >= W) continue;
    const i = y * W + x;
    if (kind.startsWith("spark") && img[i * 4 + 3] > 0) continue;
    if (kind === "cheek" && (mat[i] === EYE || mat[i] === IRIS || mat[i] === 0)) continue;
    const c = cols[kind];
    const o = i * 4;
    img[o] = c[0]; img[o + 1] = c[1]; img[o + 2] = c[2]; img[o + 3] = 255;
  }
  if (shadow && layer === "all") {
    const rows = [];
    for (let y = 0; y <= G; y++) {
      let hit = false;
      for (let x = 0; x < W; x++) if (img[(y * W + x) * 4 + 3] > 0) { hit = true; break; }
      if (hit) rows.push(y);
    }
    if (rows.length) {
      const low = rows[rows.length - 1];
      const yA = Math.max(0, low - 3);
      let cmin = W, cmax = -1;
      for (let x = 0; x < W; x++) {
        let hit = false;
        for (let y = yA; y <= low; y++) if (img[(y * W + x) * 4 + 3] > 0) { hit = true; break; }
        if (hit) { if (x < cmin) cmin = x; if (x > cmax) cmax = x; }
      }
      if (cmax >= 0) {
        const cx = (cmin + cmax) / 2;
        const half = Math.max(5, (cmax - cmin) / 2 + 2) * (cv.floatH ? 0.7 : 1);
        for (const [gy, frac, alpha] of [[G + 1, 1, 150], [G + 2, 0.82, 90]]) {
          if (gy >= W) continue;
          const a = trunc(cx - half * frac);
          const b = trunc(cx + half * frac);
          for (let gx = a; gx <= b; gx++) {
            if (gx >= 0 && gx < W && img[(gy * W + gx) * 4 + 3] === 0) {
              const o = (gy * W + gx) * 4;
              img[o] = 10; img[o + 1] = 14; img[o + 2] = 36; img[o + 3] = alpha;
            }
          }
        }
      }
    }
  }
  if (gen.facing === "left") {
    const flipped = new Uint8ClampedArray(img.length);
    for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) {
      const s = (y * W + x) * 4;
      const d = (y * W + (W - 1 - x)) * 4;
      flipped[d] = img[s]; flipped[d + 1] = img[s + 1]; flipped[d + 2] = img[s + 2]; flipped[d + 3] = img[s + 3];
    }
    return flipped;
  }
  return img;
}

const BAYER = [
  [0 / 16, 8 / 16, 2 / 16, 10 / 16],
  [12 / 16, 4 / 16, 14 / 16, 6 / 16],
  [3 / 16, 11 / 16, 1 / 16, 9 / 16],
  [15 / 16, 7 / 16, 13 / 16, 5 / 16],
];

export function renderSprite(genome, stage, options = {}) {
  const layer = options.layer ?? "all";
  const shadow = options.shadow === undefined ? true : options.shadow;
  const gen = options.eyes ? { ...genome, eye_style: options.eyes } : genome;
  const [cv, px] = build(gen, stage, layer, true);
  const rgba = shade(cv, gen, px, layer, shadow);
  return { width: 64, height: 64, rgba };
}
