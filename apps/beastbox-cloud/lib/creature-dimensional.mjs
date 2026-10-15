/**
 * Articulated 3D companions for the existing Three.js renderer.
 *
 * These meshes are artistic representations. They are not measured quantum
 * phenotypes, and a display name never selects one.
 *
 * Moonwraith display persona bb-7f9c2a03: black moon-cat/dragon, violet
 * accents, star eyes, crescent horns, sculpted ear pinna, gem collar.
 * Saved Zeref bb-deada969: a different dragonling silhouette. It must not
 * wear the Moonwraith body.
 */
import {
  createSecondaryMotion,
  stepSecondaryMotion,
  ELEMENT_FLUID_PROFILES,
} from './companion/fluid-motion.mjs';

export const MOONWRAITH_DISPLAY_ID = 'bb-7f9c2a03';
export const SAVED_ZEREF_ID = 'bb-deada969';

const PALETTE = {
  'moonwraith-artistic': {
    fur: 0x160d2a,
    lit: 0x422870,
    accent: 0xc288ff,
    eye: 0xf0e2ff,
    wing: 0x7c44dc,
    belly: 0x2f1a52,
    horn: 0xf8f0ff,
    pupil: 0x260b58,
    gem: 0xff66cc,
    pink: 0xff88cc,
  },
  'dragonling-artistic': {
    fur: 0x8e3d24,
    lit: 0xe69f58,
    accent: 0xf6c854,
    eye: 0xffebb2,
    wing: 0x62294a,
    belly: 0xf6d8bc,
    horn: 0x5c241c,
    pupil: 0x2a1208,
    gem: 0xff9933,
    pink: 0xe07a5f,
  },
};

export function dimensionalKind({id} = {}) {
  if (id === MOONWRAITH_DISPLAY_ID) return 'moonwraith-artistic';
  if (id === SAVED_ZEREF_ID) return 'dragonling-artistic';
  return null;
}

export function dimensionalAttribution(kind) {
  if (kind === 'moonwraith-artistic') {
    return {
      identityId: MOONWRAITH_DISPLAY_ID,
      kind,
      phenotype: 'artistic-representation',
      label: 'Artistic 3D representation of the Moonwraith display persona. Not saved Zeref and not a measured quantum phenotype.',
    };
  }
  if (kind === 'dragonling-artistic') {
    return {
      identityId: SAVED_ZEREF_ID,
      kind,
      phenotype: 'artistic-representation',
      label: 'Artistic 3D representation of the recorded dragonling silhouette for saved Zeref. Not the Moonwraith and not a newly measured quantum phenotype.',
    };
  }
  return null;
}

function material(THREE, color, extra = {}) {
  const Mat = THREE.MeshPhysicalMaterial || THREE.MeshStandardMaterial;
  return new Mat({
    color,
    roughness: extra.roughness ?? 0.38,
    metalness: extra.metalness ?? 0.08,
    clearcoat: extra.clearcoat ?? 0.42,
    clearcoatRoughness: 0.2,
    emissive: extra.emissive ?? 0x000000,
    emissiveIntensity: extra.emissiveIntensity ?? 0,
  });
}

function joint(THREE, parent, name, x, y, z) {
  const group = new THREE.Group();
  group.name = name;
  group.position.set(x, y, z);
  parent.add(group);
  return group;
}

function put(parent, mesh, name, x, y, z, scale, rot) {
  mesh.name = name;
  mesh.position.set(x, y, z);
  if (scale) mesh.scale.set(scale[0], scale[1], scale[2]);
  if (rot) mesh.rotation.set(rot[0], rot[1], rot[2]);
  parent.add(mesh);
  return mesh;
}

function buildSculptedDimensionalSkull(THREE, moon, seg) {
  const g = new THREE.SphereGeometry(1, seg[0], seg[1]);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const ax = Math.abs(x);
    if (y > 0) {
      y *= 0.86;
      x *= 1 + 0.06 * (1 - y);
    } else {
      const cheek = Math.max(0, 1 - Math.abs(y + 0.24) * 2.5) * (moon ? 0.22 : 0.14);
      x *= 1 + cheek;
      z *= 1 + cheek * 0.4;
      if (y < -0.55) y *= 0.88;
    }
    if (z > 0.2 && y < 0.08 && y > -0.65 && ax < 0.55) {
      const muzzle = (1 - ax / 0.55) * Math.max(0, 1 - Math.abs(y + 0.22) * 2.4);
      z += muzzle * (moon ? 0.18 : 0.30);
    }
    if (z < 0) z *= 0.88;
    pos.setXYZ(i, x, y, z);
  }
  pos.needsUpdate = true;
  g.computeVertexNormals();
  return g;
}

function buildSculptedDimensionalTorso(THREE, moon, seg) {
  const g = new THREE.SphereGeometry(1, seg[0], seg[1]);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    if (moon) {
      const hipFlare = y < 0 ? 1 + Math.abs(y) * 0.18 : 1 - y * 0.10;
      x *= hipFlare;
      if (z > 0 && y > -0.25) z *= 1.12;
      if (y < -0.68) y = -0.68 + (y + 0.68) * 0.35;
    } else {
      const chestPower = z > 0 ? 1.12 : 0.90;
      x *= chestPower;
      y *= z > 0 ? 1.08 : 0.88;
    }
    pos.setXYZ(i, x, y, z);
  }
  pos.needsUpdate = true;
  g.computeVertexNormals();
  return g;
}

function buildSculptedEar(THREE, low) {
  const g = new THREE.ConeGeometry(0.14, 0.36, low ? 10 : 16, low ? 4 : 6);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const t = Math.max(0, Math.min(1, (y + 0.18) / 0.36));
    const widthCurve = Math.sin(t * Math.PI * 0.85) * 0.35 + (1 - t) * 0.85;
    x *= widthCurve;
    if (z > 0 && Math.abs(x) < 0.08 && t > 0.15 && t < 0.85) z *= 0.42;
    z -= t * t * 0.04;
    pos.setXYZ(i, x, y, z);
  }
  pos.needsUpdate = true;
  g.computeVertexNormals();
  return g;
}

function buildStar4Geo(THREE, radius = 0.048) {
  const shape = new THREE.Shape();
  for (let i = 0; i < 8; i++) {
    const r = i % 2 === 0 ? radius : radius * 0.28;
    const a = (i * Math.PI) / 4;
    const x = Math.cos(a) * r;
    const y = Math.sin(a) * r;
    if (i === 0) shape.moveTo(x, y);
    else shape.lineTo(x, y);
  }
  shape.closePath();
  return new THREE.ExtrudeGeometry(shape, {depth: 0.012, bevelEnabled: false});
}

function wingShape(THREE, span, lift) {
  const shape = new THREE.Shape();
  shape.moveTo(0, 0);
  shape.bezierCurveTo(span * 0.25, lift * 1.18, span * 0.7, lift * 1.22, span, lift * 0.38);
  shape.quadraticCurveTo(span * 0.84, 0.04, span * 0.76, -lift * 0.22);
  shape.quadraticCurveTo(span * 0.56, 0.0, span * 0.42, -lift * 0.45);
  shape.quadraticCurveTo(span * 0.20, -0.04, 0.02, -0.06);
  shape.closePath();
  return new THREE.ExtrudeGeometry(shape, {depth: 0.052, bevelEnabled: true, bevelThickness: 0.014, bevelSize: 0.012, bevelSegments: 2});
}

/**
 * @param {typeof import('three')} THREE
 * @param {'moonwraith-artistic'|'dragonling-artistic'} kind
 */
export function buildDimensionalRig(THREE, kind, {quality = 'auto'} = {}) {
  const attribution = dimensionalAttribution(kind);
  if (!attribution) throw new Error('Unknown dimensional creature');
  const moon = kind === 'moonwraith-artistic';
  const colors = PALETTE[kind];
  const low = quality === 'low';
  const seg = low ? [14, 10] : [20, 16];
  const geometries = [];
  const materials = [];
  const trackGeo = geometry => {geometries.push(geometry); return geometry;};
  const trackMat = value => {materials.push(value); return value;};
  const fur = trackMat(material(THREE, colors.fur, {emissive: colors.lit, emissiveIntensity: 0.14}));
  const lit = trackMat(material(THREE, colors.lit, {emissive: colors.accent, emissiveIntensity: 0.16}));
  const belly = trackMat(material(THREE, colors.belly, {emissive: colors.belly, emissiveIntensity: 0.08}));
  const accent = trackMat(material(THREE, colors.accent, {emissive: colors.accent, emissiveIntensity: moon ? 0.52 : 0.34, roughness: 0.22, clearcoat: 0.8}));
  const gemMat = trackMat(material(THREE, colors.gem, {emissive: colors.gem, emissiveIntensity: 0.78, roughness: 0.12, clearcoat: 1.0}));
  const pinkMat = trackMat(material(THREE, colors.pink, {emissive: colors.pink, emissiveIntensity: 0.35, roughness: 0.35}));
  const eyeWhite = trackMat(material(THREE, colors.eye, {emissive: colors.eye, emissiveIntensity: moon ? 0.92 : 0.55, roughness: 0.12, clearcoat: 1.0}));
  const pupil = trackMat(material(THREE, colors.pupil, {roughness: 0.12, clearcoat: 1.0}));
  const wingMat = trackMat(material(THREE, colors.wing, {emissive: colors.accent, emissiveIntensity: 0.26, roughness: 0.32, clearcoat: 0.7, transparent: true, opacity: 0.94}));
  wingMat.transparent = true;
  wingMat.opacity = 0.94;
  wingMat.side = THREE.DoubleSide;

  const sphere = trackGeo(new THREE.SphereGeometry(1, low ? 12 : 16, low ? 10 : 12));
  const skullGeo = trackGeo(buildSculptedDimensionalSkull(THREE, moon, seg));
  const torsoGeo = trackGeo(buildSculptedDimensionalTorso(THREE, moon, seg));
  const earGeo = trackGeo(buildSculptedEar(THREE, low));
  const cone = trackGeo(new THREE.ConeGeometry(0.12, moon ? 0.34 : 0.18, low ? 8 : 12));
  const star = trackGeo(moon ? buildStar4Geo(THREE, 0.048) : new THREE.OctahedronGeometry(0.022, 0));
  const octGem = trackGeo(new THREE.OctahedronGeometry(0.065, 0));
  const wingGeo = trackGeo(wingShape(THREE, moon ? 0.92 : 0.62, moon ? 0.42 : 0.28));
  const crescent = moon ? trackGeo(new THREE.TorusGeometry(0.115, 0.030, low ? 8 : 10, low ? 14 : 20, Math.PI * 1.28)) : null;
  const collarTorus = moon ? trackGeo(new THREE.TorusGeometry(0.24, 0.026, 8, 18)) : null;

  const root = new THREE.Group();
  root.name = 'DimensionalCreature';
  root.userData = {...attribution, triangles: 0};

  const spine = joint(THREE, root, 'Spine', 0, moon ? 0.78 : 0.62, 0);
  put(spine, new THREE.Mesh(torsoGeo, fur), 'Body', 0, 0, 0, moon ? [0.52, 0.46, 0.4] : [0.34, 0.3, 0.78]);
  put(spine, new THREE.Mesh(sphere, belly), 'Belly', 0, moon ? -0.06 : -0.06, moon ? 0.16 : 0.18, moon ? [0.32, 0.26, 0.22] : [0.22, 0.16, 0.38]);

  if (moon) {
    put(spine, new THREE.Mesh(sphere, lit), 'ChestRuff', 0, 0.16, 0.24, [0.28, 0.16, 0.18]);
    const collar = put(spine, new THREE.Mesh(collarTorus, lit), 'Collar', 0, 0.25, 0.06, [1, 1, 0.9], [Math.PI * 0.48, 0, 0]);
    void collar;
    put(spine, new THREE.Mesh(octGem, gemMat), 'GemChoker', 0, 0.22, 0.30, [1.0, 1.25, 0.7]);
  } else {
    for (let i = 0; i < 4; i++) {
      put(spine, new THREE.Mesh(cone, accent), 'DorsalSpike_' + i, 0, 0.28 - i * 0.03, 0.18 - i * 0.22, [0.45, 0.65, 0.55], [-0.32, 0, 0]);
    }
  }

  const neck = joint(THREE, spine, 'Neck', 0, moon ? 0.28 : 0.16, moon ? 0.06 : 0.48);
  const head = joint(THREE, neck, 'Head', 0, moon ? 0.22 : 0.08, moon ? 0.02 : 0.16);
  put(head, new THREE.Mesh(skullGeo, fur), 'Skull', 0, 0, 0, moon ? [0.37, 0.33, 0.34] : [0.25, 0.21, 0.29]);

  if (moon) {
    put(head, new THREE.Mesh(earGeo, lit), 'CrownTuft', 0, 0.32, 0.06, [0.45, 0.42, 0.45], [-0.25, 0, 0]);
    put(head, new THREE.Mesh(octGem, accent), 'ForeheadStar', 0, 0.15, 0.32, [0.45, 0.65, 0.30]);
  }

  const nose = put(head, new THREE.Mesh(sphere, lit), 'Nose', 0, moon ? -0.04 : -0.02, moon ? 0.29 : 0.42, moon ? [0.13, 0.095, 0.14] : [0.11, 0.085, 0.28]);
  put(head, new THREE.Mesh(sphere, pinkMat), 'NoseTip', 0, moon ? -0.01 : 0.01, moon ? 0.41 : 0.66, [0.038, 0.028, 0.03]);

  const jaw = joint(THREE, head, 'Jaw', 0, -0.08, moon ? 0.12 : 0.2);
  put(jaw, new THREE.Mesh(sphere, belly), 'JawMesh', 0, 0, 0.06, moon ? [0.11, 0.045, 0.09] : [0.085, 0.038, 0.13]);

  const eyeGeoParent = head;
  for (const side of [-1, 1]) {
    const eye = joint(THREE, eyeGeoParent, side < 0 ? 'Eye_L' : 'Eye_R', side * (moon ? 0.145 : 0.105), moon ? 0.055 : 0.04, moon ? 0.25 : 0.19);
    put(eye, new THREE.Mesh(sphere, pupil), side < 0 ? 'EyeSocket_L' : 'EyeSocket_R', 0, 0, -0.006, moon ? [0.088, 0.102, 0.042] : [0.064, 0.08, 0.038]);
    put(eye, new THREE.Mesh(sphere, eyeWhite), side < 0 ? 'EyeWhite_L' : 'EyeWhite_R', 0, 0, 0, moon ? [0.078, 0.092, 0.042] : [0.056, 0.072, 0.036]);
    if (moon) {
      put(eye, new THREE.Mesh(sphere, gemMat), side < 0 ? 'IrisRing_L' : 'IrisRing_R', 0, -0.005, 0.024, [0.055, 0.065, 0.025]);
      put(eye, new THREE.Mesh(star, accent), side < 0 ? 'Star_L' : 'Star_R', -side * 0.012, 0.014, 0.042);
    } else {
      put(eye, new THREE.Mesh(star, pupil), side < 0 ? 'Slit_L' : 'Slit_R', 0, 0, 0.032, [0.35, 1.4, 0.4]);
    }
    const lid = joint(THREE, eye, side < 0 ? 'Lid_L' : 'Lid_R', 0, 0.022, 0.032);
    put(lid, new THREE.Mesh(sphere, fur), side < 0 ? 'LidMesh_L' : 'LidMesh_R', 0, 0, 0, [0.092, 0.036, 0.032]);
    put(head, new THREE.Mesh(sphere, pinkMat), side < 0 ? 'CheekGlow_L' : 'CheekGlow_R', side * (moon ? 0.22 : 0.15), -0.03, moon ? 0.22 : 0.16, [0.045, 0.028, 0.025]);
  }

  if (moon) {
    for (const side of [-1, 1]) {
      const ear = joint(THREE, head, side < 0 ? 'Ear_L' : 'Ear_R', side * 0.21, 0.26, -0.02);
      const earMesh = put(ear, new THREE.Mesh(earGeo, fur), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.13, 0);
      earMesh.rotation.z = side * -0.25;
      const earInner = put(ear, new THREE.Mesh(earGeo, pinkMat), side < 0 ? 'EarInner_L' : 'EarInner_R', 0, 0.12, 0.018, [0.58, 0.76, 0.45]);
      earInner.rotation.z = side * -0.25;
      const horn = joint(THREE, head, side < 0 ? 'Crescent_L' : 'Crescent_R', side * 0.16, 0.18, 0.02);
      const crescentMesh = put(horn, new THREE.Mesh(crescent, accent), side < 0 ? 'CrescentMesh_L' : 'CrescentMesh_R', 0, 0.08, 0);
      crescentMesh.rotation.z = side * 0.6;
      crescentMesh.rotation.y = side * -0.4;
    }
  } else {
    const hornMat = trackMat(material(THREE, colors.horn, {roughness: 0.3, clearcoat: 0.5}));
    for (const side of [-1, 1]) {
      const horn = joint(THREE, head, side < 0 ? 'Horn_L' : 'Horn_R', side * 0.1, 0.16, 0.02);
      put(horn, new THREE.Mesh(cone, hornMat), side < 0 ? 'HornMesh_L' : 'HornMesh_R', 0, 0.08, 0, [0.7, 1.05, 0.7], [-0.28, 0, side * -0.18]);
    }
    put(spine, new THREE.Mesh(sphere, accent), 'TailSpade', 0, 0.08, -1.28, [0.16, 0.1, 0.2]);
  }

  const wings = {};
  for (const side of [-1, 1]) {
    const pivot = joint(THREE, spine, side < 0 ? 'Wing_L' : 'Wing_R', side * (moon ? 0.28 : 0.18), moon ? 0.12 : 0.1, moon ? -0.05 : 0.05);
    const membrane = put(pivot, new THREE.Mesh(wingGeo, wingMat), side < 0 ? 'WingMesh_L' : 'WingMesh_R', 0, 0, 0);
    membrane.scale.x = side;
    membrane.rotation.y = side * (moon ? -0.35 : -0.2);
    wings[side < 0 ? 'L' : 'R'] = pivot;
  }

  const legs = {};
  const legLayout = moon
    ? [[-0.22, -0.28, 0.16, 'FL'], [0.22, -0.28, 0.16, 'FR'], [-0.22, -0.3, -0.14, 'BL'], [0.22, -0.3, -0.14, 'BR']]
    : [[-0.16, -0.18, 0.42, 'FL'], [0.16, -0.18, 0.42, 'FR'], [-0.16, -0.18, -0.28, 'BL'], [0.16, -0.18, -0.28, 'BR']];
  for (const [x, y, z, label] of legLayout) {
    const hip = joint(THREE, spine, 'Leg_' + label, x, y, z);
    put(hip, new THREE.Mesh(sphere, fur), 'Thigh_' + label, 0, -0.12, 0, moon ? [0.095, 0.16, 0.095] : [0.075, 0.12, 0.08]);
    const knee = joint(THREE, hip, 'Knee_' + label, 0, -0.24, 0.02);
    put(knee, new THREE.Mesh(sphere, lit), 'Shin_' + label, 0, -0.1, 0, [0.072, 0.12, 0.072]);
    put(knee, new THREE.Mesh(sphere, accent), 'Paw_' + label, 0, -0.2, 0.03, moon ? [0.105, 0.052, 0.125] : [0.082, 0.042, 0.105]);
    for (const toeIdx of [-1, 0, 1]) {
      put(knee, new THREE.Mesh(sphere, pinkMat), `Toe_${label}_${toeIdx + 2}`, toeIdx * 0.032, -0.21, 0.11, [0.024, 0.020, 0.032]);
    }
    legs[label] = hip;
  }

  let tail = spine;
  const tailZ = moon ? -0.32 : -0.7;
  for (let i = 1; i <= (moon ? 3 : 4); i++) {
    tail = joint(THREE, tail, 'Tail_' + i, 0, moon ? 0.02 : 0.04, i === 1 ? tailZ : -0.22);
    put(tail, new THREE.Mesh(sphere, i === (moon ? 3 : 4) ? accent : fur), 'TailMesh_' + i, 0, 0, -0.08, [0.11 - i * 0.012, 0.09 - i * 0.01, 0.17]);
  }
  if (moon) {
    put(tail, new THREE.Mesh(octGem, gemMat), 'TailStarTip', 0, 0.02, -0.22, [0.95, 0.95, 1.3]);
  } else {
    put(tail, new THREE.Mesh(sphere, accent), 'TailSpadeTip', 0, 0.02, -0.28, [0.14, 0.08, 0.16]);
  }

  root.updateMatrixWorld(true);
  const bounds = new THREE.Box3().setFromObject(root);
  root.position.y -= bounds.min.y;
  root.updateMatrixWorld(true);

  const secondary = createSecondaryMotion({
    seed: attribution.identityId,
    element: moon ? 'umbral' : 'ember',
    tailSegments: moon ? 3 : 4,
    particleCount: low ? 16 : 26,
  });
  const fluidProf = ELEMENT_FLUID_PROFILES[moon ? 'umbral' : 'ember'];
  const ptArr = new Float32Array(secondary.fluid.particles.length * 3);
  secondary.fluid.particles.forEach((p, idx) => {
    ptArr[idx * 3] = p.x;
    ptArr[idx * 3 + 1] = p.y;
    ptArr[idx * 3 + 2] = p.z;
  });
  const ptGeo = trackGeo(new THREE.BufferGeometry());
  ptGeo.setAttribute('position', new THREE.BufferAttribute(ptArr, 3));
  const ptMat = trackMat(new THREE.PointsMaterial({
    color: fluidProf.colorA,
    size: 0.06,
    transparent: true,
    opacity: 0.88,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  }));
  const cosmicParticles = new THREE.Points(ptGeo, ptMat);
  cosmicParticles.name = 'CosmicParticles';
  root.add(cosmicParticles);

  const joints = {spine, neck, head, jaw, wings, legs, cosmicParticles};
  let disposed = false;
  function dispose() {
    if (disposed) return;
    disposed = true;
    geometries.forEach(geometry => geometry.dispose());
    materials.forEach(value => value.dispose());
  }
  let triangles = 0;
  root.traverse(object => {
    const geo = object.geometry;
    if (!geo || object.isPoints) return;
    const pos = geo.getAttribute('position');
    triangles += geo.index ? geo.index.count / 3 : (pos ? pos.count / 3 : 0);
  });
  root.userData.triangles = triangles;
  return {kind, attribution, root, joints, secondary, materials: {fur, accent, eyeWhite}, dispose};
}

function setLid(root, amount) {
  for (const name of ['Lid_L', 'Lid_R']) {
    const lid = root.getObjectByName(name);
    if (lid) lid.scale.y = 0.35 + amount * 2.4;
  }
}

/** Visual pose only. `time` is seconds of animation, not a trusted clock. */
export function poseDimensional(rig, {state = 'idle', time = 0, reduced = false, speaking = false, emotion = null} = {}) {
  const root = rig.root;
  const {spine, neck, head, jaw, wings, legs, cosmicParticles} = rig.joints;
  const moon = rig.kind === 'moonwraith-artistic';
  const t = reduced ? 0 : time;
  const asleep = state === 'sleeping' || state === 'halted';
  const listening = state === 'listening' || speaking;
  const reacting = state === 'celebrating' || state === 'zoomies' || state === 'hop';
  const looking = state === 'observing' || state === 'thinking' || state === 'remembering' || state === 'curious' || listening;
  const walking = !reduced && !asleep && (state === 'observing' || state === 'walk' || state === 'zoomies' || state === 'scared');
  const blink = reduced || asleep ? (asleep ? 1 : 0) : (Math.sin(t * 2.6) > 0.93 ? 1 : 0);
  const breathe = reduced ? 1 : 1 + Math.sin(t * 1.6) * (asleep ? 0.015 : 0.035);
  const sec = rig.secondary ? stepSecondaryMotion(rig.secondary, 1 / 60, {
    position: {x: walking ? Math.sin(t * 2) * 0.1 : 0, y: 0, z: 0},
    lift: reacting && !reduced ? Math.abs(Math.sin(t * 6)) * 0.18 : 0,
    targetSy: breathe,
    emotion,
    reduced: reduced || asleep,
  }) : null;
  spine.scale.set(1, breathe, 1);
  spine.rotation.x = asleep ? 0.35 : state === 'curious' ? 0.2 : state === 'scared' ? -0.16 : reacting ? -0.08 + Math.sin(t * 6) * 0.04 : 0;
  neck.rotation.x = asleep ? 0.4 : listening || state === 'curious' ? -0.18 : 0;
  head.rotation.y = reduced ? 0 : looking ? Math.sin(t * 0.8) * 0.35 : Math.sin(t * 0.35) * 0.08;
  head.rotation.z = reacting ? Math.sin(t * 5) * 0.08 : 0;
  jaw.rotation.x = speaking && !reduced ? 0.25 + Math.sin(t * 14) * 0.18 : asleep ? 0.05 : 0;
  setLid(root, blink);
  const earL = root.getObjectByName('Ear_L');
  const earR = root.getObjectByName('Ear_R');
  if (earL && earR) {
    const perk = reduced ? 0 : listening ? -0.35 : Math.sin(t * 1.2) * 0.06 + (sec ? sec.earL.yaw * 0.35 : 0);
    earL.rotation.z = perk;
    earR.rotation.z = -perk;
  }
  const flap = reduced || asleep ? 0.15 : 0.25 + Math.sin(t * (reacting ? 6 : 2.2)) * (walking ? 0.15 : 0.28);
  wings.L.rotation.z = flap;
  wings.R.rotation.z = -flap;
  const labels = ['FL', 'FR', 'BL', 'BR'];
  labels.forEach((label, index) => {
    const hip = legs[label];
    const swing = walking ? Math.sin(t * 6 + (index % 2 === 0 ? 0 : Math.PI)) * 0.45 : 0;
    hip.rotation.x = swing;
  });
  for (let i = 1; i <= 4; i++) {
    const segment = root.getObjectByName('Tail_' + i);
    if (!segment) continue;
    const verletYaw = sec && sec.tailAngles[i - 1] ? sec.tailAngles[i - 1].yaw * 0.35 : 0;
    segment.rotation.y = reduced ? 0 : Math.sin(t * 1.8 + i) * (asleep ? 0.04 : 0.18) + verletYaw;
    segment.rotation.x = moon ? 0 : -0.12;
  }
  if (sec && cosmicParticles?.geometry) {
    const attr = cosmicParticles.geometry.getAttribute('position');
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
  return {
    kind: rig.kind,
    blink,
    breathe,
    speaking: Boolean(speaking) && !reduced,
    walking,
    asleep,
    jaw: jaw.rotation.x,
    wing: wings.L.rotation.z,
    leg: legs.FL.rotation.x,
  };
}

export function measureSilhouette(THREE, rig) {
  const root = rig.root;
  const nose = root.getObjectByName('Nose');
  const particles = root.getObjectByName('CosmicParticles');
  if (particles) particles.visible = false;
  const views = {};
  for (const [name, yaw] of [['front', 0], ['side', Math.PI / 2], ['back', Math.PI], ['threeQuarter', Math.PI / 4]]) {
    root.rotation.y = yaw;
    root.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(root);
    const size = box.getSize(new THREE.Vector3());
    const nosePos = new THREE.Vector3();
    nose.getWorldPosition(nosePos);
    views[name] = {
      width: round(size.x), height: round(size.y), depth: round(size.z),
      noseZ: round(nosePos.z), minY: round(box.min.y),
    };
  }
  root.rotation.y = 0;
  if (particles) particles.visible = true;
  root.updateMatrixWorld(true);
  return views;
}

function round(value) {
  return Math.round(value * 1000) / 1000;
}
