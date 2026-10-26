/**
 * Articulated 3D companions for the existing Three.js renderer.
 *
 * These meshes are artistic representations. They are not measured quantum
 * phenotypes, and a display name never selects one.
 *
 * Moonwraith display persona bb-7f9c2a03: black moon-cat/dragon, violet
 * accents, star eyes, crescent horns.
 * Saved Zeref bb-deada969: a different dragonling silhouette. It must not
 * wear the Moonwraith body.
 */
export const MOONWRAITH_DISPLAY_ID = 'bb-7f9c2a03';
export const SAVED_ZEREF_ID = 'bb-deada969';

const PALETTE = {
  'moonwraith-artistic': {
    fur: 0x140c22, lit: 0x3a2460, accent: 0xb57bff, eye: 0xe4d2ff,
    wing: 0x6d3ec8, belly: 0x2a1848, horn: 0xf4ecff, pupil: 0x2a0d5e,
  },
  'dragonling-artistic': {
    fur: 0x8a3b22, lit: 0xe09a55, accent: 0xf2c14e, eye: 0xffe7a8,
    wing: 0x5a2744, belly: 0xf3d2b4, horn: 0x5c241c, pupil: 0x2a1208,
  },
};

// Lilac membrane + deep-indigo bones (Studio's wing reference), per kind, so the sheet reads on both palettes.
const WING_LILAC = {'moonwraith-artistic': 0x9a6be0, 'dragonling-artistic': 0x9a6be0};
const WING_BONE = {'moonwraith-artistic': 0x3b2a8a, 'dragonling-artistic': 0x3b2a8a};

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
  return new THREE.MeshStandardMaterial({
    color,
    roughness: extra.roughness ?? 0.46,
    metalness: extra.metalness ?? 0.06,
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

function put(parent, mesh, name, x, y, z, scale) {
  mesh.name = name;
  mesh.position.set(x, y, z);
  if (scale) mesh.scale.set(scale[0], scale[1], scale[2]);
  parent.add(mesh);
  return mesh;
}

/**
 * Wing = real membrane on a bone frame, never an extruded slab: a thick arm bone with a round shoulder joint, four round finger rods
 * that taper to the tip (same fan as the artist's wing reference), and a thin, slightly cupped membrane with veins stretched between
 * them. The rods sweep back in depth, so a side-on view still shows the arm, the rods and the bowed sheet. Pure geometry, no randomness.
 * Wing frame: +x out from the shoulder, +y up, +z forward; the caller mirrors it for the other side.
 */
export function wingFrame(span, lift) {
  const wrist = [span * 0.34, lift * 1.0, 0.06];
  const tips = [[span, lift * 0.3, 0.0], [span * 0.82, -lift * 0.22, -0.11], [span * 0.54, -lift * 0.56, -0.24], [span * 0.12, -lift * 0.36, -0.38]];
  return {shoulder: [0, 0, 0], wrist, tips, cup: Math.min(0.1, span * 0.15), sag: 0.2};
}

function wingPoint(frame, k, u, v) {
  // k = panel index (0..3): panels 0-2 lie between finger rays k and k+1, panel 3 between the last finger and the shoulder edge.
  const a = frame.tips[k];
  const b = k < 3 ? frame.tips[k + 1] : frame.shoulder;
  const w = frame.wrist;
  const qx = a[0] + (b[0] - a[0]) * v, qy = a[1] + (b[1] - a[1]) * v, qz = a[2] + (b[2] - a[2]) * v;
  const scallop = u >= 0.999 ? 1 - frame.sag * Math.sin(Math.PI * v) : 1 - frame.sag * Math.sin(Math.PI * v) * u * u;
  const bow = -frame.cup * Math.sin(Math.PI * v) * u;
  return [w[0] + (qx - w[0]) * u * scallop, w[1] + (qy - w[1]) * u * scallop, w[2] + (qz - w[2]) * u + bow];
}

function wingMembraneGeometry(THREE, frame, rows, cols) {
  const pos = [];
  const idx = [];
  for (let k = 0; k < 4; k++) {
    const base = pos.length / 3;
    for (let r = 0; r <= rows; r++) {
      for (let c = 0; c <= cols; c++) pos.push(...wingPoint(frame, k, r / rows, c / cols));
    }
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const i = base + r * (cols + 1) + c;
        idx.push(i, i + cols + 1, i + 1, i + 1, i + cols + 1, i + cols + 2);
      }
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setIndex(idx);
  geo.computeVertexNormals();
  return geo;
}

function wingVeinGeometry(THREE, frame) {
  const pos = [];
  const lift = 0.004;
  const seg = (p, q) => pos.push(p[0], p[1], p[2] + lift, q[0], q[1], q[2] + lift);
  for (let k = 0; k < 4; k++) {
    for (const v of [0.35, 0.65]) {
      let prev = wingPoint(frame, k, 0.08, v);
      for (let s = 2; s <= 8; s++) {
        const cur = wingPoint(frame, k, s / 8, v);
        seg(prev, cur);
        prev = cur;
      }
    }
    for (const u of [0.45, 0.72]) {
      let prev = wingPoint(frame, k, u, 0.18);
      for (let s = 1; s <= 5; s++) {
        const cur = wingPoint(frame, k, u, 0.18 + (0.64 * s) / 5);
        seg(prev, cur);
        prev = cur;
      }
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  return geo;
}

/** One round, tapered rod from a to b (radius r0 at a, r1 at b). */
function wingRod(THREE, geometries, material, a, b, r0, r1, radial, name) {
  const dir = new THREE.Vector3(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
  const len = dir.length();
  const geo = new THREE.CylinderGeometry(r1, r0, len, radial, 1, false);
  geometries.push(geo);
  const mesh = new THREE.Mesh(geo, material);
  mesh.name = name;
  mesh.position.set((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
  mesh.userData.rod = {radiusRoot: r0, radiusTip: r1, length: len};
  return mesh;
}

function buildWing(THREE, {span, lift, low, boneMat, membraneMat, veinMat, joinMat, geometries, side}) {
  const frame = wingFrame(span, lift);
  const group = new THREE.Group();
  group.name = side < 0 ? 'WingMesh_L' : 'WingMesh_R';
  group.userData.wingFrame = frame;
  const radial = low ? 6 : 10;
  const membrane = new THREE.Mesh(wingMembraneGeometry(THREE, frame, low ? 3 : 5, low ? 4 : 7), membraneMat);
  geometries.push(membrane.geometry);
  membrane.name = 'WingMembrane';
  group.add(membrane);
  const veins = new THREE.LineSegments(wingVeinGeometry(THREE, frame), veinMat);
  geometries.push(veins.geometry);
  veins.name = 'WingVeins';
  group.add(veins);
  // arm bone: thick at the shoulder, thinner at the wrist, bowed a little so it reads as an arm, not a stick
  const elbow = [frame.wrist[0] * 0.5, frame.wrist[1] * 0.78, 0.1];
  group.add(wingRod(THREE, geometries, boneMat, frame.shoulder, elbow, 0.052, 0.04, radial, 'WingArm_a'));
  group.add(wingRod(THREE, geometries, boneMat, elbow, frame.wrist, 0.04, 0.032, radial, 'WingArm_b'));
  frame.tips.forEach((tip, i) => {
    const w = frame.wrist;
    const mid = [w[0] + (tip[0] - w[0]) * 0.5, w[1] + (tip[1] - w[1]) * 0.5, w[2] + (tip[2] - w[2]) * 0.5 - frame.cup * 0.35];
    const r0 = 0.03 - i * 0.002;
    group.add(wingRod(THREE, geometries, boneMat, w, mid, r0, r0 * 0.7, radial, 'WingFinger_' + i + 'a'));
    group.add(wingRod(THREE, geometries, boneMat, mid, tip, r0 * 0.7, 0.011, radial, 'WingFinger_' + i + 'b'));
  });
  const shoulder = new THREE.Mesh(new THREE.SphereGeometry(0.066, low ? 8 : 14, low ? 6 : 10), joinMat);
  geometries.push(shoulder.geometry);
  shoulder.name = 'WingShoulder';
  group.add(shoulder);
  const knuckle = new THREE.Mesh(new THREE.SphereGeometry(0.046, low ? 8 : 12, low ? 6 : 8), joinMat);
  geometries.push(knuckle.geometry);
  knuckle.name = 'WingWrist';
  knuckle.position.set(...frame.wrist);
  group.add(knuckle);
  return group;
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
  const seg = low ? [12, 8] : [20, 14];
  const geometries = [];
  const materials = [];
  const trackGeo = geometry => {geometries.push(geometry); return geometry;};
  const trackMat = value => {materials.push(value); return value;};
  const fur = trackMat(material(THREE, colors.fur));
  const lit = trackMat(material(THREE, colors.lit, {emissive: colors.accent, emissiveIntensity: 0.08}));
  const belly = trackMat(material(THREE, colors.belly));
  const accent = trackMat(material(THREE, colors.accent, {emissive: colors.accent, emissiveIntensity: moon ? 0.35 : 0.22, roughness: 0.28}));
  const eyeWhite = trackMat(material(THREE, colors.eye, {emissive: colors.eye, emissiveIntensity: moon ? 0.85 : 0.45, roughness: 0.18}));
  const pupil = trackMat(material(THREE, colors.pupil, {roughness: 0.2}));
  // thin lilac membrane: slightly see-through (veins and the far wing still read), lit from both sides
  const wingMat = trackMat(material(THREE, WING_LILAC[kind], {emissive: colors.accent, emissiveIntensity: 0.22, roughness: 0.55}));
  wingMat.transparent = true;
  wingMat.opacity = 0.78;
  wingMat.depthWrite = false;
  wingMat.side = THREE.DoubleSide;
  const wingBone = trackMat(material(THREE, WING_BONE[kind], {emissive: colors.accent, emissiveIntensity: 0.1, roughness: 0.38}));
  const wingVein = trackMat(new THREE.LineBasicMaterial({color: 0xe6ccff, transparent: true, opacity: 0.55}));
  const sphere = trackGeo(new THREE.SphereGeometry(1, seg[0], seg[1]));
  const cone = trackGeo(new THREE.ConeGeometry(0.12, moon ? 0.34 : 0.16, low ? 6 : 10));
  const star = trackGeo(new THREE.OctahedronGeometry(moon ? 0.045 : 0.02, 0));
  const wingSpan = moon ? 0.92 : 0.62;
  const wingLift = moon ? 0.42 : 0.28;
  const crescent = moon ? trackGeo(new THREE.TorusGeometry(0.11, 0.028, low ? 6 : 8, low ? 12 : 18, Math.PI * 1.25)) : null;
  const root = new THREE.Group();
  root.name = 'DimensionalCreature';
  root.userData = {...attribution, triangles: 0};

  const spine = joint(THREE, root, 'Spine', 0, moon ? 0.78 : 0.62, 0);
  const chest = put(spine, new THREE.Mesh(sphere, fur), 'Body', 0, 0, 0, moon ? [0.52, 0.46, 0.4] : [0.34, 0.3, 0.78]);
  put(spine, new THREE.Mesh(sphere, belly), 'Belly', 0, moon ? -0.08 : -0.06, moon ? 0.12 : 0.18, moon ? [0.28, 0.22, 0.16] : [0.2, 0.14, 0.36]);
  const neck = joint(THREE, spine, 'Neck', 0, moon ? 0.28 : 0.16, moon ? 0.06 : 0.48);
  const head = joint(THREE, neck, 'Head', 0, moon ? 0.22 : 0.08, moon ? 0.02 : 0.16);
  put(head, new THREE.Mesh(sphere, fur), 'Skull', 0, 0, 0, moon ? [0.36, 0.32, 0.34] : [0.24, 0.2, 0.28]);
  const nose = put(head, new THREE.Mesh(sphere, lit), 'Nose', 0, moon ? -0.04 : -0.02, moon ? 0.28 : 0.42, moon ? [0.12, 0.09, 0.14] : [0.1, 0.08, 0.28]);
  const jaw = joint(THREE, head, 'Jaw', 0, -0.08, moon ? 0.12 : 0.2);
  put(jaw, new THREE.Mesh(sphere, belly), 'JawMesh', 0, 0, 0.06, moon ? [0.1, 0.04, 0.08] : [0.08, 0.035, 0.12]);

  const eyeGeoParent = head;
  for (const side of [-1, 1]) {
    const eye = joint(THREE, eyeGeoParent, side < 0 ? 'Eye_L' : 'Eye_R', side * (moon ? 0.14 : 0.1), moon ? 0.06 : 0.04, moon ? 0.24 : 0.18);
    put(eye, new THREE.Mesh(sphere, eyeWhite), side < 0 ? 'EyeWhite_L' : 'EyeWhite_R', 0, 0, 0, moon ? [0.075, 0.09, 0.04] : [0.055, 0.07, 0.035]);
    if (moon) put(eye, new THREE.Mesh(star, accent), side < 0 ? 'Star_L' : 'Star_R', 0, 0, 0.04);
    else put(eye, new THREE.Mesh(star, pupil), side < 0 ? 'Slit_L' : 'Slit_R', 0, 0, 0.03, [0.35, 1.4, 0.4]);
    const lid = joint(THREE, eye, side < 0 ? 'Lid_L' : 'Lid_R', 0, 0.02, 0.03);
    put(lid, new THREE.Mesh(sphere, fur), side < 0 ? 'LidMesh_L' : 'LidMesh_R', 0, 0, 0, [0.09, 0.035, 0.03]);
  }

  if (moon) {
    for (const side of [-1, 1]) {
      const ear = joint(THREE, head, side < 0 ? 'Ear_L' : 'Ear_R', side * 0.2, 0.26, -0.02);
      const earMesh = put(ear, new THREE.Mesh(cone, fur), side < 0 ? 'EarMesh_L' : 'EarMesh_R', 0, 0.12, 0);
      earMesh.rotation.z = side * -0.25;
      const horn = joint(THREE, head, side < 0 ? 'Crescent_L' : 'Crescent_R', side * 0.16, 0.18, 0.02);
      const crescentMesh = put(horn, new THREE.Mesh(crescent, accent), side < 0 ? 'CrescentMesh_L' : 'CrescentMesh_R', 0, 0.08, 0);
      crescentMesh.rotation.z = side * 0.6;
      crescentMesh.rotation.y = side * -0.4;
    }
  } else {
    for (const side of [-1, 1]) {
      const horn = joint(THREE, head, side < 0 ? 'Horn_L' : 'Horn_R', side * 0.1, 0.16, 0.02);
      put(horn, new THREE.Mesh(cone, trackMat(material(THREE, colors.horn))), side < 0 ? 'HornMesh_L' : 'HornMesh_R', 0, 0.08, 0, [0.7, 1, 0.7]);
    }
    put(spine, new THREE.Mesh(sphere, accent), 'TailSpade', 0, 0.08, -1.28, [0.16, 0.1, 0.2]);
  }

  const wings = {};
  for (const side of [-1, 1]) {
    const pivot = joint(THREE, spine, side < 0 ? 'Wing_L' : 'Wing_R', side * (moon ? 0.28 : 0.18), moon ? 0.12 : 0.1, moon ? -0.05 : 0.05);
    const membrane = buildWing(THREE, {span: wingSpan, lift: wingLift, low, boneMat: wingBone, membraneMat: wingMat, veinMat: wingVein, joinMat: wingBone, geometries, side});
    pivot.add(membrane);
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
    put(hip, new THREE.Mesh(sphere, fur), 'Thigh_' + label, 0, -0.12, 0, moon ? [0.09, 0.16, 0.09] : [0.07, 0.12, 0.08]);
    const knee = joint(THREE, hip, 'Knee_' + label, 0, -0.24, 0.02);
    put(knee, new THREE.Mesh(sphere, lit), 'Shin_' + label, 0, -0.1, 0, [0.07, 0.12, 0.07]);
    put(knee, new THREE.Mesh(sphere, accent), 'Paw_' + label, 0, -0.2, 0.03, moon ? [0.1, 0.05, 0.12] : [0.08, 0.04, 0.1]);
    legs[label] = hip;
  }

  let tail = spine;
  const tailZ = moon ? -0.32 : -0.7;
  for (let i = 1; i <= (moon ? 3 : 4); i++) {
    tail = joint(THREE, tail, 'Tail_' + i, 0, moon ? 0.02 : 0.04, i === 1 ? tailZ : -0.22);
    put(tail, new THREE.Mesh(sphere, i === (moon ? 3 : 4) ? accent : fur), 'TailMesh_' + i, 0, 0, -0.08, [0.1 - i * 0.012, 0.08 - i * 0.01, 0.16]);
  }
  if (!moon) put(tail, new THREE.Mesh(sphere, accent), 'TailSpadeTip', 0, 0.02, -0.28, [0.14, 0.08, 0.16]);

  root.updateMatrixWorld(true);
  const bounds = new THREE.Box3().setFromObject(root);
  root.position.y -= bounds.min.y;
  root.updateMatrixWorld(true);

  const joints = {spine, neck, head, jaw, wings, legs};
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
    if (!geo) return;
    const pos = geo.getAttribute('position');
    triangles += geo.index ? geo.index.count / 3 : (pos ? pos.count / 3 : 0);
  });
  root.userData.triangles = triangles;
  return {kind, attribution, root, joints, materials: {fur, accent, eyeWhite}, dispose};
}

function setLid(root, amount) {
  for (const name of ['Lid_L', 'Lid_R']) {
    const lid = root.getObjectByName(name);
    if (lid) lid.scale.y = 0.35 + amount * 2.4;
  }
}

/** Visual pose only. `time` is seconds of animation, not a trusted clock. */
export function poseDimensional(rig, {state = 'idle', time = 0, reduced = false, speaking = false} = {}) {
  const root = rig.root;
  const {spine, neck, head, jaw, wings, legs} = rig.joints;
  const moon = rig.kind === 'moonwraith-artistic';
  const t = reduced ? 0 : time;
  const asleep = state === 'sleeping' || state === 'halted';
  const listening = state === 'listening' || speaking;
  const reacting = state === 'celebrating';
  const looking = state === 'observing' || state === 'thinking' || state === 'remembering' || listening;
  const walking = !reduced && !asleep && (state === 'observing' || state === 'walk');
  const blink = reduced || asleep ? (asleep ? 1 : 0) : (Math.sin(t * 2.6) > 0.93 ? 1 : 0);
  const breathe = reduced ? 1 : 1 + Math.sin(t * 1.6) * (asleep ? 0.015 : 0.035);
  spine.scale.set(1, breathe, 1);
  spine.rotation.x = asleep ? 0.35 : reacting ? -0.08 + Math.sin(t * 6) * 0.04 : 0;
  neck.rotation.x = asleep ? 0.4 : listening ? -0.18 : 0;
  head.rotation.y = reduced ? 0 : looking ? Math.sin(t * 0.8) * 0.35 : Math.sin(t * 0.35) * 0.08;
  head.rotation.z = reacting ? Math.sin(t * 5) * 0.08 : 0;
  jaw.rotation.x = speaking && !reduced ? 0.25 + Math.sin(t * 14) * 0.18 : asleep ? 0.05 : 0;
  setLid(root, blink);
  const earL = root.getObjectByName('Ear_L');
  const earR = root.getObjectByName('Ear_R');
  if (earL && earR) {
    const perk = reduced ? 0 : listening ? -0.35 : Math.sin(t * 1.2) * 0.06;
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
    segment.rotation.y = reduced ? 0 : Math.sin(t * 1.8 + i) * (asleep ? 0.04 : 0.18);
    segment.rotation.x = moon ? 0 : -0.12;
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
  root.updateMatrixWorld(true);
  return views;
}

function round(value) {
  return Math.round(value * 1000) / 1000;
}
