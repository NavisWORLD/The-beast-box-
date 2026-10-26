import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {buildDimensionalRig, wingFrame} from '../lib/creature-dimensional.mjs';

/** Rasterise the projection of every triangle of `objects` onto the screen plane (world x right, y up, looking down -z)
 * and return the covered area, so an edge-on slab shows up as a sliver. */
function projectedArea(root, pick) {
  let top = root;
  while (top.parent) top = top.parent;
  top.updateMatrixWorld(true); // refresh the whole rig, not only the wing, so the creature's yaw is applied
  const tris = [];
  const v = new THREE.Vector3();
  root.traverse(o => {
    if (!o.isMesh || !pick(o)) return;
    const pos = o.geometry.getAttribute('position');
    const index = o.geometry.index;
    const n = index ? index.count : pos.count;
    const at = i => {
      const j = index ? index.getX(i) : i;
      v.fromBufferAttribute(pos, j).applyMatrix4(o.matrixWorld);
      return [v.x, v.y];
    };
    for (let i = 0; i < n; i += 3) tris.push([at(i), at(i + 1), at(i + 2)]);
  });
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const t of tris) for (const [x, y] of t) { minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y); }
  return {tris, minX, maxX, minY, maxY};
}

function coverage(info, box, cells = 220) {
  const w = (box.maxX - box.minX) / cells, h = (box.maxY - box.minY) / cells;
  let hit = 0;
  for (let i = 0; i < cells; i++) for (let j = 0; j < cells; j++) {
    const px = box.minX + (i + 0.5) * w, py = box.minY + (j + 0.5) * h;
    for (const [a, b, c] of info.tris) {
      const d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1]);
      if (Math.abs(d) < 1e-12) continue;
      const l1 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / d;
      const l2 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / d;
      if (l1 >= 0 && l2 >= 0 && l1 + l2 <= 1) { hit++; break; }
    }
  }
  return hit * w * h;
}

const isWingPart = o => /^Wing(Membrane|Arm|Finger|Shoulder|Wrist)/.test(o.name);

for (const kind of ['dragonling-artistic', 'moonwraith-artistic']) {
  test(`${kind}: wings keep arm, rods and a cupped sheet at a 90 degree camera angle`, () => {
    const rig = buildDimensionalRig(THREE, kind);
    try {
      const wing = rig.root.getObjectByName('WingMesh_R');
      assert.ok(wing, 'right wing group exists');
      const rods = [];
      wing.traverse(o => { if (o.userData.rod) rods.push(o); });
      const arm = rods.filter(o => o.name.startsWith('WingArm'));
      const fingers = rods.filter(o => o.name.startsWith('WingFinger'));
      assert.equal(arm.length, 2, 'arm bone has two segments');
      assert.equal(fingers.length, 8, 'four finger rods of two segments');
      // round rods with real thickness, thick at the shoulder and thinner toward the tip
      for (const r of rods) assert.ok(r.userData.rod.radiusRoot >= 0.011 && r.userData.rod.radiusTip >= 0.009, 'rod ' + r.name + ' is not a hairline');
      assert.ok(arm[0].userData.rod.radiusRoot >= 0.05, 'arm bone is thick at the shoulder');
      assert.ok(arm[0].userData.rod.radiusRoot > arm[1].userData.rod.radiusTip * 1.4, 'arm tapers');
      for (let i = 0; i < 4; i++) {
        const a = rods.find(o => o.name === `WingFinger_${i}a`), b = rods.find(o => o.name === `WingFinger_${i}b`);
        assert.ok(a.userData.rod.radiusRoot > b.userData.rod.radiusTip * 2, `finger ${i} tapers to a thin tip`);
      }
      assert.ok(wing.getObjectByName('WingShoulder').geometry.type === 'SphereGeometry', 'round shoulder joint');
      // membrane: thin, slightly see-through, with veins, and cupped (not coplanar)
      const mem = wing.getObjectByName('WingMembrane');
      assert.ok(mem.material.transparent && mem.material.opacity < 1 && mem.material.opacity > 0.5, 'slightly see-through');
      assert.equal(mem.material.side, THREE.DoubleSide);
      assert.ok(wing.getObjectByName('WingVeins').geometry.getAttribute('position').count >= 100, 'veins drawn');
      const pos = mem.geometry.getAttribute('position');
      let zMin = Infinity, zMax = -Infinity;
      for (let i = 0; i < pos.count; i++) { zMin = Math.min(zMin, pos.getZ(i)); zMax = Math.max(zMax, pos.getZ(i)); }
      assert.ok(zMax - zMin > 0.3, `membrane has depth in the wing frame (${(zMax - zMin).toFixed(3)})`);
      const f = wingFrame(0.62, 0.28);
      assert.ok(f.cup >= 0.08, 'membrane is cupped');

      // 90 degree camera: creature faces +x, camera looks down -z. Compare each wing's side silhouette with its front silhouette.
      const sideArea = (() => {
        rig.root.rotation.y = Math.PI / 2;
        const info = projectedArea(wing, isWingPart);
        info.tris.length || assert.fail('no wing triangles');
        return {info, area: coverage(info, info)};
      })();
      rig.root.rotation.y = 0;
      const front = projectedArea(wing, isWingPart);
      const frontArea = coverage(front, front);
      rig.root.rotation.y = Math.PI / 2;
      const side = sideArea;
      rig.root.updateMatrixWorld(true);
      const sideDepthSpan = side.info.maxX - side.info.minX;
      // the old extruded slab kept only ~35% of its front area and was 0.20 wide here; the bone frame sweeps back in depth
      assert.ok(side.area / frontArea > 0.45, `side-on wing keeps real area: ${(side.area / frontArea).toFixed(2)} of its front area`);
      assert.ok(sideDepthSpan > 0.3, `side-on wing is not a sliver: ${sideDepthSpan.toFixed(3)} wide`);
      // the rods alone (no membrane) still show a clear arm and fingers at 90 degrees, each at least 0.04 across
      const rodsOnly = projectedArea(wing, o => o.userData.rod);
      const rodArea = coverage(rodsOnly, side.info);
      assert.ok(rodArea > 0.002, `rods alone fill visible area at 90 degrees: ${rodArea.toFixed(4)}`);
      for (const r of rods) assert.ok(r.userData.rod.radiusRoot * 2 >= 0.022, 'visible rod thickness');
      rig.root.rotation.y = 0;
    } finally {
      rig.dispose();
    }
  });
}

test('wing geometry is deterministic (no randomness) and disposes with the rig', () => {
  const a = buildDimensionalRig(THREE, 'dragonling-artistic');
  const b = buildDimensionalRig(THREE, 'dragonling-artistic');
  const pa = a.root.getObjectByName('WingMesh_L').getObjectByName('WingMembrane').geometry.getAttribute('position').array;
  const pb = b.root.getObjectByName('WingMesh_L').getObjectByName('WingMembrane').geometry.getAttribute('position').array;
  assert.deepEqual(Array.from(pa), Array.from(pb));
  a.dispose(); b.dispose();
  assert.ok(a.root.userData.triangles < 25000, 'mobile triangle budget');
});
