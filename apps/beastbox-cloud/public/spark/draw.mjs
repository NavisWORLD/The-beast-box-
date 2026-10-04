/** 64x64 seeded sprite. Same genome fields as the Python generator; pixels are drawn in the browser. */

import { PALETTES } from "./genome.mjs";

const W = 64;

function hsv(h, s, v) {
  const hh = ((h % 360) + 360) % 360 / 60;
  const i = Math.floor(hh);
  const f = hh - i;
  const p = v * (1 - s);
  const q = v * (1 - f * s);
  const t = v * (1 - (1 - f) * s);
  const map = [[v, t, p], [q, v, p], [p, v, t], [p, q, v], [t, p, v], [v, p, q]];
  const [r, g, b] = map[i % 6];
  return [r, g, b].map((c) => Math.round(Math.max(0, Math.min(1, c)) * 255));
}

function snap(rgb) {
  return rgb.map((c) => Math.min(248, Math.round((c / 255) * 31) * 8));
}

function ramp(h, s, v) {
  const mid = snap(hsv(h, s, v));
  const sh = snap(hsv(h + 8, Math.min(1, s + 0.08), v * 0.62));
  const li = snap(hsv(h - 6, s * 0.75, Math.min(1, v * 1.18)));
  return { sh, mid, li };
}

export function paletteOf(gen) {
  const p = PALETTES[gen.island];
  const g = gen.genes;
  const dh = (g.hue - 0.5) * 28;
  const ds = (g.sat - 0.5) * 0.22;
  const dv = (g.val - 0.5) * 0.16;
  const adj = (t) => ramp(t[0] + dh, Math.max(0, Math.min(1, t[1] + ds)), Math.max(0.15, Math.min(1, t[2] + dv)));
  const glow = gen.glow === "native" ? p.glow : (gen.glow === "gold" ? [46, 0.85, 1] : [184, 0.8, 1]);
  return {
    base: adj(p.base), alt: adj(p.alt), belly: adj(p.belly), accent: adj(p.accent),
    glow: ramp(glow[0], glow[1] * 0.8, glow[2]),
    outline: [12, 16, 36],
    white: [240, 244, 248],
    dark: [18, 22, 40],
  };
}

function idx(x, y) { return (y * W + x) * 4; }

function inside(x, y) { return x >= 0 && y >= 0 && x < W && y < W; }

class Board {
  constructor() {
    this.mat = new Uint8Array(W * W);
    this.light = new Float32Array(W * W);
  }
  plot(x, y, mat, light) {
    x = Math.round(x); y = Math.round(y);
    if (!inside(x, y)) return;
    const i = y * W + x;
    this.mat[i] = mat;
    this.light[i] = light;
  }
  ell(cx, cy, rx, ry, mat) {
    rx = Math.max(0.8, rx); ry = Math.max(0.8, ry);
    const x0 = Math.max(0, Math.floor(cx - rx - 1));
    const x1 = Math.min(W - 1, Math.ceil(cx + rx + 1));
    const y0 = Math.max(0, Math.floor(cy - ry - 1));
    const y1 = Math.min(W - 1, Math.ceil(cy + ry + 1));
    for (let y = y0; y <= y1; y++) {
      for (let x = x0; x <= x1; x++) {
        const dx = (x + 0.5 - cx) / rx;
        const dy = (y + 0.5 - cy) / ry;
        if (dx * dx + dy * dy <= 1) this.plot(x, y, mat, -0.65 * dx - 0.85 * dy);
      }
    }
  }
  poly(pts, mat) {
    const xs = pts.map((p) => p[0]);
    const ys = pts.map((p) => p[1]);
    const x0 = Math.max(0, Math.floor(Math.min(...xs)));
    const x1 = Math.min(W - 1, Math.ceil(Math.max(...xs)));
    const y0 = Math.max(0, Math.floor(Math.min(...ys)));
    const y1 = Math.min(W - 1, Math.ceil(Math.max(...ys)));
    const cx = xs.reduce((a, b) => a + b, 0) / xs.length;
    const cy = ys.reduce((a, b) => a + b, 0) / ys.length;
    for (let y = y0; y <= y1; y++) {
      for (let x = x0; x <= x1; x++) {
        if (!pointInPoly(x + 0.5, y + 0.5, pts)) continue;
        const dx = (x - cx) / 8;
        const dy = (y - cy) / 8;
        this.plot(x, y, mat, -0.5 * dx - 0.8 * dy);
      }
    }
  }
}

function pointInPoly(x, y, pts) {
  let hit = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [xi, yi] = pts[i];
    const [xj, yj] = pts[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / ((yj - yi) || 1e-6) + xi) hit = !hit;
  }
  return hit;
}

const MAT = { base: 1, alt: 2, belly: 3, accent: 4, glow: 5, white: 6, dark: 7 };

function ear(board, kind, x, y, s, side) {
  if (kind === "pointy" || kind === "horns" || kind === "crown") {
    board.poly([[x - side * s * 0.35, y + 2], [x + side * s * 0.15, y - s * 1.3], [x + side * s * 0.55, y + 1]], kind === "horns" || kind === "crown" ? MAT.accent : MAT.base);
  } else if (kind === "round" || kind === "gills") {
    board.ell(x, y - s * 0.2, s * 0.45, s * 0.45, MAT.base);
  } else if (kind === "leaf" || kind === "antlers") {
    board.poly([[x, y + 2], [x - side * s * 0.7, y - s], [x + side * s * 0.15, y - s * 0.2]], MAT.accent);
  } else if (kind === "flame") {
    board.poly([[x - s * 0.3, y], [x, y - s * 1.4], [x + s * 0.35, y], [x, y + s * 0.2]], MAT.glow);
  } else if (kind === "crystal") {
    board.poly([[x, y + 2], [x - s * 0.35, y - s * 0.2], [x, y - s * 1.3], [x + s * 0.35, y - s * 0.2]], MAT.accent);
  } else if (kind === "antenna" || kind === "feelers" || kind === "bolts") {
    board.ell(x + side * s * 0.2, y - s, s * 0.22, s * 0.22, MAT.glow);
    board.ell(x, y, s * 0.18, s * 0.7, MAT.alt);
  }
}

function tail(board, kind, x, y, len, side) {
  if (kind === "none" || kind === "tip") return;
  if (kind === "fluffy" || kind === "plume") {
    board.ell(x + side * len * 0.35, y - len * 0.15, len * 0.28, len * 0.22, MAT.base);
    board.ell(x + side * len * 0.7, y - len * 0.45, len * 0.34, len * 0.3, kind === "plume" ? MAT.glow : MAT.belly);
  } else if (kind === "flame") {
    board.poly([[x, y], [x + side * len * 0.2, y - len * 0.3], [x + side * len * 0.85, y - len * 0.9], [x + side * len * 0.35, y]], MAT.glow);
  } else if (kind === "spade") {
    board.ell(x + side * len * 0.4, y - len * 0.2, len * 0.16, len * 0.16, MAT.base);
    board.poly([[x + side * len * 0.55, y], [x + side * len, y - len * 0.45], [x + side * len * 0.7, y + len * 0.15]], MAT.accent);
  } else if (kind === "fishtail" || kind === "fin") {
    board.poly([[x, y], [x + side * len, y - len * 0.45], [x + side * len * 0.7, y + len * 0.35]], MAT.accent);
  } else if (kind === "leaf") {
    board.poly([[x, y], [x + side * len * 0.8, y - len * 0.7], [x + side * len * 0.3, y + 2]], MAT.accent);
  } else if (kind === "crystal") {
    board.poly([[x, y], [x + side * len * 0.3, y - 2], [x + side * len, y - len * 0.4], [x + side * len * 0.2, y + 3]], MAT.accent);
  } else if (kind === "cable" || kind === "gear") {
    board.ell(x + side * len * 0.45, y - 2, len * 0.12, len * 0.12, MAT.alt);
    board.ell(x + side * len * 0.9, y - len * 0.25, kind === "gear" ? len * 0.28 : len * 0.16, len * 0.2, MAT.alt);
  }
}

function wing(board, kind, x, y, span, side) {
  if (!kind || kind === "none") return;
  if (kind === "feather" || kind === "leaf") {
    board.poly([[x, y], [x + side * span, y - span * 0.85], [x + side * span * 0.72, y + span * 0.15], [x + side * span * 0.2, y + 2]], kind === "leaf" ? MAT.accent : MAT.alt);
  } else if (kind === "bat" || kind === "moth") {
    board.poly([[x, y], [x + side * span * 0.95, y - span * 0.55], [x + side * span * 0.7, y + span * 0.35], [x + side * 2, y + span * 0.2]], MAT.accent);
  } else if (kind === "crystal" || kind === "vanes" || kind === "flame") {
    board.poly([[x, y], [x + side * span * 0.8, y - span * 0.7], [x + side * span * 0.45, y + span * 0.1]], kind === "flame" ? MAT.glow : MAT.accent);
  }
}

function bodyShape(board, gen, k) {
  const cx = 33;
  const feet = 56;
  const chub = 0.75 + gen.genes.chub * 0.7;
  const head = 0.85 + gen.genes.head * 0.45;
  const legs = gen.genes.legs;
  const pose = gen.pose;
  const side = pose === "side" ? 1 : 0;
  let hx = cx - side * 2;
  let hy = 30;
  let hr = 8 * k * head;
  if (gen.body === "pup") {
    board.ell(cx, feet - 10 * k, 11 * k * chub, 9 * k, MAT.base);
    hy = feet - 18 * k;
    board.ell(hx, hy, hr, hr * 0.95, MAT.base);
    board.ell(cx, feet - 7 * k, 6 * k, 5 * k, MAT.belly);
    for (const s of [-1, 1]) board.ell(cx + s * 7 * k, feet - 2, 2.2 * k, 2.4 + legs, MAT.base);
  } else if (gen.body === "fox") {
    board.ell(cx - 2, feet - 9 * k, 13 * k, 7 * k * chub, MAT.base);
    hx = cx + (pose === "front" ? 0 : 6 * k);
    hy = feet - 16 * k;
    hr = 7 * k * head;
    board.ell(hx, hy, hr * 1.15, hr, MAT.base);
    board.ell(hx + 6 * k, hy + 1, 4.2 * k, 2.4 * k, MAT.base);
    board.ell(cx - 4, feet - 6 * k, 5 * k, 4 * k, MAT.belly);
  } else if (gen.body === "sprout") {
    board.ell(cx, feet - 11 * k, 10 * k * chub, 11 * k, MAT.base);
    hy = feet - 20 * k; hr = 6.5 * k;
    board.ell(cx, hy, hr, hr, MAT.base);
    board.poly([[cx - 2, hy - hr], [cx, hy - hr - 10 * k], [cx + 3, hy - hr + 1]], MAT.accent);
  } else if (gen.body === "moth") {
    hy = 30; hr = 5 * k;
    board.ell(cx, 34, 4 * k, 8 * k, MAT.base);
    board.ell(cx, 22, hr, hr, MAT.base);
  } else if (gen.body === "axolotl") {
    board.ell(cx, feet - 10 * k, 12 * k * chub, 7 * k, MAT.base);
    hy = feet - 16 * k; hr = 8 * k;
    board.ell(cx, hy, hr * 1.2, hr * 0.8, MAT.base);
    board.ell(cx, feet - 8 * k, 5 * k, 3 * k, MAT.belly);
  } else if (gen.body === "golem") {
    board.poly([[cx - 10 * k, feet], [cx - 11 * k, feet - 16 * k], [cx + 11 * k, feet - 16 * k], [cx + 10 * k, feet]], MAT.alt);
    hy = feet - 22 * k; hr = 7 * k;
    board.poly([[cx - hr, hy + hr], [cx - hr, hy - hr], [cx + hr, hy - hr], [cx + hr, hy + hr]], MAT.base);
  } else if (gen.body === "dragonling") {
    board.ell(cx - 1, feet - 10 * k, 12 * k, 8 * k * chub, MAT.base);
    hx = cx + 5 * k; hy = feet - 18 * k; hr = 7 * k * head;
    board.ell(hx, hy, hr, hr * 0.9, MAT.base);
    board.ell(hx + 6 * k, hy + 1, 5 * k, 2.6 * k, MAT.base);
  } else if (gen.body === "bird") {
    board.ell(cx, feet - 12 * k, 8 * k * chub, 7 * k, MAT.base);
    hy = feet - 20 * k; hr = 6 * k;
    board.ell(cx + 2, hy, hr, hr * 0.9, MAT.base);
    board.poly([[cx + hr, hy], [cx + hr + 7 * k, hy + 1], [cx + hr, hy + 3]], MAT.accent);
  } else if (gen.body === "fish") {
    board.ell(cx, 34, 14 * k * chub, 8 * k, MAT.base);
    hy = 33; hx = cx + 6 * k; hr = 5 * k;
    board.ell(cx - 2, 36, 6 * k, 4 * k, MAT.belly);
  } else if (gen.body === "serpent") {
    board.ell(22, 40, 7 * k, 5 * k, MAT.base);
    board.ell(34, 34, 8 * k, 5.5 * k, MAT.base);
    board.ell(46, 30, 6 * k, 5 * k, MAT.base);
    hx = 48; hy = 28; hr = 5.5 * k;
  } else {
    board.poly([[cx - 6 * k, feet], [cx - 7 * k, feet - 12 * k], [cx + 7 * k, feet - 12 * k], [cx + 6 * k, feet]], MAT.base);
    hy = feet - 20 * k; hr = 6.5 * k * head;
    board.ell(cx, hy, hr, hr, MAT.base);
    board.ell(cx, feet - 8 * k, 4 * k, 4 * k, MAT.belly);
    if (pose === "three_quarter") hx = cx + 2;
  }
  return { hx, hy, hr };
}

function pattern(board, gen, hx, hy, hr) {
  const n = 2 + Math.round(gen.genes.pattern_density * 4);
  const scale = 1.2 + gen.genes.pattern_scale * 2.2;
  for (let i = 0; i < n; i++) {
    const ang = (i / n) * Math.PI * 2 + gen.pattern_variant;
    const x = hx + Math.cos(ang) * hr * 0.45;
    const y = hy + 6 + Math.sin(ang) * hr * 0.35;
    if (gen.pattern === "stripes" || gen.pattern === "circuits") board.ell(x, y, scale * 2.2, 0.7, MAT.alt);
    else if (gen.pattern === "belly") board.ell(hx, hy + hr * 0.8, hr * 0.55, hr * 0.4, MAT.belly);
    else board.ell(x, y, scale * 0.7, scale * 0.55, gen.pattern === "stars" ? MAT.glow : MAT.accent);
  }
}

function glyph(board, x, y, bits) {
  for (let i = 0; i < 5; i++) {
    if ((bits >> i) & 1) board.plot(x + i - 2, y, MAT.glow, 1);
    else board.plot(x + i - 2, y, MAT.dark, -0.2);
  }
}

function eyes(pix, pal, hx, hy, hr, style, state, gap) {
  const spread = hr * (0.35 + gap * 0.25);
  for (const side of [-1, 1]) {
    const ex = hx + side * spread;
    const ey = hy - hr * 0.05;
    const er = Math.max(2, hr * 0.28);
    if (state === "closed") {
      for (let x = -er; x <= er; x++) put(pix, ex + x, ey, pal.dark);
      continue;
    }
    const ry = state === "sleepy" ? er * 0.45 : er;
    for (let y = -ry; y <= ry; y++) {
      for (let x = -er; x <= er; x++) {
        if ((x / er) ** 2 + (y / ry) ** 2 <= 1) put(pix, ex + x, ey + y, pal.white);
      }
    }
    if (state !== "sleepy") {
      const iris = style === "sparkle" || state === "sparkle" ? pal.glow.li : pal.accent.mid;
      put(pix, ex + 0.4, ey + 0.2, iris);
      put(pix, ex + 1, ey + 0.6, pal.dark);
      if (style === "sparkle" || state === "sparkle") put(pix, ex - 0.6, ey - 0.6, pal.white);
    }
  }
}

function put(pix, x, y, rgb) {
  x = Math.round(x); y = Math.round(y);
  if (!inside(x, y)) return;
  const i = idx(x, y);
  pix[i] = rgb[0]; pix[i + 1] = rgb[1]; pix[i + 2] = rgb[2]; pix[i + 3] = 255;
}

function shade(board, pix, pal) {
  const mats = { 1: pal.base, 2: pal.alt, 3: pal.belly, 4: pal.accent, 5: pal.glow, 6: { sh: pal.white, mid: pal.white, li: pal.white }, 7: { sh: pal.dark, mid: pal.dark, li: pal.dark } };
  for (let i = 0; i < board.mat.length; i++) {
    const m = board.mat[i];
    if (!m) continue;
    const tone = mats[m];
    const L = board.light[i];
    const rgb = L > 0.35 ? tone.li : L < -0.25 ? tone.sh : tone.mid;
    const o = i * 4;
    pix[o] = rgb[0]; pix[o + 1] = rgb[1]; pix[o + 2] = rgb[2]; pix[o + 3] = 255;
  }
  for (let y = 0; y < W; y++) {
    for (let x = 0; x < W; x++) {
      const i = y * W + x;
      if (board.mat[i]) continue;
      let edge = false;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const xx = x + dx, yy = y + dy;
        if (inside(xx, yy) && board.mat[yy * W + xx]) edge = true;
      }
      if (edge) put(pix, x, y, pal.outline);
    }
  }
}

export function renderBeast(gen, stage = 2, eye = "open") {
  const board = new Board();
  const k = stage === 1 ? 0.62 : stage === 3 ? 1.05 : 0.84;
  const span = (8 + 14 * gen.genes.wing_size) * k * (stage === 1 ? 0.7 : 1);
  if (gen.wings !== "none") {
    wing(board, gen.wings, 30, 34, span, -1);
    wing(board, gen.wings, 36, 34, span, 1);
  }
  const anchor = bodyShape(board, gen, k);
  const len = (10 + 10 * gen.genes.tail_size) * k;
  const side = gen.pose === "side" ? 1 : -1;
  tail(board, gen.tail, anchor.hx - side * anchor.hr, anchor.hy + anchor.hr * 0.4, len, side);
  const es = (4 + 5 * gen.genes.ear_size) * k;
  if (gen.pose !== "side") {
    ear(board, gen.ears, anchor.hx - anchor.hr * 0.55, anchor.hy - anchor.hr * 0.7, es, -1);
    ear(board, gen.ears, anchor.hx + anchor.hr * 0.55, anchor.hy - anchor.hr * 0.7, es, 1);
  } else ear(board, gen.ears, anchor.hx, anchor.hy - anchor.hr, es, 1);
  pattern(board, gen, anchor.hx, anchor.hy, anchor.hr);
  glyph(board, anchor.hx, anchor.hy + anchor.hr * 0.9, gen.pattern_variant);
  if (stage === 3) {
    board.plot(anchor.hx - 8, anchor.hy - 10, MAT.glow, 1);
    board.plot(anchor.hx + 9, anchor.hy - 6, MAT.glow, 1);
  }
  const pal = paletteOf(gen);
  const pix = new Uint8ClampedArray(W * W * 4);
  shade(board, pix, pal);
  const eyeState = eye === "open" ? (gen.eye_style === "sleepy" ? "sleepy" : gen.eye_style === "sparkle" ? "sparkle" : "open") : eye;
  eyes(pix, pal, anchor.hx, anchor.hy, anchor.hr, gen.eye_style, eyeState, gen.genes.eye_gap);
  if (gen.facing === "left") mirror(pix);
  return pix;
}

function mirror(pix) {
  for (let y = 0; y < W; y++) {
    for (let x = 0; x < W / 2; x++) {
      const a = idx(x, y);
      const b = idx(W - 1 - x, y);
      for (let c = 0; c < 4; c++) {
        const tmp = pix[a + c];
        pix[a + c] = pix[b + c];
        pix[b + c] = tmp;
      }
    }
  }
}

export function blit(ctx, pix, dx, dy, scale = 4) {
  const canvas = ctx.canvas;
  const tmp = document.createElement("canvas");
  tmp.width = W; tmp.height = W;
  const tctx = tmp.getContext("2d");
  const img = new ImageData(pix, W, W);
  tctx.putImageData(img, 0, 0);
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(tmp, dx, dy, W * scale, W * scale);
}

export const SPRITE = W;
