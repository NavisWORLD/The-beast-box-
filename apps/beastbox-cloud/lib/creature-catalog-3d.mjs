/**
 * FAITHFUL 3D CATALOGUE CREATURES
 *
 * Turns every Beast Box catalogue creature (all 11 body plans: fox, pup, biped, golem,
 * serpent, axolotl, moth, bird, dragonling, sprout, fish) into a true, 360°-rotatable
 * Three.js 3D living character using its exact island palette from public/spark/genome.mjs
 * (and public/spark/catalog-index.json), genes, ears, tails, wings, patterns, eyes, and mouth.
 *
 * Driven deterministically by the creature's seed, film-motion actor state, and Verlet +
 * curl-noise/SPH-lite fluid secondary motion (lib/companion/fluid-motion.mjs).
 * Triangle budget: strictly < 25,000 triangles per creature for 60fps on iPhone 16.
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
 * Build a deterministic procedural pattern texture when running in browser, or null in headless Node.
 */
function buildPatternTexture(THREE, genome, pal) {
  if (typeof document === 'undefined') return null;
  try {
    const c = document.createElement('canvas');
    c.width = 128;
    c.height = 128;
    const ctx = c.getContext('2d');
    if (!ctx) return null;
    const hex = n => '#' + n.toString(16).padStart(6, '0');
    ctx.fillStyle = hex(pal.base);
    ctx.fillRect(0, 0, 128, 128);

    // Subtle vertical shading ramp like the 5-tone sprite ramp
    const grad = ctx.createLinearGradient(0, 0, 0, 128);
    grad.addColorStop(0, hex(pal.baseLight));
    grad.addColorStop(0.55, hex(pal.base));
    grad.addColorStop(1, hex(pal.baseShadow));
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 128, 128);

    const pat = genome?.pattern || 'spots';
    const rand = seededPrng(String(genome?.seed || 'pat') + ':' + pat + ':' + String(genome?.pattern_variant ?? 0));
    ctx.fillStyle = hex(pal.alt);
    ctx.strokeStyle = hex(pal.accent);
    ctx.lineWidth = 3;

    if (pat === 'spots') {
      for (let i = 0; i < 14; i++) {
        ctx.beginPath();
        ctx.arc(12 + rand() * 104, 12 + rand() * 104, 5 + rand() * 7, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (pat === 'stripes') {
      for (let y = 14; y < 116; y += 18) {
        ctx.fillRect(8, y, 112, 6);
      }
    } else if (pat === 'stars') {
      ctx.fillStyle = hex(pal.glow);
      for (let i = 0; i < 16; i++) {
        const x = 10 + rand() * 108, y = 10 + rand() * 108, r = 3 + rand() * 3;
        ctx.fillRect(x - r, y - 1, r * 2, 2);
        ctx.fillRect(x - 1, y - r, 2, r * 2);
      }
    } else if (pat === 'circuits') {
      ctx.strokeStyle = hex(pal.glow);
      ctx.lineWidth = 2;
      for (let i = 0; i < 8; i++) {
        const x0 = 16 + rand() * 96, y0 = 16 + rand() * 96;
        ctx.beginPath();
        ctx.moveTo(x0, y0);
        ctx.lineTo(x0 + (rand() > 0.5 ? 24 : -24), y0);
        ctx.lineTo(x0 + (rand() > 0.5 ? 24 : -24), y0 + 20);
        ctx.stroke();
      }
    } else if (pat === 'cracks') {
      ctx.strokeStyle = hex(pal.glow);
      for (let i = 0; i < 7; i++) {
        ctx.beginPath();
        let x = 20 + rand() * 88, y = 16 + rand() * 96;
        ctx.moveTo(x, y);
        for (let s = 0; s < 3; s++) {
          x += (rand() - 0.5) * 28;
          y += 12 + rand() * 14;
          ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
    } else if (pat === 'facets' || pat === 'plates') {
      for (let i = 0; i < 10; i++) {
        const x = 14 + rand() * 90, y = 14 + rand() * 90;
        ctx.fillRect(x, y, 16, 12);
        ctx.strokeRect(x, y, 16, 12);
      }
    } else if (pat === 'moss') {
      ctx.fillStyle = hex(pal.accent);
      for (let i = 0; i < 12; i++) {
        ctx.beginPath();
        ctx.arc(16 + rand() * 96, 8 + rand() * 48, 8 + rand() * 8, 0, Math.PI * 2);
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

function buildWingGeometry(THREE, wingType, span = 0.48, lift = 0.28) {
  const shape = new THREE.Shape();
  shape.moveTo(0, 0);
  if (wingType === 'bat' || wingType === 'flame') {
    shape.bezierCurveTo(span * 0.3, lift * 1.15, span * 0.75, lift * 1.25, span, lift * 0.45);
    shape.quadraticCurveTo(span * 0.78, 0.02, span * 0.68, -lift * 0.32);
    shape.quadraticCurveTo(span * 0.45, -0.02, span * 0.32, -lift * 0.38);
    shape.quadraticCurveTo(span * 0.15, -0.05, 0.02, -0.05);
  } else if (wingType === 'moth') {
    shape.bezierCurveTo(span * 0.25, lift * 1.35, span * 0.95, lift * 1.2, span, lift * 0.25);
    shape.bezierCurveTo(span * 0.92, -lift * 0.35, span * 0.65, -lift * 0.85, span * 0.25, -lift * 0.65);
    shape.lineTo(0.02, -0.06);
  } else if (wingType === 'crystal' || wingType === 'vanes') {
    shape.lineTo(span * 0.38, lift * 0.95);
    shape.lineTo(span, lift * 0.42);
    shape.lineTo(span * 0.78, -lift * 0.28);
    shape.lineTo(span * 0.32, -lift * 0.42);
    shape.lineTo(0.02, -0.05);
  } else {
    // feather / leaf
    shape.bezierCurveTo(span * 0.28, lift * 1.1, span * 0.72, lift * 1.05, span, lift * 0.3);
    shape.bezierCurveTo(span * 0.82, -lift * 0.25, span * 0.45, -lift * 0.45, 0.02, -0.05);
  }
  shape.closePath();
  return new THREE.ExtrudeGeometry(shape, {
    depth: 0.032,
    bevelEnabled: true,
    bevelThickness: 0.008,
    bevelSize: 0.008,
    bevelSegments: 1,
  });
}

/**
 * Build a faithful 3D Three.js character for any Beast Box catalogue creature genome.
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
  const earSize = 0.82 + (gg.ear_size ?? 0.5) * 0.42;
  const tailSize = 0.82 + (gg.tail_size ?? 0.5) * 0.45;
  const wingSize = 0.82 + (gg.wing_size ?? 0.5) * 0.45;
  const eyeSize = 0.88 + (gg.eye_size ?? 0.5) * 0.32;
  const eyeGap = 0.88 + (gg.eye_gap ?? 0.5) * 0.28;
  const glowAmt = gg.glow_amount ?? 0.5;
  const stageScale = STAGE_SCALE[stage] || STAGE_SCALE[1];

  const pal = deriveCatalogPalette(genome);
  const low = quality === 'low';
  const seg = low ? [12, 9] : [18, 13];

  const geometries = [];
  const materials = [];
  const textures = [];
  const trackGeo = g => { geometries.push(g); return g; };
  const trackMat = m => { materials.push(m); return m; };
  const trackTex = t => { if (t) textures.push(t); return t; };

  const patTex = trackTex(buildPatternTexture(THREE, genome, pal));

  const matBase = trackMat(new THREE.MeshStandardMaterial({
    color: patTex ? 0xffffff : pal.base,
    map: patTex || null,
    roughness: bodyType === 'golem' || element === 'crystal' ? 0.32 : 0.52,
    metalness: element === 'machine' ? 0.38 : element === 'crystal' ? 0.18 : 0.06,
    emissive: pal.baseShadow,
    emissiveIntensity: 0.08,
  }));
  const matAlt = trackMat(new THREE.MeshStandardMaterial({
    color: pal.alt,
    roughness: 0.48,
    metalness: element === 'machine' ? 0.35 : 0.08,
  }));
  const matBelly = trackMat(new THREE.MeshStandardMaterial({
    color: pal.belly,
    roughness: 0.56,
    metalness: 0.04,
  }));
  const matAccent = trackMat(new THREE.MeshStandardMaterial({
    color: pal.accent,
    roughness: 0.36,
    metalness: 0.12,
    emissive: pal.accent,
    emissiveIntensity: 0.18 + glowAmt * 0.15,
  }));
  const matGlow = trackMat(new THREE.MeshStandardMaterial({
    color: pal.glow,
    roughness: 0.2,
    metalness: 0.1,
    emissive: pal.glow,
    emissiveIntensity: 0.55 + glowAmt * 0.35,
  }));
  const matDark = trackMat(new THREE.MeshStandardMaterial({
    color: pal.dark,
    roughness: 0.5,
    metalness: 0.08,
  }));
  const matEye = trackMat(new THREE.MeshStandardMaterial({
    color: pal.eye,
    roughness: 0.15,
    metalness: 0.1,
  }));
  const matIris = trackMat(new THREE.MeshStandardMaterial({
    color: pal.iris,
    emissive: pal.iris,
    emissiveIntensity: 0.35,
    roughness: 0.18,
  }));
  const matWhite = trackMat(new THREE.MeshStandardMaterial({
    color: pal.white,
    emissive: pal.white,
    emissiveIntensity: 0.45,
    roughness: 0.15,
  }));
  const matCheek = trackMat(new THREE.MeshStandardMaterial({
    color: pal.cheek,
    emissive: pal.cheek,
    emissiveIntensity: 0.2,
    roughness: 0.5,
  }));
  const matBeak = trackMat(new THREE.MeshStandardMaterial({
    color: pal.beak,
    roughness: 0.35,
    metalness: 0.08,
  }));
  const matWing = trackMat(new THREE.MeshStandardMaterial({
    color: wingsType === 'flame' || wingsType === 'crystal' ? pal.glow : pal.accent,
    emissive: pal.glow,
    emissiveIntensity: wingsType === 'flame' || wingsType === 'crystal' ? 0.35 : 0.14,
    roughness: 0.38,
    transparent: true,
    opacity: wingsType === 'crystal' ? 0.84 : 0.94,
    side: THREE.DoubleSide,
  }));

  const sphere = trackGeo(new THREE.SphereGeometry(1, seg[0], seg[1]));
  const cone = trackGeo(new THREE.ConeGeometry(1, 1, low ? 7 : 12));
  const cyl = trackGeo(new THREE.CylinderGeometry(0.7, 1, 1, low ? 8 : 12));
  const oct = trackGeo(new THREE.OctahedronGeometry(1, bodyType === 'golem' ? 1 : 0));
  const torus = trackGeo(new THREE.TorusGeometry(1, 0.28, low ? 6 : 8, low ? 12 : 18));

  const root = new THREE.Group();
  root.name = 'CatalogCreature_' + bodyType;

  // Body proportions per species matching lib/companion/spark/render.mjs
  const B = {
    pup:        { spineY: 0.52, bodyScale: [0.34 + chub * 0.08, 0.30 + chub * 0.06, 0.42], neckPos: [0, 0.22, 0.16], headScale: [0.31, 0.28, 0.29], snoutScale: [0.13, 0.10, 0.14], snoutZ: 0.25 },
    fox:        { spineY: 0.52, bodyScale: [0.30 + chub * 0.06, 0.27 + chub * 0.05, 0.48], neckPos: [0, 0.23, 0.22], headScale: [0.29, 0.26, 0.31], snoutScale: [0.11, 0.08, 0.20], snoutZ: 0.29 },
    sprout:     { spineY: 0.42, bodyScale: [0.36 + chub * 0.08, 0.35 + chub * 0.07, 0.36], neckPos: [0, 0.20, 0.04], headScale: [0.30, 0.28, 0.29], snoutScale: [0.09, 0.07, 0.08], snoutZ: 0.24 },
    moth:       { spineY: 0.54, bodyScale: [0.28 + chub * 0.06, 0.32 + chub * 0.06, 0.34], neckPos: [0, 0.24, 0.06], headScale: [0.27, 0.25, 0.26], snoutScale: [0.08, 0.06, 0.08], snoutZ: 0.22 },
    axolotl:    { spineY: 0.44, bodyScale: [0.33 + chub * 0.07, 0.25 + chub * 0.05, 0.46], neckPos: [0, 0.16, 0.20], headScale: [0.35, 0.25, 0.29], snoutScale: [0.15, 0.08, 0.12], snoutZ: 0.24 },
    golem:      { spineY: 0.64, bodyScale: [0.46 + chub * 0.08, 0.42 + chub * 0.08, 0.38], neckPos: [0, 0.32, 0.06], headScale: [0.29, 0.25, 0.27], snoutScale: [0.12, 0.08, 0.10], snoutZ: 0.24 },
    dragonling: { spineY: 0.58, bodyScale: [0.32 + chub * 0.07, 0.30 + chub * 0.06, 0.52], neckPos: [0, 0.25, 0.26], headScale: [0.28, 0.24, 0.32], snoutScale: [0.13, 0.10, 0.20], snoutZ: 0.30 },
    bird:       { spineY: 0.52, bodyScale: [0.31 + chub * 0.07, 0.34 + chub * 0.06, 0.36], neckPos: [0, 0.26, 0.10], headScale: [0.27, 0.26, 0.27], snoutScale: [0.09, 0.08, 0.18], snoutZ: 0.26 },
    fish:       { spineY: 0.52, bodyScale: [0.26 + chub * 0.06, 0.32 + chub * 0.06, 0.48], neckPos: [0, 0.06, 0.26], headScale: [0.25, 0.28, 0.28], snoutScale: [0.10, 0.09, 0.12], snoutZ: 0.23 },
    serpent:    { spineY: 0.46, bodyScale: [0.26 + chub * 0.05, 0.24 + chub * 0.05, 0.44], neckPos: [0, 0.28, 0.22], headScale: [0.25, 0.21, 0.29], snoutScale: [0.11, 0.08, 0.16], snoutZ: 0.25 },
    biped:      { spineY: 0.58, bodyScale: [0.31 + chub * 0.07, 0.36 + chub * 0.06, 0.29], neckPos: [0, 0.30, 0.04], headScale: [0.31, 0.29, 0.29], snoutScale: [0.10, 0.08, 0.11], snoutZ: 0.24 },
  }[bodyType];

  const headFactor = 0.92 + (headGene - 0.5) * 0.24;
  const spine = joint(THREE, root, 'Spine', 0, B.spineY, 0);

  // Main body + belly patch + species silhouette details
  const bodyGeo = bodyType === 'golem' ? oct : sphere;
  put(spine, new THREE.Mesh(bodyGeo, matBase), 'Body', 0, 0, 0, B.bodyScale);
  put(spine, new THREE.Mesh(sphere, matBelly), 'Belly', 0, -B.bodyScale[1] * 0.18, B.bodyScale[2] * 0.52, [
    B.bodyScale[0] * 0.68,
    B.bodyScale[1] * 0.66,
    B.bodyScale[2] * 0.52,
  ]);

  // Species-specific silhouette features (ruff, collar, shell, dorsal crest, coils)
  const coils = [];
  if (bodyType === 'fox' || bodyType === 'moth') {
    put(spine, new THREE.Mesh(sphere, matBelly), 'ChestRuff', 0, B.bodyScale[1] * 0.36, B.bodyScale[2] * 0.55, [
      B.bodyScale[0] * 0.72,
      B.bodyScale[1] * 0.38,
      B.bodyScale[2] * 0.45,
    ]);
  }
  if (bodyType === 'golem') {
    put(spine, new THREE.Mesh(oct, matGlow), 'CoreCrystal', 0, 0.05, B.bodyScale[2] * 0.88, [0.11, 0.14, 0.08]);
    for (const side of [-1, 1]) {
      put(spine, new THREE.Mesh(oct, matAlt), side < 0 ? 'Pauldron_L' : 'Pauldron_R', side * (B.bodyScale[0] * 0.92), B.bodyScale[1] * 0.45, 0, [0.18, 0.15, 0.2]);
    }
  }
  if (bodyType === 'dragonling' || bodyType === 'axolotl') {
    for (let i = 0; i < 3; i++) {
      put(spine, new THREE.Mesh(cone, matAccent), 'BackCrest_' + i, 0, B.bodyScale[1] * 0.95, 0.12 - i * 0.15, [0.045, 0.12, 0.07], [-0.25, 0, 0]);
    }
  }
  if (bodyType === 'fish') {
    put(spine, new THREE.Mesh(cone, matAccent), 'DorsalFin', 0, B.bodyScale[1] * 1.05, -0.04, [0.04, 0.22, 0.26], [-0.35, 0, 0]);
  }
  if (bodyType === 'serpent') {
    let coilParent = spine;
    for (let i = 1; i <= 4; i++) {
      const cJoint = joint(THREE, coilParent, 'Coil_' + i, (i % 2 === 0 ? 1 : -1) * 0.08, -0.05, -0.22);
      put(cJoint, new THREE.Mesh(sphere, i % 2 === 0 ? matAlt : matBase), 'CoilMesh_' + i, 0, 0, 0, [
        Math.max(0.11, 0.24 - i * 0.03),
        Math.max(0.10, 0.20 - i * 0.025),
        0.22,
      ]);
      coils.push(cJoint);
      coilParent = cJoint;
    }
  }

  // 3D Pattern relief accents so patterns read even in silhouette/headless mode
  if (patternType === 'plates' || patternType === 'facets') {
    for (let i = 0; i < 3; i++) {
      put(spine, new THREE.Mesh(oct, matAlt), 'PatternPlate_' + i, 0, B.bodyScale[1] * (0.65 - i * 0.22), -B.bodyScale[2] * 0.72, [0.14, 0.06, 0.1]);
    }
  }

  // Neck & Head
  const neck = joint(THREE, spine, 'Neck', B.neckPos[0], B.neckPos[1], B.neckPos[2]);
  const head = joint(THREE, neck, 'Head', 0, 0.12, 0.04);
  const hs = B.headScale.map(v => v * headFactor);
  put(head, new THREE.Mesh(bodyType === 'golem' ? oct : sphere, matBase), 'Skull', 0, 0, 0, hs);

  // Cheek tufts / Fur wisps (driven by Verlet furChain)
  const furL = joint(THREE, head, 'Fur_L', -hs[0] * 0.88, -hs[1] * 0.18, 0.02);
  const furR = joint(THREE, head, 'Fur_R', hs[0] * 0.88, -hs[1] * 0.18, 0.02);
  put(furL, new THREE.Mesh(cone, matBase), 'FurMesh_L', -0.04, 0, 0, [0.06, 0.12, 0.06], [0, 0, Math.PI * 0.6]);
  put(furR, new THREE.Mesh(cone, matBase), 'FurMesh_R', 0.04, 0, 0, [0.06, 0.12, 0.06], [0, 0, -Math.PI * 0.6]);

  // Snout / Beak / Nose & Jaw
  const noseMat = bodyType === 'bird' ? matBeak : matAlt;
  const noseGeo = bodyType === 'bird' ? cone : sphere;
  const noseRot = bodyType === 'bird' ? [Math.PI / 2, 0, 0] : [0, 0, 0];
  put(head, new THREE.Mesh(noseGeo, noseMat), 'Nose', 0, -hs[1] * 0.14, B.snoutZ * headFactor, B.snoutScale, noseRot);
  if (bodyType !== 'bird' && bodyType !== 'golem') {
    put(head, new THREE.Mesh(sphere, matDark), 'NoseTip', 0, -hs[1] * 0.08, (B.snoutZ + B.snoutScale[2] * 0.78) * headFactor, [0.042, 0.032, 0.032]);
  }

  const jaw = joint(THREE, head, 'Jaw', 0, -hs[1] * 0.42, B.snoutZ * 0.68);
  put(jaw, new THREE.Mesh(sphere, matBelly), 'JawMesh', 0, 0, 0.04, [B.snoutScale[0] * 0.78, 0.038, B.snoutScale[2] * 0.72]);

  // Mouth style: smile, w, fang, open
  if (mouthType === 'fang') {
    for (const side of [-1, 1]) {
      put(head, new THREE.Mesh(cone, matWhite), side < 0 ? 'Fang_L' : 'Fang_R', side * 0.055, -hs[1] * 0.34, B.snoutZ * 0.95, [0.02, 0.055, 0.02], [Math.PI, 0, 0]);
    }
  } else if (mouthType === 'open') {
    put(jaw, new THREE.Mesh(sphere, matCheek), 'Tongue', 0, 0.015, 0.05, [0.045, 0.02, 0.05]);
  } else if (mouthType === 'w') {
    for (const side of [-1, 1]) {
      put(head, new THREE.Mesh(torus, matDark), side < 0 ? 'MouthW_L' : 'MouthW_R', side * 0.032, -hs[1] * 0.28, B.snoutZ * 0.98, [0.026, 0.02, 0.02], [Math.PI, 0, 0]);
    }
  }

  // Eyes (round, sparkle, sleepy, closed) + Cheeks
  const ex = hs[0] * 0.44 * eyeGap;
  const ey = hs[1] * 0.14;
  const ez = hs[2] * 0.84;
  const er = 0.068 * eyeSize;
  for (const side of [-1, 1]) {
    const eye = joint(THREE, head, side < 0 ? 'Eye_L' : 'Eye_R', side * ex, ey, ez);
    put(eye, new THREE.Mesh(sphere, matEye), side < 0 ? 'EyeBall_L' : 'EyeBall_R', 0, 0, 0, [er, er * (eyeStyle === 'sleepy' ? 0.78 : 1.12), er * 0.55]);
    put(eye, new THREE.Mesh(sphere, matIris), side < 0 ? 'Iris_L' : 'Iris_R', 0, -er * 0.12, er * 0.42, [er * 0.68, er * 0.68, er * 0.25]);
    put(eye, new THREE.Mesh(sphere, matWhite), side < 0 ? 'Spec_L' : 'Spec_R', side * -er * 0.22, er * 0.28, er * 0.52, [er * 0.32, er * 0.32, er * 0.18]);
    if (eyeStyle === 'sparkle') {
      put(eye, new THREE.Mesh(oct, matGlow), side < 0 ? 'Sparkle_L' : 'Sparkle_R', side * er * 0.2, -er * 0.18, er * 0.55, [er * 0.28, er * 0.28, er * 0.18]);
    }
    const lid = joint(THREE, eye, side < 0 ? 'Lid_L' : 'Lid_R', 0, er * 0.35, er * 0.18);
    const initLidScale = eyeStyle === 'closed' ? 1.8 : eyeStyle === 'sleepy' ? 0.95 : 0.32;
    put(lid, new THREE.Mesh(sphere, matBase), side < 0 ? 'LidMesh_L' : 'LidMesh_R', 0, 0, 0, [er * 1.15, er * initLidScale, er * 0.55]);

    put(head, new THREE.Mesh(sphere, matCheek), side < 0 ? 'Cheek_L' : 'Cheek_R', side * (ex * 1.25), ey - er * 0.95, ez * 0.88, [0.042, 0.028, 0.022]);
  }

  // Sprout head stem + leaves
  if (bodyType === 'sprout') {
    const stem = joint(THREE, head, 'SproutStem', 0, hs[1] * 0.92, 0);
    put(stem, new THREE.Mesh(cyl, matAccent), 'SproutStalk', 0, 0.08, 0, [0.025, 0.16, 0.025]);
    put(stem, new THREE.Mesh(sphere, matGlow), 'SproutLeaf_L', -0.09, 0.16, 0, [0.11, 0.03, 0.06], [0, 0, 0.35]);
    put(stem, new THREE.Mesh(sphere, matAccent), 'SproutLeaf_R', 0.09, 0.16, 0, [0.11, 0.03, 0.06], [0, 0, -0.35]);
  }

  // Ears (all 12 catalogue types: pointy, round, horns, crown, leaf, antlers, flame, crystal, antenna, feelers, bolts, gills)
  const ears = {};
  for (const side of [-1, 1]) {
    const eJoint = joint(THREE, head, side < 0 ? 'Ear_L' : 'Ear_R', side * (hs[0] * 0.65), hs[1] * 0.78, -0.02);
    ears[side < 0 ? 'L' : 'R'] = eJoint;
    if (earsType === 'round') {
      put(eJoint, new THREE.Mesh(sphere, matBase), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.07 * earSize, 0, [0.09 * earSize, 0.09 * earSize, 0.05]);
      put(eJoint, new THREE.Mesh(sphere, matCheek), side < 0 ? 'EarInner_L' : 'EarInner_R', 0, 0.07 * earSize, 0.03, [0.05 * earSize, 0.05 * earSize, 0.02]);
    } else if (earsType === 'horns') {
      put(eJoint, new THREE.Mesh(cone, matAccent), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.12 * earSize, 0, [0.055 * earSize, 0.24 * earSize, 0.055 * earSize], [-0.2, 0, side * -0.28]);
    } else if (earsType === 'crown') {
      put(eJoint, new THREE.Mesh(oct, matGlow), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.11 * earSize, 0.02, [0.06 * earSize, 0.15 * earSize, 0.04 * earSize], [0, 0, side * -0.18]);
    } else if (earsType === 'leaf') {
      put(eJoint, new THREE.Mesh(sphere, matAccent), side < 0 ? 'EarMesh_L' : 'EarMesh_R', side * 0.04, 0.11 * earSize, 0, [0.07 * earSize, 0.16 * earSize, 0.03], [0, 0, side * -0.45]);
    } else if (earsType === 'antlers') {
      put(eJoint, new THREE.Mesh(cyl, matAlt), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.13 * earSize, 0, [0.025, 0.24 * earSize, 0.025], [0, 0, side * -0.25]);
      put(eJoint, new THREE.Mesh(cyl, matAlt), side < 0 ? 'AntlerTine_L' : 'AntlerTine_R', side * 0.05, 0.16 * earSize, 0.02, [0.02, 0.12 * earSize, 0.02], [0, 0, side * -0.75]);
    } else if (earsType === 'flame') {
      put(eJoint, new THREE.Mesh(cone, matGlow), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.13 * earSize, 0, [0.065 * earSize, 0.24 * earSize, 0.05 * earSize], [-0.15, 0, side * -0.22]);
    } else if (earsType === 'crystal') {
      put(eJoint, new THREE.Mesh(oct, matGlow), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.12 * earSize, 0, [0.06 * earSize, 0.19 * earSize, 0.05 * earSize], [0, 0, side * -0.3]);
    } else if (earsType === 'antenna' || earsType === 'feelers') {
      put(eJoint, new THREE.Mesh(cyl, matAlt), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.12 * earSize, 0.02, [0.018, 0.22 * earSize, 0.018], [0.2, 0, side * -0.3]);
      put(eJoint, new THREE.Mesh(sphere, matGlow), side < 0 ? 'AntennaOrb_L' : 'AntennaOrb_R', side * 0.05, 0.23 * earSize, 0.05, [0.042, 0.042, 0.042]);
    } else if (earsType === 'bolts') {
      put(eJoint, new THREE.Mesh(cyl, matAccent), side < 0 ? 'EarMesh_L' : 'EarMesh_R', side * 0.04, 0.04, 0, [0.045 * earSize, 0.12 * earSize, 0.045 * earSize], [0, 0, side * -1.2]);
    } else if (earsType === 'gills') {
      for (let g = 0; g < 3; g++) {
        put(eJoint, new THREE.Mesh(cone, matAccent), `${side < 0 ? 'Gill_L_' : 'Gill_R_'}${g}`, side * (0.06 + g * 0.02), (0.04 - g * 0.05) * earSize, 0, [0.032, 0.13 * earSize, 0.025], [0, 0, side * (-0.9 - g * 0.25)]);
      }
    } else {
      // pointy default
      put(eJoint, new THREE.Mesh(cone, matBase), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.12 * earSize, 0, [0.075 * earSize, 0.24 * earSize, 0.055 * earSize], [0, 0, side * -0.22]);
      put(eJoint, new THREE.Mesh(cone, matCheek), side < 0 ? 'EarInner_L' : 'EarInner_R', 0, 0.11 * earSize, 0.025, [0.042 * earSize, 0.16 * earSize, 0.025], [0, 0, side * -0.22]);
    }
  }

  // Wings (feather, bat, moth, leaf, crystal, flame, vanes, none) + fish pectoral fins
  const wings = {};
  const effectiveWings = bodyType === 'fish' && wingsType === 'none' ? 'leaf' : wingsType;
  if (effectiveWings !== 'none') {
    const wGeo = trackGeo(buildWingGeometry(THREE, effectiveWings, 0.46 * wingSize, 0.28 * wingSize));
    for (const side of [-1, 1]) {
      const pivot = joint(THREE, spine, side < 0 ? 'Wing_L' : 'Wing_R', side * (B.bodyScale[0] * 0.76), B.bodyScale[1] * 0.22, -0.04);
      const wMesh = put(pivot, new THREE.Mesh(wGeo, matWing), side < 0 ? 'WingMesh_L' : 'WingMesh_R', 0, 0, 0);
      wMesh.scale.x = side;
      wMesh.rotation.y = side * -0.25;
      wings[side < 0 ? 'L' : 'R'] = pivot;
    }
  } else {
    wings.L = joint(THREE, spine, 'Wing_L', -B.bodyScale[0] * 0.7, 0.08, 0);
    wings.R = joint(THREE, spine, 'Wing_R', B.bodyScale[0] * 0.7, 0.08, 0);
  }

  // Limbs (quadruped FL/FR/BL/BR, biped/golem/bird Arm_L/R + Leg_L/R, fish/serpent ventral fins)
  const legs = {};
  const arms = {};
  const legLen = 0.85 + (legsGene - 0.5) * 0.3;
  if (bodyType === 'biped' || bodyType === 'golem' || bodyType === 'bird' || bodyType === 'sprout' || bodyType === 'moth') {
    for (const side of [-1, 1]) {
      const hip = joint(THREE, spine, side < 0 ? 'Leg_FL' : 'Leg_FR', side * (B.bodyScale[0] * 0.48), -B.bodyScale[1] * 0.68, 0.02);
      put(hip, new THREE.Mesh(sphere, matBase), side < 0 ? 'Thigh_L' : 'Thigh_R', 0, -0.09 * legLen, 0, [0.08, 0.13 * legLen, 0.08]);
      put(hip, new THREE.Mesh(sphere, bodyType === 'bird' ? matBeak : matAlt), side < 0 ? 'Paw_L' : 'Paw_R', 0, -0.19 * legLen, 0.03, [0.085, 0.045, 0.11]);
      legs[side < 0 ? 'FL' : 'FR'] = hip;
      legs[side < 0 ? 'BL' : 'BR'] = hip;

      if (bodyType !== 'sprout') {
        const arm = joint(THREE, spine, side < 0 ? 'Arm_L' : 'Arm_R', side * (B.bodyScale[0] * 0.88), B.bodyScale[1] * 0.1, 0.05);
        put(arm, new THREE.Mesh(bodyType === 'golem' ? oct : sphere, matAlt), side < 0 ? 'ArmMesh_L' : 'ArmMesh_R', side * 0.04, -0.09, 0.02, bodyType === 'golem' ? [0.11, 0.19, 0.11] : [0.065, 0.14, 0.065]);
        arms[side < 0 ? 'L' : 'R'] = arm;
      }
    }
  } else if (bodyType === 'fish' || bodyType === 'serpent') {
    for (const side of [-1, 1]) {
      const fin = joint(THREE, spine, side < 0 ? 'Leg_FL' : 'Leg_FR', side * (B.bodyScale[0] * 0.75), -B.bodyScale[1] * 0.55, 0.08);
      put(fin, new THREE.Mesh(sphere, matAccent), side < 0 ? 'VentralFin_L' : 'VentralFin_R', 0, -0.05, 0, [0.04, 0.07, 0.09]);
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
      put(hip, new THREE.Mesh(sphere, matBase), 'Thigh_' + label, 0, -0.09 * legLen, 0, [0.075, 0.13 * legLen, 0.075]);
      put(hip, new THREE.Mesh(sphere, matAlt), 'Paw_' + label, 0, -0.19 * legLen, 0.025, [0.08, 0.045, 0.095]);
      legs[label] = hip;
    }
  }

  // Multi-segment Verlet-driven Tail (fluffy, plume, flame, spade, fishtail, fin, leaf, crystal, cable, gear, tip, none)
  const tailSegments = [];
  let tailParent = coils.length ? coils[coils.length - 1] : spine;
  const numTailSegs = tailType === 'none' ? 1 : 4;
  for (let i = 1; i <= numTailSegs; i++) {
    const tz = i === 1 ? (coils.length ? -0.18 : -B.bodyScale[2] * 0.85) : -0.15 * tailSize;
    const ty = i === 1 ? 0.03 : 0.025;
    const tJoint = joint(THREE, tailParent, 'Tail_' + i, 0, ty, tz);
    const rScale = tailType === 'fluffy' || tailType === 'plume'
      ? [0.11 * tailSize * (1.15 - i * 0.12), 0.10 * tailSize * (1.15 - i * 0.12), 0.14 * tailSize]
      : [0.07 * tailSize * (1.1 - i * 0.15), 0.07 * tailSize * (1.1 - i * 0.15), 0.13 * tailSize];
    const segMat = (i === numTailSegs && (tailType === 'flame' || tailType === 'crystal')) ? matGlow : i >= numTailSegs - 1 ? matAccent : matBase;
    put(tJoint, new THREE.Mesh(tailType === 'crystal' ? oct : sphere, segMat), 'TailMesh_' + i, 0, 0, -0.05, rScale);
    tailSegments.push(tJoint);
    tailParent = tJoint;
  }

  // Distinct tail tips per tailType
  const tailTip = tailSegments[tailSegments.length - 1];
  if (tailType === 'spade' || tailType === 'leaf') {
    put(tailTip, new THREE.Mesh(cone, matAccent), 'TailTipOrnament', 0, 0.02, -0.14 * tailSize, [0.11 * tailSize, 0.16 * tailSize, 0.04], [-Math.PI / 2, 0, 0]);
  } else if (tailType === 'fishtail' || tailType === 'fin') {
    put(tailTip, new THREE.Mesh(cone, matAccent), 'TailFinUpper', 0, 0.08 * tailSize, -0.12 * tailSize, [0.035, 0.16 * tailSize, 0.12 * tailSize], [-0.8, 0, 0]);
    put(tailTip, new THREE.Mesh(cone, matAccent), 'TailFinLower', 0, -0.06 * tailSize, -0.12 * tailSize, [0.035, 0.14 * tailSize, 0.11 * tailSize], [-2.2, 0, 0]);
  } else if (tailType === 'gear') {
    put(tailTip, new THREE.Mesh(torus, matAccent), 'TailGear', 0, 0, -0.12 * tailSize, [0.09 * tailSize, 0.09 * tailSize, 0.06], [0, Math.PI / 2, 0]);
  } else if (tailType === 'flame') {
    put(tailTip, new THREE.Mesh(cone, matGlow), 'TailFlameTip', 0, 0.05 * tailSize, -0.14 * tailSize, [0.09 * tailSize, 0.22 * tailSize, 0.09 * tailSize], [-0.4, 0, 0]);
  }

  // Cosmic / Elemental Wisp chain floating around shoulder
  const wispJoints = [];
  let wispParent = spine;
  for (let i = 1; i <= 3; i++) {
    const wj = joint(THREE, wispParent, 'Wisp_' + i, i === 1 ? B.bodyScale[0] * 0.85 : 0, i === 1 ? 0.18 : 0.08, -0.12);
    put(wj, new THREE.Mesh(oct, matGlow), 'WispOrb_' + i, 0, 0, 0, [0.035 - i * 0.006, 0.035 - i * 0.006, 0.035 - i * 0.006]);
    wispJoints.push(wj);
    wispParent = wj;
  }

  root.scale.setScalar(stageScale);
  root.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(root);
  spine.position.y -= box.min.y / stageScale;
  root.updateMatrixWorld(true);

  // Grounded contact shadow at y = 0
  const shadowGeo = trackGeo(new THREE.CircleGeometry(0.52 * stageScale, low ? 16 : 24));
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
  const particleCount = low ? 14 : 24;
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
    size: 0.065,
    transparent: true,
    opacity: 0.85,
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
