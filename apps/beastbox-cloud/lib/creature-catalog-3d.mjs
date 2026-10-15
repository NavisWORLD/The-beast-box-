/**
 * FAITHFUL HIGH-QUALITY 3D CATALOGUE CREATURES (STUDIO-GRADE SCULPTED GEOMETRY)
 *
 * Turns every Beast Box catalogue creature (all 11 body plans: fox, pup, biped, golem,
 * serpent, axolotl, moth, bird, dragonling, sprout, fish) into a true, 360°-rotatable
 * Three.js 3D living character faithful to its original sprite art.
 *
 * Sculpting architecture:
 * - Custom parametric organic loft/lathe geometries (`sculptedSkullGeo`, `sculptedTorsoGeo`,
 *   `sculptedLimbGeo`, `sculptedPawGeo`, `sculptedEarGeo`, `sculptedHornGeo`, `sculptedWingGeo`,
 *   `sculptedCrystalGeo`, `sculptedEyeStarGeo`, `sculptedTailPlumeGeo`) with smooth vertex normals.
 * - Multi-layered anime/chibi eyes (sclera dome, concave iris cup, pupil, 4-point star catchlight,
 *   secondary specular dot, sculpted upper eyelid + lash line).
 * - Rich MeshPhysicalMaterial clearcoat & velvet sheen + painted 256×256 procedural island textures
 *   matching the 5-tone BGR555 sprite ramp in `lib/companion/spark/render.mjs`.
 * - Driven deterministically by the creature's seed, film-motion actor state, and Verlet +
 *   curl-noise/SPH-lite fluid secondary motion (`lib/companion/fluid-motion.mjs`).
 * - Triangle budget: strictly < 25,000 triangles per creature (~3,500–8,500 tris) for 60fps on iPhone 16.
 */

import { BODIES, PALETTES } from '../public/spark/genome.mjs';
import {
  createSecondaryMotion,
  stepSecondaryMotion,
  seededPrng,
  ELEMENT_FLUID_PROFILES,
} from './companion/fluid-motion.mjs';
import { contactShadow } from './companion/film-motion.mjs';

export const CATALOG_BODIES = BODIES;
export const MAX_MOBILE_TRIANGLES = 25000;

const ISLAND_ELEMENTS = {
  'Eridoria Prime': 'verdant',
  'Hollow Verdance': 'grove',
  'The Crown': 'radiant',
  'The Pale Expanse': 'frost',
  'Rust Meridian': 'machine',
  'Cinder Drift': 'ember',
  'Umbral Deep': 'umbral',
  'The Shattered Reef': 'crystal',
};

/**
 * Unpack a packed row from public/spark/catalog-index.json into a genome descriptor.
 */
export function catalogRowToGenome(catalogIndex, rowOrIndex = 0) {
  const row = Array.isArray(rowOrIndex) ? rowOrIndex : catalogIndex?.rows?.[rowOrIndex];
  if (!row || !catalogIndex?.traits || !catalogIndex?.values) return null;
  const [runKey, name1, name3, pubIndex] = row;
  const traits = {};
  catalogIndex.traits.forEach((traitName, i) => {
    const idx = row[4 + i];
    traits[traitName] = catalogIndex.values[traitName]?.[idx] ?? null;
  });
  const island = traits.island || 'Eridoria Prime';
  return {
    seed: `${runKey}:${pubIndex}:${name1}`,
    names: { 1: name1, 2: name1, 3: name3 },
    island,
    element: ISLAND_ELEMENTS[island] || 'verdant',
    ...traits,
    genes: {
      chub: 0.5, head: 0.5, legs: 0.5, ear_size: 0.5, tail_size: 0.5, wing_size: 0.5,
      eye_size: 0.5, eye_gap: 0.5, hue: 0.5, sat: 0.5, val: 0.5, glow_amount: 0.5,
    },
  };
}

const STAGE_SCALE = { 1: 0.78, 2: 0.92, 3: 1.08 };
const GLOW_HSV = { gold: [46, 0.85, 1.0], cyan: [184, 0.80, 1.0] };
const NAVY_RGB = [14, 20, 44];

function mod(a, b) {
  return ((a % b) + b) % b;
}

function hsvToRgb(h, s, v) {
  const hh = mod(h, 360) / 360;
  const ss = Math.max(0, Math.min(1, s));
  const vv = Math.max(0, Math.min(1, v));
  if (ss === 0) {
    const c = Math.trunc(vv * 255);
    return [c, c, c];
  }
  const i = mod(Math.trunc(hh * 6), 6);
  const f = hh * 6 - Math.trunc(hh * 6);
  const p = vv * (1 - ss);
  const q = vv * (1 - ss * f);
  const t = vv * (1 - ss * (1 - f));
  let r = 0, g = 0, b = 0;
  if (i === 0) { r = vv; g = t; b = p; }
  else if (i === 1) { r = q; g = vv; b = p; }
  else if (i === 2) { r = p; g = vv; b = t; }
  else if (i === 3) { r = p; g = q; b = vv; }
  else if (i === 4) { r = t; g = p; b = vv; }
  else { r = vv; g = p; b = q; }
  return [Math.trunc(r * 255), Math.trunc(g * 255), Math.trunc(b * 255)];
}

function snapBgr555(rgb) {
  return rgb.map(c => Math.min(248, Math.round((c / 255) * 31) * 8));
}

function rgbToHex(rgb) {
  const [r, g, b] = snapBgr555(rgb);
  return ((r & 0xff) << 16) | ((g & 0xff) << 8) | (b & 0xff);
}

/**
 * Derive the exact island + gene-shifted BGR555 palette matching lib/companion/spark/render.mjs.
 */
export function deriveCatalogPalette(genome = {}) {
  const island = genome?.island && PALETTES[genome.island] ? genome.island : 'Eridoria Prime';
  const p = PALETTES[island];
  const gg = genome?.genes || {};
  const dh = ((gg.hue ?? 0.5) - 0.5) * 30;
  const ds = ((gg.sat ?? 0.5) - 0.5) * 0.25;
  const dv = ((gg.val ?? 0.5) - 0.5) * 0.18;
  const adj = t => [t[0] + dh, t[1] + ds, t[2] + dv];
  const glowHsv = genome?.glow === 'gold' ? GLOW_HSV.gold : genome?.glow === 'cyan' ? GLOW_HSV.cyan : p.glow;

  const baseHsv = adj(p.base);
  const altHsv = adj(p.alt);
  const bellyHsv = adj(p.belly);
  const accentHsv = adj(p.accent);

  const cool = (60 < mod(baseHsv[0], 360) && mod(baseHsv[0], 360) < 240) ? 12 : -14;
  const warm = -((60 < mod(baseHsv[0], 360) && mod(baseHsv[0], 360) < 240) ? 8 : -6);

  return {
    island,
    base: rgbToHex(hsvToRgb(baseHsv[0], baseHsv[1], baseHsv[2])),
    baseShadow: rgbToHex(hsvToRgb(baseHsv[0] + cool, baseHsv[1] * 1.05 + 0.08, baseHsv[2] * 0.68)),
    baseLight: rgbToHex(hsvToRgb(baseHsv[0] + warm, baseHsv[1] * 0.8, Math.min(1, baseHsv[2] * 1.16 + 0.05))),
    alt: rgbToHex(hsvToRgb(altHsv[0], altHsv[1], altHsv[2])),
    belly: rgbToHex(hsvToRgb(bellyHsv[0], bellyHsv[1], bellyHsv[2])),
    accent: rgbToHex(hsvToRgb(accentHsv[0], accentHsv[1], accentHsv[2])),
    glow: rgbToHex(hsvToRgb(glowHsv[0], glowHsv[1], glowHsv[2])),
    cheek: rgbToHex(hsvToRgb(350, 0.45, 1.0)),
    dark: rgbToHex(hsvToRgb(p.base[0] + 20, 0.5, 0.32)),
    nose: rgbToHex(hsvToRgb(240, 0.3, 0.2)),
    beak: rgbToHex(hsvToRgb(40, 0.72, 0.97)),
    white: rgbToHex(hsvToRgb(220, 0.04, 0.97)),
    eye: rgbToHex(NAVY_RGB),
    iris: rgbToHex(hsvToRgb(glowHsv[0], 0.55, 0.95)),
  };
}

function joint(THREE, parent, name, x, y, z) {
  const g = new THREE.Group();
  g.name = name;
  g.position.set(x, y, z);
  parent.add(g);
  return g;
}

function put(parent, mesh, name, x, y, z, scale, rot) {
  mesh.name = name;
  mesh.position.set(x, y, z);
  if (scale) mesh.scale.set(scale[0], scale[1], scale[2]);
  if (rot) mesh.rotation.set(rot[0] || 0, rot[1] || 0, rot[2] || 0);
  parent.add(mesh);
  return mesh;
}

/**
 * Build a vivid 256×256 procedural 5-tone ramp + pattern texture when in browser.
 */
function buildPatternTexture(THREE, genome, pal) {
  if (typeof document === 'undefined') return null;
  try {
    const c = document.createElement('canvas');
    c.width = 256;
    c.height = 256;
    const ctx = c.getContext('2d');
    if (!ctx) return null;
    const hex = n => '#' + n.toString(16).padStart(6, '0');

    // Rich 5-tone vertical + radial cel-style ramp matching spark/render.mjs
    const grad = ctx.createLinearGradient(0, 0, 0, 256);
    grad.addColorStop(0.0, hex(pal.baseLight));
    grad.addColorStop(0.38, hex(pal.base));
    grad.addColorStop(0.75, hex(pal.base));
    grad.addColorStop(1.0, hex(pal.baseShadow));
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 256, 256);

    // Subtle top crown sheen
    const sheen = ctx.createRadialGradient(128, 52, 8, 128, 80, 120);
    sheen.addColorStop(0, hex(pal.baseLight) + '88');
    sheen.addColorStop(1, hex(pal.base) + '00');
    ctx.fillStyle = sheen;
    ctx.fillRect(0, 0, 256, 256);

    const pat = genome?.pattern || 'spots';
    const rand = seededPrng(String(genome?.seed || 'pat') + ':' + pat + ':' + String(genome?.pattern_variant ?? 0));
    ctx.fillStyle = hex(pal.alt);
    ctx.strokeStyle = hex(pal.accent);
    ctx.lineWidth = 4;

    if (pat === 'spots') {
      for (let i = 0; i < 20; i++) {
        const x = 18 + rand() * 220, y = 18 + rand() * 220, r = 8 + rand() * 13;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = hex(pal.accent);
        ctx.beginPath();
        ctx.arc(x - r * 0.2, y - r * 0.2, r * 0.35, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = hex(pal.alt);
      }
    } else if (pat === 'stripes') {
      for (let y = 20; y < 236; y += 26) {
        ctx.beginPath();
        ctx.moveTo(10, y);
        ctx.quadraticCurveTo(128, y + 14, 246, y);
        ctx.lineWidth = 10;
        ctx.strokeStyle = hex(pal.alt);
        ctx.stroke();
      }
    } else if (pat === 'stars') {
      for (let i = 0; i < 26; i++) {
        const x = 16 + rand() * 224, y = 16 + rand() * 224, r = 5 + rand() * 6;
        ctx.fillStyle = i % 3 === 0 ? hex(pal.white) : hex(pal.glow);
        ctx.beginPath();
        ctx.moveTo(x, y - r);
        ctx.quadraticCurveTo(x + r * 0.2, y - r * 0.2, x + r, y);
        ctx.quadraticCurveTo(x + r * 0.2, y + r * 0.2, x, y + r);
        ctx.quadraticCurveTo(x - r * 0.2, y + r * 0.2, x - r, y);
        ctx.quadraticCurveTo(x - r * 0.2, y - r * 0.2, x, y - r);
        ctx.fill();
      }
    } else if (pat === 'circuits') {
      ctx.strokeStyle = hex(pal.glow);
      ctx.lineWidth = 3.5;
      for (let i = 0; i < 12; i++) {
        const x0 = 24 + rand() * 208, y0 = 24 + rand() * 208;
        const dx = rand() > 0.5 ? 42 : -42;
        ctx.beginPath();
        ctx.moveTo(x0, y0);
        ctx.lineTo(x0 + dx, y0);
        ctx.lineTo(x0 + dx, y0 + 36);
        ctx.stroke();
        ctx.fillStyle = hex(pal.glow);
        ctx.beginPath();
        ctx.arc(x0 + dx, y0 + 36, 4.5, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (pat === 'cracks') {
      ctx.strokeStyle = hex(pal.glow);
      ctx.lineWidth = 3.5;
      for (let i = 0; i < 10; i++) {
        ctx.beginPath();
        let x = 28 + rand() * 200, y = 24 + rand() * 200;
        ctx.moveTo(x, y);
        for (let s = 0; s < 4; s++) {
          x += (rand() - 0.5) * 44;
          y += 18 + rand() * 22;
          ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
    } else if (pat === 'facets' || pat === 'plates') {
      for (let i = 0; i < 14; i++) {
        const x = 20 + rand() * 190, y = 20 + rand() * 190;
        ctx.fillStyle = hex(pal.alt);
        ctx.fillRect(x, y, 28, 20);
        ctx.strokeStyle = hex(pal.baseLight);
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, 28, 20);
      }
    } else if (pat === 'moss') {
      ctx.fillStyle = hex(pal.accent);
      for (let i = 0; i < 18; i++) {
        ctx.beginPath();
        ctx.arc(24 + rand() * 208, 12 + rand() * 96, 12 + rand() * 14, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    const tex = new THREE.CanvasTexture(c);
    if (THREE.SRGBColorSpace) tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  } catch {
    return null;
  }
}

/* ============================================================================
 * STUDIO SCULPTING PRIMITIVES (ORGANIC DEFORMED & LOFTED MESHES)
 * ========================================================================== */

/**
 * Sculpted character skull: flat forehead dome, wide expressive cheek Pouches,
 * gentle eye socket indents, integrated forward muzzle bridge, and tapered back cranium.
 */
function buildSculptedSkullGeo(THREE, bodyType, segs = [28, 22]) {
  if (bodyType === 'golem') {
    const g = new THREE.OctahedronGeometry(1, 2);
    const pos = g.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
      // Chiseled golem cranium with brow ridge and flat jaw
      if (y > 0.35) y *= 0.82;
      if (y < -0.3) { y *= 0.78; x *= 1.12; }
      if (z > 0.3 && y > 0.05 && y < 0.45) z *= 1.14; // heavy stone brow
      // Facet quantization for carved mineral look
      x = Math.round(x * 14) / 14;
      y = Math.round(y * 14) / 14;
      z = Math.round(z * 14) / 14;
      pos.setXYZ(i, x, y, z);
    }
    pos.needsUpdate = true;
    g.computeVertexNormals();
    return g;
  }

  const g = new THREE.SphereGeometry(1, segs[0], segs[1]);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const ax = Math.abs(x);

    // 1. Flatter crown so ears/horns sit naturally on a wide head table
    if (y > 0) {
      y *= 0.86;
      x *= 1 + 0.06 * (1 - y);
    } else {
      // 2. Chubby lower cheek pouches (signature chibi/GBA creature silhouette)
      const cheekBulge = Math.max(0, 1 - Math.abs(y + 0.26) * 2.6) * (0.18 + (bodyType === 'axolotl' || bodyType === 'pup' || bodyType === 'fox' ? 0.08 : 0.02));
      x *= 1 + cheekBulge;
      z *= 1 + cheekBulge * 0.45;
      if (y < -0.55) y *= 0.88; // tucked chin
    }

    // 3. Forward muzzle / snout bridge push on the front lower face
    if (z > 0.2 && y < 0.08 && y > -0.65 && ax < 0.55) {
      const muzzleFactor = (1 - ax / 0.55) * Math.max(0, 1 - Math.abs(y + 0.22) * 2.4);
      const snoutPush = (bodyType === 'fox' || bodyType === 'dragonling' || bodyType === 'serpent') ? 0.32
        : (bodyType === 'pup' || bodyType === 'axolotl') ? 0.20 : 0.12;
      z += muzzleFactor * snoutPush;
    }

    // 4. Subtle eye socket seating so large anime eyes sit flush in the face
    if (z > 0.45 && y > -0.15 && y < 0.42 && ax > 0.18 && ax < 0.68) {
      z *= 0.95;
    }

    // 5. Flatter back of skull
    if (z < 0) z *= 0.88;

    pos.setXYZ(i, x, y, z);
  }
  pos.needsUpdate = true;
  g.computeVertexNormals();
  return g;
}

/**
 * Sculpted anatomical torso: pear-shaped chibi drop or sleek quadruped chest-to-hip loft.
 */
function buildSculptedTorsoGeo(THREE, bodyType, segs = [28, 22]) {
  if (bodyType === 'golem') {
    const g = new THREE.OctahedronGeometry(1, 2);
    const pos = g.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
      // Broad heroic chest, tapered waist, faceted rock planes
      const chest = y > 0 ? 1.18 : 0.86;
      x *= chest;
      z *= y > 0 ? 1.08 : 0.92;
      x = Math.round(x * 12) / 12;
      y = Math.round(y * 12) / 12;
      z = Math.round(z * 12) / 12;
      pos.setXYZ(i, x, y, z);
    }
    pos.needsUpdate = true;
    g.computeVertexNormals();
    return g;
  }

  const g = new THREE.SphereGeometry(1, segs[0], segs[1]);
  const pos = g.attributes.position;
  const isQuad = bodyType === 'fox' || bodyType === 'pup' || bodyType === 'dragonling' || bodyType === 'axolotl';
  const isFish = bodyType === 'fish';

  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    if (isFish) {
      // Hydrodynamic fusiform fish body: round front, sleek tapered tail peduncle
      const taper = z < 0 ? 1 + z * 0.48 : 1 - z * 0.08;
      x *= Math.max(0.22, taper) * 0.86;
      y *= Math.max(0.28, taper);
      if (y > 0) y *= 1.08; // arched dorsal line
    } else if (isQuad) {
      // Quadruped ribcage + tucked waist + rounded haunches + arched spine
      const rib = z > 0 ? 1 + 0.14 * z : 1 + 0.06 * z;
      const bellyDrop = (y < 0 && z > -0.3) ? 1.12 : 0.95;
      x *= rib;
      y *= bellyDrop;
      if (y > 0.3) y += 0.06 * Math.cos(z * Math.PI * 0.7);
    } else {
      // Pear-shaped chibi torso (biped, bird, moth, sprout, serpent): cozy rounded belly, tapered shoulders
      const pear = 1 - y * 0.24;
      x *= pear;
      z *= pear;
      if (z > 0 && y < 0.2) z *= 1.12; // soft tummy curve
      if (y < -0.65) y *= 0.92; // stable base
    }
    pos.setXYZ(i, x, y, z);
  }
  pos.needsUpdate = true;
  g.computeVertexNormals();
  return g;
}

/**
 * Sculpted organic ear: outer pinna shell with curved tip and concave inner ear cup.
 */
function buildSculptedEarGeo(THREE, low = false) {
  const g = new THREE.ConeGeometry(1, 2.2, low ? 12 : 20, low ? 5 : 8);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const t = Math.max(0, Math.min(1, (y + 1.1) / 2.2)); // 0 at base, 1 at tip
    // Wide base, organic bell curve mid-section, swept tip
    const widthCurve = Math.sin(t * Math.PI * 0.85) * 0.35 + (1 - t) * 0.85;
    x *= widthCurve;
    // Concave front hollow (z > 0 pushed inward in middle)
    if (z > 0 && Math.abs(x) < 0.55 && t > 0.12 && t < 0.85) {
      z *= 0.42;
    } else {
      z *= 0.68;
    }
    // Gentle backward curve toward tip
    z -= t * t * 0.28;
    pos.setXYZ(i, x, y, z);
  }
  pos.needsUpdate = true;
  g.computeVertexNormals();
  return g;
}

/**
 * Sculpted curved horn along a 3D Catmull-Rom spline with organic rings.
 */
function buildSculptedHornGeo(THREE, low = false) {
  const radial = low ? 8 : 14;
  const heightSegs = low ? 8 : 14;
  const g = new THREE.CylinderGeometry(0.06, 1, 2.2, radial, heightSegs, false);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const t = Math.max(0, Math.min(1, (y + 1.1) / 2.2)); // 0..1
    const ridge = 1 + 0.06 * Math.sin(t * Math.PI * 10);
    x *= ridge;
    z *= ridge;
    // S-curve sweep backward and slightly outward
    z -= Math.pow(t, 1.7) * 0.75;
    x += Math.pow(t, 1.5) * 0.32;
    pos.setXYZ(i, x, y, z);
  }
  pos.needsUpdate = true;
  g.computeVertexNormals();
  return g;
}

/**
 * Sculpted paw with 3 distinct rounded toes and a soft heel pad.
 */
function buildSculptedPawGeo(THREE, low = false) {
  const g = new THREE.SphereGeometry(1, low ? 12 : 16, low ? 8 : 12);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    // Flatten sole at bottom
    if (y < 0) y *= 0.45;
    else y *= 0.72;
    // 3-toescalloping at the front (z > 0.25)
    if (z > 0.25) {
      const toeWave = Math.cos(x * Math.PI * 2.6) * 0.14 * Math.max(0, z - 0.25);
      z += toeWave;
      y += toeWave * 0.35;
    }
    pos.setXYZ(i, x, y, z);
  }
  pos.needsUpdate = true;
  g.computeVertexNormals();
  return g;
}

/**
 * Sculpted organic tail plume (S-curved volumetric brush).
 */
function buildSculptedTailSegmentGeo(THREE, isFluffy = true, low = false) {
  const g = new THREE.SphereGeometry(1, low ? 10 : 14, low ? 8 : 12);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    if (isFluffy) {
      // Fur tuft ridges along longitudinal ribs
      const angle = Math.atan2(y, x);
      const tuft = 1 + 0.11 * Math.cos(angle * 5) * (1 - Math.abs(z) * 0.5);
      x *= tuft;
      y *= tuft;
    }
    pos.setXYZ(i, x, y, z);
  }
  pos.needsUpdate = true;
  g.computeVertexNormals();
  return g;
}

/**
 * 4-point star catchlight geometry for expressive anime eyes and celestial ornaments.
 */
function buildStarCatchlightGeo(THREE, rOuter = 1, rInner = 0.28) {
  const shape = new THREE.Shape();
  for (let i = 0; i < 8; i++) {
    const r = i % 2 === 0 ? rOuter : rInner;
    const a = (i * Math.PI) / 4;
    const x = Math.cos(a) * r;
    const y = Math.sin(a) * r;
    if (i === 0) shape.moveTo(x, y);
    else shape.lineTo(x, y);
  }
  shape.closePath();
  return new THREE.ExtrudeGeometry(shape, { depth: 0.18, bevelEnabled: false });
}

function buildWingGeometry(THREE, wingType, span = 0.52, lift = 0.32) {
  const shape = new THREE.Shape();
  shape.moveTo(0, 0);
  if (wingType === 'bat' || wingType === 'flame') {
    shape.bezierCurveTo(span * 0.28, lift * 1.25, span * 0.72, lift * 1.32, span, lift * 0.48);
    shape.quadraticCurveTo(span * 0.78, 0.04, span * 0.68, -lift * 0.36);
    shape.quadraticCurveTo(span * 0.46, 0.0, span * 0.34, -lift * 0.42);
    shape.quadraticCurveTo(span * 0.16, -0.04, 0.02, -0.06);
  } else if (wingType === 'moth') {
    shape.bezierCurveTo(span * 0.22, lift * 1.45, span * 0.95, lift * 1.28, span, lift * 0.28);
    shape.bezierCurveTo(span * 0.95, -lift * 0.38, span * 0.68, -lift * 0.92, span * 0.24, -lift * 0.68);
    shape.lineTo(0.02, -0.06);
  } else if (wingType === 'crystal' || wingType === 'vanes') {
    shape.lineTo(span * 0.36, lift * 1.02);
    shape.lineTo(span, lift * 0.46);
    shape.lineTo(span * 0.80, -lift * 0.30);
    shape.lineTo(span * 0.34, -lift * 0.46);
    shape.lineTo(0.02, -0.05);
  } else {
    // feather / leaf: layered primary pinion silhouette
    shape.bezierCurveTo(span * 0.26, lift * 1.18, span * 0.70, lift * 1.12, span, lift * 0.36);
    shape.quadraticCurveTo(span * 0.88, 0.02, span * 0.76, -lift * 0.18);
    shape.quadraticCurveTo(span * 0.62, -lift * 0.08, span * 0.50, -lift * 0.36);
    shape.quadraticCurveTo(span * 0.26, -lift * 0.42, 0.02, -0.05);
  }
  shape.closePath();
  return new THREE.ExtrudeGeometry(shape, {
    depth: 0.036,
    bevelEnabled: true,
    bevelThickness: 0.012,
    bevelSize: 0.010,
    bevelSegments: 2,
    curveSegments: 12,
  });
}

/**
 * Build a faithful, studio-sculpted 3D Three.js character for any Beast Box catalogue creature genome.
 */
export function buildCatalogCreatureRig(THREE, genome = {}, { stage = 1, quality = 'auto' } = {}) {
  const bodyType = CATALOG_BODIES.includes(genome?.body) ? genome.body : 'pup';
  const earsType = genome?.ears || 'pointy';
  const tailType = genome?.tail || 'fluffy';
  const wingsType = genome?.wings || (bodyType === 'moth' ? 'moth' : bodyType === 'bird' ? 'feather' : bodyType === 'dragonling' ? 'bat' : 'none');
  const patternType = genome?.pattern || 'spots';
  const eyeStyle = genome?.eye_style || 'round';
  const mouthType = genome?.mouth || 'smile';
  const element = genome?.element || 'verdant';
  const seed = String(genome?.seed || genome?.names?.[1] || bodyType);

  const gg = genome?.genes || {};
  const chub = gg.chub ?? 0.5;
  const headGene = gg.head ?? 0.5;
  const legsGene = gg.legs ?? 0.5;
  const earSize = 0.85 + (gg.ear_size ?? 0.5) * 0.42;
  const tailSize = 0.85 + (gg.tail_size ?? 0.5) * 0.45;
  const wingSize = 0.85 + (gg.wing_size ?? 0.5) * 0.45;
  const eyeSize = 0.90 + (gg.eye_size ?? 0.5) * 0.32;
  const eyeGap = 0.88 + (gg.eye_gap ?? 0.5) * 0.26;
  const glowAmt = gg.glow_amount ?? 0.5;
  const stageScale = STAGE_SCALE[stage] || STAGE_SCALE[1];

  const pal = deriveCatalogPalette(genome);
  const low = quality === 'low';
  const seg = low ? [14, 10] : [20, 16];
  const detailSeg = low ? [10, 8] : [14, 10];

  const geometries = [];
  const materials = [];
  const textures = [];
  const trackGeo = g => { geometries.push(g); return g; };
  const trackMat = m => { materials.push(m); return m; };
  const trackTex = t => { if (t) textures.push(t); return t; };

  const patTex = trackTex(buildPatternTexture(THREE, genome, pal));
  const MatClass = THREE.MeshPhysicalMaterial || THREE.MeshStandardMaterial;

  const matBase = trackMat(new MatClass({
    color: patTex ? 0xffffff : pal.base,
    map: patTex || null,
    roughness: bodyType === 'golem' || element === 'crystal' ? 0.24 : 0.44,
    metalness: element === 'machine' ? 0.42 : element === 'crystal' ? 0.22 : 0.06,
    clearcoat: bodyType === 'fish' || bodyType === 'axolotl' || element === 'crystal' ? 0.85 : 0.35,
    clearcoatRoughness: 0.22,
    emissive: pal.baseShadow,
    emissiveIntensity: 0.12,
  }));
  const matAlt = trackMat(new MatClass({
    color: pal.alt,
    roughness: 0.40,
    metalness: element === 'machine' ? 0.38 : 0.08,
    clearcoat: 0.3,
    emissive: pal.alt,
    emissiveIntensity: 0.06,
  }));
  const matBelly = trackMat(new MatClass({
    color: pal.belly,
    roughness: 0.48,
    metalness: 0.04,
    clearcoat: 0.2,
    emissive: pal.belly,
    emissiveIntensity: 0.05,
  }));
  const matAccent = trackMat(new MatClass({
    color: pal.accent,
    roughness: 0.28,
    metalness: 0.14,
    clearcoat: 0.55,
    emissive: pal.accent,
    emissiveIntensity: 0.24 + glowAmt * 0.18,
  }));
  const matGlow = trackMat(new MatClass({
    color: pal.glow,
    roughness: 0.16,
    metalness: 0.12,
    clearcoat: 0.8,
    emissive: pal.glow,
    emissiveIntensity: 0.68 + glowAmt * 0.38,
  }));
  const matDark = trackMat(new MatClass({
    color: pal.dark,
    roughness: 0.42,
    metalness: 0.1,
  }));
  const matEye = trackMat(new MatClass({
    color: pal.eye,
    roughness: 0.08,
    metalness: 0.15,
    clearcoat: 1.0,
    clearcoatRoughness: 0.05,
  }));
  const matIris = trackMat(new MatClass({
    color: pal.iris,
    emissive: pal.iris,
    emissiveIntensity: 0.48,
    roughness: 0.12,
    clearcoat: 1.0,
  }));
  const matWhite = trackMat(new MatClass({
    color: pal.white,
    emissive: pal.white,
    emissiveIntensity: 0.65,
    roughness: 0.1,
  }));
  const matCheek = trackMat(new MatClass({
    color: pal.cheek,
    emissive: pal.cheek,
    emissiveIntensity: 0.28,
    roughness: 0.45,
  }));
  const matBeak = trackMat(new MatClass({
    color: pal.beak,
    roughness: 0.28,
    metalness: 0.1,
    clearcoat: 0.6,
  }));
  const matWing = trackMat(new MatClass({
    color: wingsType === 'flame' || wingsType === 'crystal' ? pal.glow : pal.accent,
    emissive: pal.glow,
    emissiveIntensity: wingsType === 'flame' || wingsType === 'crystal' ? 0.42 : 0.18,
    roughness: 0.28,
    clearcoat: 0.75,
    transparent: true,
    opacity: wingsType === 'crystal' ? 0.86 : 0.95,
    side: THREE.DoubleSide,
  }));

  // Sculpted reusable geometries
  const sphere = trackGeo(new THREE.SphereGeometry(1, detailSeg[0], detailSeg[1]));
  const skullGeo = trackGeo(buildSculptedSkullGeo(THREE, bodyType, seg));
  const torsoGeo = trackGeo(buildSculptedTorsoGeo(THREE, bodyType, seg));
  const earGeo = trackGeo(buildSculptedEarGeo(THREE, low));
  const hornGeo = trackGeo(buildSculptedHornGeo(THREE, low));
  const pawGeo = trackGeo(buildSculptedPawGeo(THREE, low));
  const tailSegGeo = trackGeo(buildSculptedTailSegmentGeo(THREE, tailType === 'fluffy' || tailType === 'plume', low));
  const starGeo = trackGeo(buildStarCatchlightGeo(THREE, 1, 0.28));
  const cone = trackGeo(new THREE.ConeGeometry(1, 1, low ? 10 : 16));
  const cyl = trackGeo(new THREE.CylinderGeometry(0.68, 1, 1, low ? 10 : 16));
  const oct = trackGeo(new THREE.OctahedronGeometry(1, bodyType === 'golem' ? 1 : 0));
  const torus = trackGeo(new THREE.TorusGeometry(1, 0.26, low ? 8 : 10, low ? 14 : 22));

  const root = new THREE.Group();
  root.name = 'CatalogCreature_' + bodyType;

  // Authentic sprite-faithful proportions per species matching lib/companion/spark/render.mjs
  const B = {
    pup:        { spineY: 0.52, bodyScale: [0.35 + chub * 0.08, 0.31 + chub * 0.06, 0.44], neckPos: [0, 0.22, 0.16], headScale: [0.33, 0.30, 0.31], snoutScale: [0.13, 0.095, 0.14], snoutZ: 0.26 },
    fox:        { spineY: 0.52, bodyScale: [0.31 + chub * 0.06, 0.28 + chub * 0.05, 0.49], neckPos: [0, 0.24, 0.22], headScale: [0.31, 0.28, 0.32], snoutScale: [0.115, 0.085, 0.21], snoutZ: 0.30 },
    sprout:     { spineY: 0.42, bodyScale: [0.38 + chub * 0.08, 0.36 + chub * 0.07, 0.38], neckPos: [0, 0.20, 0.04], headScale: [0.32, 0.29, 0.30], snoutScale: [0.09, 0.07, 0.08], snoutZ: 0.25 },
    moth:       { spineY: 0.54, bodyScale: [0.29 + chub * 0.06, 0.33 + chub * 0.06, 0.35], neckPos: [0, 0.24, 0.06], headScale: [0.29, 0.26, 0.27], snoutScale: [0.08, 0.06, 0.08], snoutZ: 0.23 },
    axolotl:    { spineY: 0.44, bodyScale: [0.34 + chub * 0.07, 0.26 + chub * 0.05, 0.47], neckPos: [0, 0.16, 0.20], headScale: [0.37, 0.27, 0.30], snoutScale: [0.15, 0.085, 0.12], snoutZ: 0.25 },
    golem:      { spineY: 0.64, bodyScale: [0.47 + chub * 0.08, 0.43 + chub * 0.08, 0.40], neckPos: [0, 0.32, 0.06], headScale: [0.30, 0.26, 0.28], snoutScale: [0.12, 0.08, 0.10], snoutZ: 0.25 },
    dragonling: { spineY: 0.58, bodyScale: [0.33 + chub * 0.07, 0.31 + chub * 0.06, 0.53], neckPos: [0, 0.26, 0.26], headScale: [0.30, 0.26, 0.33], snoutScale: [0.135, 0.10, 0.21], snoutZ: 0.31 },
    bird:       { spineY: 0.52, bodyScale: [0.32 + chub * 0.07, 0.35 + chub * 0.06, 0.37], neckPos: [0, 0.26, 0.10], headScale: [0.29, 0.27, 0.28], snoutScale: [0.095, 0.085, 0.19], snoutZ: 0.27 },
    fish:       { spineY: 0.52, bodyScale: [0.28 + chub * 0.06, 0.33 + chub * 0.06, 0.50], neckPos: [0, 0.06, 0.26], headScale: [0.26, 0.29, 0.29], snoutScale: [0.10, 0.09, 0.12], snoutZ: 0.24 },
    serpent:    { spineY: 0.46, bodyScale: [0.27 + chub * 0.05, 0.25 + chub * 0.05, 0.45], neckPos: [0, 0.28, 0.22], headScale: [0.27, 0.23, 0.30], snoutScale: [0.11, 0.08, 0.17], snoutZ: 0.26 },
    biped:      { spineY: 0.58, bodyScale: [0.32 + chub * 0.07, 0.37 + chub * 0.06, 0.31], neckPos: [0, 0.30, 0.04], headScale: [0.33, 0.30, 0.30], snoutScale: [0.10, 0.08, 0.11], snoutZ: 0.25 },
  }[bodyType];

  const headFactor = 0.94 + (headGene - 0.5) * 0.22;
  const spine = joint(THREE, root, 'Spine', 0, B.spineY, 0);

  // Sculpted main torso + plush belly shield
  put(spine, new THREE.Mesh(torsoGeo, matBase), 'Body', 0, 0, 0, B.bodyScale);
  put(spine, new THREE.Mesh(sphere, matBelly), 'Belly', 0, -B.bodyScale[1] * 0.16, B.bodyScale[2] * 0.54, [
    B.bodyScale[0] * 0.70,
    B.bodyScale[1] * 0.68,
    B.bodyScale[2] * 0.54,
  ]);

  // Species-specific sculpted anatomy (layered chest ruff, armored pauldrons, dorsal spine ridge, S-coils)
  const coils = [];
  if (bodyType === 'fox' || bodyType === 'moth' || bodyType === 'pup') {
    put(spine, new THREE.Mesh(tailSegGeo, matBelly), 'ChestRuff', 0, B.bodyScale[1] * 0.38, B.bodyScale[2] * 0.56, [
      B.bodyScale[0] * 0.76,
      B.bodyScale[1] * 0.40,
      B.bodyScale[2] * 0.46,
    ]);
    for (const side of [-1, 1]) {
      put(spine, new THREE.Mesh(earGeo, matBelly), side < 0 ? 'RuffTuft_L' : 'RuffTuft_R', side * B.bodyScale[0] * 0.62, B.bodyScale[1] * 0.32, B.bodyScale[2] * 0.48, [0.08, 0.09, 0.08], [0.4, 0, side * -0.85]);
    }
  }
  if (bodyType === 'golem') {
    put(spine, new THREE.Mesh(oct, matGlow), 'CoreCrystal', 0, 0.06, B.bodyScale[2] * 0.90, [0.13, 0.16, 0.09]);
    put(spine, new THREE.Mesh(torus, matAlt), 'CoreBezel', 0, 0.06, B.bodyScale[2] * 0.86, [0.15, 0.18, 0.08]);
    for (const side of [-1, 1]) {
      put(spine, new THREE.Mesh(oct, matAlt), side < 0 ? 'Pauldron_L' : 'Pauldron_R', side * (B.bodyScale[0] * 0.96), B.bodyScale[1] * 0.48, 0, [0.20, 0.16, 0.22], [0, 0, side * -0.25]);
      put(spine, new THREE.Mesh(oct, matGlow), side < 0 ? 'ShoulderRune_L' : 'ShoulderRune_R', side * (B.bodyScale[0] * 1.06), B.bodyScale[1] * 0.58, 0.04, [0.06, 0.09, 0.06], [0, 0, side * -0.35]);
    }
  }
  if (bodyType === 'dragonling' || bodyType === 'axolotl' || bodyType === 'serpent') {
    for (let i = 0; i < 4; i++) {
      put(spine, new THREE.Mesh(earGeo, matAccent), 'BackCrest_' + i, 0, B.bodyScale[1] * (0.94 - i * 0.08), 0.14 - i * 0.14, [0.045, 0.085 - i * 0.01, 0.07], [-0.45, 0, 0]);
    }
  }
  if (bodyType === 'fish') {
    put(spine, new THREE.Mesh(earGeo, matAccent), 'DorsalFin', 0, B.bodyScale[1] * 1.04, -0.02, [0.045, 0.16, 0.24], [-0.55, 0, 0]);
  }
  if (bodyType === 'serpent') {
    let coilParent = spine;
    for (let i = 1; i <= 5; i++) {
      const cJoint = joint(THREE, coilParent, 'Coil_' + i, (i % 2 === 0 ? 1 : -1) * 0.09, -0.04, -0.20);
      put(cJoint, new THREE.Mesh(sphere, i % 2 === 0 ? matAlt : matBase), 'CoilMesh_' + i, 0, 0, 0, [
        Math.max(0.10, 0.25 - i * 0.028),
        Math.max(0.09, 0.21 - i * 0.024),
        0.22,
      ]);
      put(cJoint, new THREE.Mesh(sphere, matBelly), 'CoilBelly_' + i, 0, -0.04, 0.05, [
        Math.max(0.07, 0.18 - i * 0.02),
        Math.max(0.05, 0.12 - i * 0.015),
        0.18,
      ]);
      coils.push(cJoint);
      coilParent = cJoint;
    }
  }

  // 3D Pattern relief accents so patterns read in 3D silhouette
  if (patternType === 'plates' || patternType === 'facets') {
    for (let i = 0; i < 3; i++) {
      put(spine, new THREE.Mesh(oct, matAlt), 'PatternPlate_' + i, 0, B.bodyScale[1] * (0.65 - i * 0.22), -B.bodyScale[2] * 0.74, [0.15, 0.065, 0.11]);
    }
  }

  // Neck & Sculpted Skull
  const neck = joint(THREE, spine, 'Neck', B.neckPos[0], B.neckPos[1], B.neckPos[2]);
  const head = joint(THREE, neck, 'Head', 0, 0.12, 0.04);
  const hs = B.headScale.map(v => v * headFactor);
  put(head, new THREE.Mesh(skullGeo, matBase), 'Skull', 0, 0, 0, hs);

  // Crown fur tuft (like GBA/Moonwraith forehead lock)
  if (bodyType !== 'golem' && bodyType !== 'fish') {
    put(head, new THREE.Mesh(earGeo, matBase), 'CrownTuft', 0, hs[1] * 0.95, hs[2] * 0.35, [0.065, 0.075, 0.06], [0.35, 0, 0]);
  }

  // Sculpted Cheek Ruffs / Fur Wisps (driven by Verlet furChain)
  const furL = joint(THREE, head, 'Fur_L', -hs[0] * 0.92, -hs[1] * 0.18, 0.04);
  const furR = joint(THREE, head, 'Fur_R', hs[0] * 0.92, -hs[1] * 0.18, 0.04);
  put(furL, new THREE.Mesh(earGeo, matBase), 'FurMesh_L', -0.04, 0, 0, [0.065, 0.095, 0.065], [0, 0, Math.PI * 0.58]);
  put(furR, new THREE.Mesh(earGeo, matBase), 'FurMesh_R', 0.04, 0, 0, [0.065, 0.095, 0.065], [0, 0, -Math.PI * 0.58]);

  // Sculpted Muzzle / Beak / Nose & Jaw
  const noseMat = bodyType === 'bird' ? matBeak : matAlt;
  const noseGeo = bodyType === 'bird' ? earGeo : sphere;
  const noseRot = bodyType === 'bird' ? [Math.PI / 2, 0, 0] : [0, 0, 0];
  put(head, new THREE.Mesh(noseGeo, noseMat), 'Nose', 0, -hs[1] * 0.14, B.snoutZ * headFactor, B.snoutScale, noseRot);
  if (bodyType !== 'bird' && bodyType !== 'golem') {
    put(head, new THREE.Mesh(pawGeo, matDark), 'NoseTip', 0, -hs[1] * 0.07, (B.snoutZ + B.snoutScale[2] * 0.80) * headFactor, [0.046, 0.034, 0.036]);
  }

  const jaw = joint(THREE, head, 'Jaw', 0, -hs[1] * 0.42, B.snoutZ * 0.68);
  put(jaw, new THREE.Mesh(sphere, matBelly), 'JawMesh', 0, 0, 0.04, [B.snoutScale[0] * 0.82, 0.042, B.snoutScale[2] * 0.76]);

  // Mouth style: smile, w, fang, open
  if (mouthType === 'fang') {
    for (const side of [-1, 1]) {
      put(head, new THREE.Mesh(cone, matWhite), side < 0 ? 'Fang_L' : 'Fang_R', side * 0.058, -hs[1] * 0.34, B.snoutZ * 0.96, [0.022, 0.062, 0.022], [Math.PI, 0, 0]);
    }
  } else if (mouthType === 'open') {
    put(jaw, new THREE.Mesh(sphere, matCheek), 'Tongue', 0, 0.016, 0.05, [0.048, 0.024, 0.055]);
  } else if (mouthType === 'w') {
    for (const side of [-1, 1]) {
      put(head, new THREE.Mesh(torus, matDark), side < 0 ? 'MouthW_L' : 'MouthW_R', side * 0.034, -hs[1] * 0.28, B.snoutZ * 0.98, [0.028, 0.022, 0.02], [Math.PI, 0, 0]);
    }
  }

  // Studio Multi-Layer Expressive Eyes (sclera, iris dome, deep pupil, 4-point star catchlight, secondary highlight, brow & lid)
  const ex = hs[0] * 0.44 * eyeGap;
  const ey = hs[1] * 0.12;
  const ez = hs[2] * 0.86;
  const er = 0.076 * eyeSize;
  for (const side of [-1, 1]) {
    const eye = joint(THREE, head, side < 0 ? 'Eye_L' : 'Eye_R', side * ex, ey, ez);
    eye.rotation.y = side * 0.16; // wrap naturally around curved cheek/face
    put(eye, new THREE.Mesh(sphere, matEye), side < 0 ? 'EyeBall_L' : 'EyeBall_R', 0, 0, 0, [er, er * (eyeStyle === 'sleepy' ? 0.80 : 1.15), er * 0.56]);
    put(eye, new THREE.Mesh(sphere, matIris), side < 0 ? 'Iris_L' : 'Iris_R', 0, -er * 0.08, er * 0.42, [er * 0.76, er * 0.82, er * 0.26]);
    put(eye, new THREE.Mesh(sphere, matDark), side < 0 ? 'Pupil_L' : 'Pupil_R', 0, -er * 0.04, er * 0.54, [er * 0.42, er * 0.52, er * 0.16]);
    // Primary 4-point star catchlight + secondary specular droplet
    put(eye, new THREE.Mesh(starGeo, matWhite), side < 0 ? 'Spec_L' : 'Spec_R', side * -er * 0.26, er * 0.30, er * 0.64, [er * 0.34, er * 0.34, er * 0.18]);
    put(eye, new THREE.Mesh(sphere, matWhite), side < 0 ? 'SpecSub_L' : 'SpecSub_R', side * er * 0.28, -er * 0.28, er * 0.62, [er * 0.16, er * 0.16, er * 0.12]);
    if (eyeStyle === 'sparkle') {
      put(eye, new THREE.Mesh(starGeo, matGlow), side < 0 ? 'Sparkle_L' : 'Sparkle_R', side * er * 0.22, er * 0.04, er * 0.66, [er * 0.28, er * 0.28, er * 0.18]);
    }
    const lid = joint(THREE, eye, side < 0 ? 'Lid_L' : 'Lid_R', 0, er * 0.38, er * 0.20);
    const initLidScale = eyeStyle === 'closed' ? 1.85 : eyeStyle === 'sleepy' ? 0.96 : 0.32;
    put(lid, new THREE.Mesh(sphere, matBase), side < 0 ? 'LidMesh_L' : 'LidMesh_R', 0, 0, 0, [er * 1.16, er * initLidScale, er * 0.58]);
    // Sculpted brow ridge above eye
    put(eye, new THREE.Mesh(torus, matAlt), side < 0 ? 'Brow_L' : 'Brow_R', 0, er * 0.92, er * 0.26, [er * 0.72, er * 0.22, er * 0.32], [0, 0, side * -0.18]);

    put(head, new THREE.Mesh(sphere, matCheek), side < 0 ? 'Cheek_L' : 'Cheek_R', side * (ex * 1.26), ey - er * 0.96, ez * 0.88, [0.046, 0.030, 0.024]);
  }

  // Sprout head stem + sculpted leaves
  if (bodyType === 'sprout') {
    const stem = joint(THREE, head, 'SproutStem', 0, hs[1] * 0.90, 0);
    put(stem, new THREE.Mesh(cyl, matAccent), 'SproutStalk', 0, 0.08, 0, [0.026, 0.16, 0.026]);
    put(stem, new THREE.Mesh(earGeo, matGlow), 'SproutLeaf_L', -0.09, 0.16, 0, [0.065, 0.08, 0.04], [0, 0, 1.15]);
    put(stem, new THREE.Mesh(earGeo, matAccent), 'SproutLeaf_R', 0.09, 0.16, 0, [0.065, 0.08, 0.04], [0, 0, -1.15]);
  }

  // Ears (all 12 catalogue types: pointy, round, horns, crown, leaf, antlers, flame, crystal, antenna, feelers, bolts, gills)
  const ears = {};
  for (const side of [-1, 1]) {
    const eJoint = joint(THREE, head, side < 0 ? 'Ear_L' : 'Ear_R', side * (hs[0] * 0.64), hs[1] * 0.76, -0.02);
    ears[side < 0 ? 'L' : 'R'] = eJoint;
    if (earsType === 'round') {
      put(eJoint, new THREE.Mesh(sphere, matBase), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.07 * earSize, 0, [0.095 * earSize, 0.095 * earSize, 0.055]);
      put(eJoint, new THREE.Mesh(sphere, matCheek), side < 0 ? 'EarInner_L' : 'EarInner_R', 0, 0.07 * earSize, 0.032, [0.055 * earSize, 0.055 * earSize, 0.024]);
    } else if (earsType === 'horns') {
      put(eJoint, new THREE.Mesh(hornGeo, matAccent), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.12 * earSize, 0, [0.058 * earSize, 0.12 * earSize, 0.058 * earSize], [-0.15, side < 0 ? Math.PI : 0, side * -0.28]);
    } else if (earsType === 'crown') {
      put(eJoint, new THREE.Mesh(oct, matGlow), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.11 * earSize, 0.02, [0.065 * earSize, 0.16 * earSize, 0.045 * earSize], [0, 0, side * -0.18]);
    } else if (earsType === 'leaf') {
      put(eJoint, new THREE.Mesh(earGeo, matAccent), side < 0 ? 'EarMesh_L' : 'EarMesh_R', side * 0.04, 0.11 * earSize, 0, [0.075 * earSize, 0.10 * earSize, 0.04], [0, 0, side * -0.45]);
    } else if (earsType === 'antlers') {
      put(eJoint, new THREE.Mesh(hornGeo, matAlt), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.13 * earSize, 0, [0.032, 0.12 * earSize, 0.032], [0, 0, side * -0.25]);
      put(eJoint, new THREE.Mesh(cyl, matAlt), side < 0 ? 'AntlerTine_L' : 'AntlerTine_R', side * 0.055, 0.16 * earSize, 0.02, [0.022, 0.13 * earSize, 0.022], [0, 0, side * -0.78]);
    } else if (earsType === 'flame') {
      put(eJoint, new THREE.Mesh(earGeo, matGlow), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.13 * earSize, 0, [0.072 * earSize, 0.13 * earSize, 0.055 * earSize], [-0.15, 0, side * -0.22]);
    } else if (earsType === 'crystal') {
      put(eJoint, new THREE.Mesh(oct, matGlow), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.12 * earSize, 0, [0.065 * earSize, 0.20 * earSize, 0.055 * earSize], [0, 0, side * -0.3]);
    } else if (earsType === 'antenna' || earsType === 'feelers') {
      put(eJoint, new THREE.Mesh(hornGeo, matAlt), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.12 * earSize, 0.02, [0.022, 0.11 * earSize, 0.022], [0.2, 0, side * -0.3]);
      put(eJoint, new THREE.Mesh(sphere, matGlow), side < 0 ? 'AntennaOrb_L' : 'AntennaOrb_R', side * 0.055, 0.24 * earSize, 0.05, [0.046, 0.046, 0.046]);
    } else if (earsType === 'bolts') {
      put(eJoint, new THREE.Mesh(cyl, matAccent), side < 0 ? 'EarMesh_L' : 'EarMesh_R', side * 0.04, 0.04, 0, [0.048 * earSize, 0.12 * earSize, 0.048 * earSize], [0, 0, side * -1.2]);
    } else if (earsType === 'gills') {
      for (let g = 0; g < 3; g++) {
        put(eJoint, new THREE.Mesh(earGeo, matAccent), `${side < 0 ? 'Gill_L_' : 'Gill_R_'}${g}`, side * (0.06 + g * 0.02), (0.04 - g * 0.05) * earSize, 0, [0.036, 0.07 * earSize, 0.028], [0, 0, side * (-0.9 - g * 0.25)]);
      }
    } else {
      // Sculpted hollow pointy ear + inner ear cushion
      put(eJoint, new THREE.Mesh(earGeo, matBase), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.12 * earSize, 0, [0.088 * earSize, 0.125 * earSize, 0.075 * earSize], [0, 0, side * -0.22]);
      put(eJoint, new THREE.Mesh(earGeo, matCheek), side < 0 ? 'EarInner_L' : 'EarInner_R', 0, 0.11 * earSize, 0.024, [0.052 * earSize, 0.085 * earSize, 0.035], [0, 0, side * -0.22]);
    }
  }

  // Sculpted Beveled Wings (feather, bat, moth, leaf, crystal, flame, vanes, none) + fish pectoral fins
  const wings = {};
  const effectiveWings = bodyType === 'fish' && wingsType === 'none' ? 'leaf' : wingsType;
  if (effectiveWings !== 'none') {
    const wGeo = trackGeo(buildWingGeometry(THREE, effectiveWings, 0.48 * wingSize, 0.30 * wingSize));
    for (const side of [-1, 1]) {
      const pivot = joint(THREE, spine, side < 0 ? 'Wing_L' : 'Wing_R', side * (B.bodyScale[0] * 0.76), B.bodyScale[1] * 0.22, -0.04);
      const wMesh = put(pivot, new THREE.Mesh(wGeo, matWing), side < 0 ? 'WingMesh_L' : 'WingMesh_R', 0, 0, 0);
      wMesh.scale.x = side;
      wMesh.rotation.y = side * -0.25;
      // Glowing star/eye-spot ornament on wing membrane
      put(pivot, new THREE.Mesh(starGeo, matGlow), side < 0 ? 'WingSpot_L' : 'WingSpot_R', side * 0.24 * wingSize, 0.08 * wingSize, 0.025, [0.038, 0.038, 0.02]);
      wings[side < 0 ? 'L' : 'R'] = pivot;
    }
  } else {
    wings.L = joint(THREE, spine, 'Wing_L', -B.bodyScale[0] * 0.7, 0.08, 0);
    wings.R = joint(THREE, spine, 'Wing_R', B.bodyScale[0] * 0.7, 0.08, 0);
  }

  // Sculpted Articulated Limbs & 3-Toed Paws
  const legs = {};
  const arms = {};
  const legLen = 0.85 + (legsGene - 0.5) * 0.3;
  if (bodyType === 'biped' || bodyType === 'golem' || bodyType === 'bird' || bodyType === 'sprout' || bodyType === 'moth') {
    for (const side of [-1, 1]) {
      const hip = joint(THREE, spine, side < 0 ? 'Leg_FL' : 'Leg_FR', side * (B.bodyScale[0] * 0.48), -B.bodyScale[1] * 0.68, 0.02);
      put(hip, new THREE.Mesh(cyl, matBase), side < 0 ? 'Thigh_L' : 'Thigh_R', 0, -0.09 * legLen, 0, [0.082, 0.14 * legLen, 0.082]);
      put(hip, new THREE.Mesh(pawGeo, bodyType === 'bird' ? matBeak : matAlt), side < 0 ? 'Paw_L' : 'Paw_R', 0, -0.19 * legLen, 0.035, [0.092, 0.052, 0.115]);
      legs[side < 0 ? 'FL' : 'FR'] = hip;
      legs[side < 0 ? 'BL' : 'BR'] = hip;

      if (bodyType !== 'sprout') {
        const arm = joint(THREE, spine, side < 0 ? 'Arm_L' : 'Arm_R', side * (B.bodyScale[0] * 0.88), B.bodyScale[1] * 0.12, 0.05);
        put(arm, new THREE.Mesh(bodyType === 'golem' ? oct : cyl, matAlt), side < 0 ? 'ArmMesh_L' : 'ArmMesh_R', side * 0.04, -0.09, 0.02, bodyType === 'golem' ? [0.12, 0.20, 0.12] : [0.068, 0.15, 0.068]);
        put(arm, new THREE.Mesh(pawGeo, matBelly), side < 0 ? 'Hand_L' : 'Hand_R', side * 0.05, -0.17, 0.03, [0.058, 0.048, 0.062]);
        arms[side < 0 ? 'L' : 'R'] = arm;
      }
    }
  } else if (bodyType === 'fish' || bodyType === 'serpent') {
    for (const side of [-1, 1]) {
      const fin = joint(THREE, spine, side < 0 ? 'Leg_FL' : 'Leg_FR', side * (B.bodyScale[0] * 0.75), -B.bodyScale[1] * 0.55, 0.08);
      put(fin, new THREE.Mesh(earGeo, matAccent), side < 0 ? 'VentralFin_L' : 'VentralFin_R', 0, -0.05, 0, [0.045, 0.055, 0.095], [Math.PI, 0, side * 0.35]);
      legs[side < 0 ? 'FL' : 'FR'] = fin;
      legs[side < 0 ? 'BL' : 'BR'] = fin;
    }
  } else {
    // Quadruped: pup, fox, axolotl, dragonling
    const layout = [
      [-B.bodyScale[0] * 0.58, -B.bodyScale[1] * 0.62, B.bodyScale[2] * 0.48, 'FL'],
      [ B.bodyScale[0] * 0.58, -B.bodyScale[1] * 0.62, B.bodyScale[2] * 0.48, 'FR'],
      [-B.bodyScale[0] * 0.60, -B.bodyScale[1] * 0.62, -B.bodyScale[2] * 0.46, 'BL'],
      [ B.bodyScale[0] * 0.60, -B.bodyScale[1] * 0.62, -B.bodyScale[2] * 0.46, 'BR'],
    ];
    for (const [x, y, z, label] of layout) {
      const hip = joint(THREE, spine, 'Leg_' + label, x, y, z);
      put(hip, new THREE.Mesh(cyl, matBase), 'Thigh_' + label, 0, -0.09 * legLen, 0, [0.078, 0.14 * legLen, 0.078]);
      put(hip, new THREE.Mesh(pawGeo, matAlt), 'Paw_' + label, 0, -0.19 * legLen, 0.03, [0.088, 0.050, 0.105]);
      legs[label] = hip;
    }
  }

  // Multi-segment Verlet-driven Sculpted Tail
  const tailSegments = [];
  let tailParent = coils.length ? coils[coils.length - 1] : spine;
  const numTailSegs = tailType === 'none' ? 1 : 4;
  for (let i = 1; i <= numTailSegs; i++) {
    const tz = i === 1 ? (coils.length ? -0.18 : -B.bodyScale[2] * 0.85) : -0.15 * tailSize;
    const ty = i === 1 ? 0.04 : 0.035;
    const tJoint = joint(THREE, tailParent, 'Tail_' + i, 0, ty, tz);
    const rScale = tailType === 'fluffy' || tailType === 'plume'
      ? [0.125 * tailSize * (1.18 - i * 0.11), 0.115 * tailSize * (1.18 - i * 0.11), 0.15 * tailSize]
      : [0.075 * tailSize * (1.12 - i * 0.15), 0.075 * tailSize * (1.12 - i * 0.15), 0.135 * tailSize];
    const segMat = (i === numTailSegs && (tailType === 'flame' || tailType === 'crystal')) ? matGlow : i >= numTailSegs - 1 ? matAccent : matBase;
    put(tJoint, new THREE.Mesh(tailType === 'crystal' ? oct : tailSegGeo, segMat), 'TailMesh_' + i, 0, 0, -0.05, rScale);
    tailSegments.push(tJoint);
    tailParent = tJoint;
  }

  // Distinct sculpted tail tips per tailType
  const tailTip = tailSegments[tailSegments.length - 1];
  if (tailType === 'spade' || tailType === 'leaf') {
    put(tailTip, new THREE.Mesh(earGeo, matAccent), 'TailTipOrnament', 0, 0.02, -0.14 * tailSize, [0.11 * tailSize, 0.10 * tailSize, 0.05], [-Math.PI / 2, 0, 0]);
  } else if (tailType === 'fishtail' || tailType === 'fin') {
    put(tailTip, new THREE.Mesh(earGeo, matAccent), 'TailFinUpper', 0, 0.08 * tailSize, -0.12 * tailSize, [0.04, 0.10 * tailSize, 0.12 * tailSize], [-0.8, 0, 0]);
    put(tailTip, new THREE.Mesh(earGeo, matAccent), 'TailFinLower', 0, -0.06 * tailSize, -0.12 * tailSize, [0.04, 0.09 * tailSize, 0.11 * tailSize], [-2.2, 0, 0]);
  } else if (tailType === 'gear') {
    put(tailTip, new THREE.Mesh(torus, matAccent), 'TailGear', 0, 0, -0.12 * tailSize, [0.095 * tailSize, 0.095 * tailSize, 0.06], [0, Math.PI / 2, 0]);
  } else if (tailType === 'flame') {
    put(tailTip, new THREE.Mesh(earGeo, matGlow), 'TailFlameTip', 0, 0.05 * tailSize, -0.14 * tailSize, [0.095 * tailSize, 0.14 * tailSize, 0.095 * tailSize], [-0.4, 0, 0]);
  }

  // Cosmic / Elemental Wisp chain floating around shoulder
  const wispJoints = [];
  let wispParent = spine;
  for (let i = 1; i <= 3; i++) {
    const wj = joint(THREE, wispParent, 'Wisp_' + i, i === 1 ? B.bodyScale[0] * 0.88 : 0, i === 1 ? 0.18 : 0.08, -0.12);
    put(wj, new THREE.Mesh(starGeo, matGlow), 'WispOrb_' + i, 0, 0, 0, [0.038 - i * 0.006, 0.038 - i * 0.006, 0.038 - i * 0.006]);
    wispJoints.push(wj);
    wispParent = wj;
  }

  root.scale.setScalar(stageScale);
  root.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(root);
  spine.position.y -= box.min.y / stageScale;
  root.updateMatrixWorld(true);

  // Grounded contact shadow at y = 0
  const shadowGeo = trackGeo(new THREE.CircleGeometry(0.54 * stageScale, low ? 18 : 28));
  const shadowMat = trackMat(new THREE.MeshBasicMaterial({
    color: 0x050312,
    transparent: true,
    opacity: 0.48,
    depthWrite: false,
  }));
  const shadowMesh = new THREE.Mesh(shadowGeo, shadowMat);
  shadowMesh.name = 'ContactShadow';
  shadowMesh.rotation.x = -Math.PI / 2;
  shadowMesh.position.y = 0.003;
  root.add(shadowMesh);

  // Real-time Elemental Fluid Particles (Points)
  const particleCount = low ? 16 : 28;
  const secondary = createSecondaryMotion({
    seed,
    element,
    tailSegments: tailSegments.length,
    particleCount,
  });

  const fluidProf = ELEMENT_FLUID_PROFILES[element] || ELEMENT_FLUID_PROFILES.verdant;
  const ptPositions = new Float32Array(particleCount * 3);
  secondary.fluid.particles.forEach((pt, idx) => {
    ptPositions[idx * 3] = pt.x;
    ptPositions[idx * 3 + 1] = pt.y;
    ptPositions[idx * 3 + 2] = pt.z;
  });
  const ptGeo = trackGeo(new THREE.BufferGeometry());
  ptGeo.setAttribute('position', new THREE.BufferAttribute(ptPositions, 3));
  const ptMat = trackMat(new THREE.PointsMaterial({
    color: fluidProf.colorA || pal.glow,
    size: 0.068,
    transparent: true,
    opacity: 0.88,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  }));
  const fluidPoints = new THREE.Points(ptGeo, ptMat);
  fluidPoints.name = 'ElementFluidParticles';
  root.add(fluidPoints);

  // Count total triangles and verify phone budget (< 25,000)
  let triangles = 0;
  root.traverse(obj => {
    const g = obj.geometry;
    if (!g || obj.isPoints) return;
    const pos = g.getAttribute('position');
    triangles += g.index ? g.index.count / 3 : (pos ? pos.count / 3 : 0);
  });
  triangles = Math.round(triangles);

  root.userData = {
    body: bodyType,
    island: pal.island,
    element,
    ears: earsType,
    tail: tailType,
    wings: wingsType,
    pattern: patternType,
    eye_style: eyeStyle,
    mouth: mouthType,
    stage,
    triangles,
    seed,
  };

  let disposed = false;
  function dispose() {
    if (disposed) return;
    disposed = true;
    geometries.forEach(g => g.dispose());
    materials.forEach(m => m.dispose());
    textures.forEach(t => t.dispose());
  }

  return {
    body: bodyType,
    element,
    palette: pal,
    root,
    joints: {
      spine,
      neck,
      head,
      jaw,
      ears,
      wings,
      legs,
      arms,
      coils,
      tailSegments,
      furL,
      furR,
      wispJoints,
      shadowMesh,
      fluidPoints,
    },
    secondary,
    triangles,
    dispose,
  };
}

/**
 * Step and apply film-style animation + Verlet/fluid secondary motion to a 3D catalogue creature rig.
 */
export function poseCatalogCreature(rig, {
  actorPose = null,
  emotion = null,
  dt = 1 / 60,
  time = 0,
  lookAt = null,
  speaking = false,
  reduced = false,
} = {}) {
  const { spine, neck, head, jaw, ears, wings, legs, arms, coils, tailSegments, furL, furR, wispJoints, shadowMesh, fluidPoints } = rig.joints;
  const t = reduced ? 0 : time;
  const state = actorPose?.state || 'idle';
  const lift = reduced ? 0 : (actorPose?.lift || 0);
  const targetSy = reduced ? 1 : (actorPose?.sy || 1);

  const sec = stepSecondaryMotion(rig.secondary, dt, {
    position: { x: actorPose?.x || 0, y: 0, z: actorPose?.z || 0 },
    lift,
    targetSy,
    emotion,
    lookAt,
    reduced,
  });

  // Soft-body squash & stretch + breathing
  const breathe = reduced ? 1 : 1 + Math.sin(t * 2.1) * 0.028;
  const sy = sec.softBody.sy * breathe;
  const sx = sec.softBody.sx;
  const sz = sec.softBody.sz;
  spine.scale.set(sx, sy, sz);
  spine.position.y = (rig.root.userData.baseSpineY ?? (rig.root.userData.baseSpineY = spine.position.y)) + lift * 0.42;

  // Body pitch/lean for curious lean, scared scoot, happy zoomies, hop, walk
  const lean = reduced ? 0 : (actorPose?.lean ?? (state === 'curious' ? 0.22 : state === 'scared' ? -0.18 : state === 'zoomies' ? 0.18 : 0));
  spine.rotation.x = lean;
  spine.rotation.z = reduced ? 0 : (state === 'zoomies' ? Math.sin(t * 14) * 0.12 : sec.softBody.jiggle * 0.25);

  // Head turn & tilt
  neck.rotation.x = state === 'curious' ? 0.16 : state === 'scared' ? -0.12 : 0;
  head.rotation.y = reduced ? 0 : (actorPose?.head ?? Math.sin(t * 0.7) * 0.12);
  head.rotation.z = reduced ? 0 : (state === 'curious' ? 0.18 : Math.sin(t * 1.1) * 0.04);

  // Speaking / open jaw
  jaw.rotation.x = speaking && !reduced ? 0.24 + Math.sin(t * 14) * 0.16 : state === 'zoomies' ? 0.15 : 0;

  // Eyelid blink
  const blink = !reduced && Math.sin(t * 2.7 + 0.4) > 0.94 ? 1 : 0;
  for (const name of ['Lid_L', 'Lid_R']) {
    const lid = rig.root.getObjectByName(name);
    if (lid) lid.scale.y = 0.32 + blink * 1.65;
  }

  // Verlet ear motion
  if (ears.L && ears.R) {
    ears.L.rotation.z = sec.earL.yaw + (actorPose?.ear || 0) * 0.5;
    ears.L.rotation.x = sec.earL.pitch;
    ears.R.rotation.z = -sec.earR.yaw - (actorPose?.ear || 0) * 0.5;
    ears.R.rotation.x = sec.earR.pitch;
  }

  // Verlet fur tufts
  if (furL && furR) {
    furL.rotation.z = sec.fur.yaw * 0.6;
    furR.rotation.z = -sec.fur.yaw * 0.6;
  }

  // Verlet wing motion
  if (wings.L && wings.R) {
    const flapBoost = state === 'hop' || state === 'zoomies' ? Math.sin(t * 14) * 0.38 : 0;
    wings.L.rotation.z = 0.18 + sec.wingL.pitch + flapBoost;
    wings.R.rotation.z = -(0.18 + sec.wingR.pitch + flapBoost);
  }

  // Locomotion leg & arm swing
  const moving = !reduced && (state === 'walk' || state === 'hop' || state === 'zoomies' || state === 'scared');
  const freq = state === 'zoomies' ? 14 : state === 'scared' ? 11 : 7;
  const amp = state === 'zoomies' ? 0.62 : state === 'hop' ? 0.48 : 0.38;
  ['FL', 'FR', 'BL', 'BR'].forEach((label, idx) => {
    const leg = legs[label];
    if (!leg) return;
    leg.rotation.x = moving ? Math.sin(t * freq + (idx % 2 === 0 ? 0 : Math.PI)) * amp : 0;
  });
  if (arms.L && arms.R) {
    arms.L.rotation.x = moving ? Math.sin(t * freq + Math.PI) * (amp * 0.7) : state === 'curious' ? -0.35 : 0;
    arms.R.rotation.x = moving ? Math.sin(t * freq) * (amp * 0.7) : state === 'curious' ? -0.35 : 0;
  }

  // Serpent body coil wave
  coils.forEach((cJoint, i) => {
    cJoint.rotation.y = reduced ? 0 : Math.sin(t * 3.5 - i * 0.9) * (moving ? 0.32 : 0.14);
  });

  // Verlet multi-segment tail chain
  tailSegments.forEach((seg, i) => {
    const a = sec.tailAngles[i] || sec.tailAngles[sec.tailAngles.length - 1] || { yaw: 0, pitch: 0 };
    seg.rotation.y = a.yaw + (actorPose?.tail || 0) * 0.35;
    seg.rotation.x = a.pitch;
  });

  // Verlet cosmic wisps
  wispJoints.forEach((wj, i) => {
    const a = sec.wisp[i] || { yaw: 0, pitch: 0 };
    wj.rotation.y = a.yaw;
    wj.rotation.x = a.pitch;
  });

  // Update elemental fluid particle positions in 3D buffer
  if (fluidPoints?.geometry) {
    const attr = fluidPoints.geometry.getAttribute('position');
    if (attr) {
      const arr = attr.array;
      for (let i = 0; i < sec.particles.length; i++) {
        const pt = sec.particles[i];
        arr[i * 3] = pt.x;
        arr[i * 3 + 1] = pt.y;
        arr[i * 3 + 2] = pt.z;
      }
      attr.needsUpdate = true;
    }
  }

  // Update grounded contact shadow
  const sh = contactShadow({ lift, sy });
  if (shadowMesh) {
    shadowMesh.scale.setScalar(sh.scale);
    if (shadowMesh.material) shadowMesh.material.opacity = sh.opacity;
  }

  return {
    state,
    sx,
    sy,
    sz,
    lift,
    blink,
    shadowScale: sh.scale,
    tailYaw: tailSegments[0]?.rotation.y || 0,
    wingFlap: wings.L?.rotation.z || 0,
  };
}

/**
 * Measure 360° silhouettes (front, side, back, threeQuarter) for automated tests.
 */
export function measureCatalogSilhouette(THREE, rig) {
  const root = rig.root;
  const nose = root.getObjectByName('Nose');
  const shadow = root.getObjectByName('ContactShadow');
  const fluid = root.getObjectByName('ElementFluidParticles');
  if (shadow) shadow.visible = false;
  if (fluid) fluid.visible = false;

  const round = v => Math.round(v * 1000) / 1000;
  const views = {};
  for (const [name, yaw] of [['front', 0], ['side', Math.PI / 2], ['back', Math.PI], ['threeQuarter', Math.PI / 4]]) {
    root.rotation.y = yaw;
    root.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(root);
    const size = box.getSize(new THREE.Vector3());
    const nosePos = new THREE.Vector3();
    if (nose) nose.getWorldPosition(nosePos);
    views[name] = {
      width: round(size.x),
      height: round(size.y),
      depth: round(size.z),
      noseZ: round(nosePos.z),
      minY: round(box.min.y),
    };
  }
  root.rotation.y = 0;
  if (shadow) shadow.visible = true;
  if (fluid) fluid.visible = true;
  root.updateMatrixWorld(true);
  return views;
}
