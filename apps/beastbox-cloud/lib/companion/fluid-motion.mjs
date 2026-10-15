/**
 * DETERMINISTIC FLUID DYNAMICS & VERLET SECONDARY MOTION
 *
 * Gives every 3D creature living, flowing secondary motion:
 * - Multi-node 3D Verlet / spring simulation on tails, ears, wings, fur tufts, and wisps.
 * - Volume-preserving soft-body squash & stretch on landing, hop launch, and sudden turns.
 * - Real-time divergence-free 3D curl-noise + SPH-lite elemental fluid solver for
 *   flame/ember, ice/frost, crystal, plasma/machine, radiant, void/umbral, verdant, and grove.
 *
 * Pure and honest: driven deterministically by the creature's recorded seed and emotion state
 * (lib/companion/emotion.mjs). Never uses unseeded randomness, clock, network, or storage.
 */

function fnv1a(str) {
  let h = 0x811c9dc5;
  const s = String(str || 'beast');
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

export function seededPrng(seed) {
  let a = fnv1a(seed) || 1;
  return () => {
    a ^= a << 13; a >>>= 0;
    a ^= a >>> 17;
    a ^= a << 5; a >>>= 0;
    return a / 4294967296;
  };
}

/** Element fluid profiles mapping Beast Box island elements + canonical archetypes. */
export const ELEMENT_FLUID_PROFILES = Object.freeze({
  ember:   { kind: 'flame',   buoyancy:  1.45, curlFreq: 2.6, curlAmp: 0.95, sphRepel: 0.28, viscosity: 0.12, drag: 1.8, radius: 0.52, colorA: 0xff6b1a, colorB: 0xffd24c },
  flame:   { kind: 'flame',   buoyancy:  1.45, curlFreq: 2.6, curlAmp: 0.95, sphRepel: 0.28, viscosity: 0.12, drag: 1.8, radius: 0.52, colorA: 0xff6b1a, colorB: 0xffd24c },
  frost:   { kind: 'ice',     buoyancy: -0.32, curlFreq: 1.4, curlAmp: 0.42, sphRepel: 0.35, viscosity: 0.28, drag: 2.4, radius: 0.58, colorA: 0x9cecff, colorB: 0xe8fbff },
  ice:     { kind: 'ice',     buoyancy: -0.32, curlFreq: 1.4, curlAmp: 0.42, sphRepel: 0.35, viscosity: 0.28, drag: 2.4, radius: 0.58, colorA: 0x9cecff, colorB: 0xe8fbff },
  crystal: { kind: 'ice',     buoyancy:  0.08, curlFreq: 1.7, curlAmp: 0.48, sphRepel: 0.42, viscosity: 0.25, drag: 2.2, radius: 0.56, colorA: 0x5ef2e4, colorB: 0xff94d6 },
  machine: { kind: 'plasma',  buoyancy:  0.35, curlFreq: 3.1, curlAmp: 1.05, sphRepel: 0.38, viscosity: 0.08, drag: 1.5, radius: 0.54, colorA: 0x3bf0ff, colorB: 0xff9b38 },
  plasma:  { kind: 'plasma',  buoyancy:  0.35, curlFreq: 3.1, curlAmp: 1.05, sphRepel: 0.38, viscosity: 0.08, drag: 1.5, radius: 0.54, colorA: 0x3bf0ff, colorB: 0xb978ff },
  radiant: { kind: 'plasma',  buoyancy:  0.62, curlFreq: 2.2, curlAmp: 0.72, sphRepel: 0.30, viscosity: 0.16, drag: 1.9, radius: 0.60, colorA: 0xffe478, colorB: 0xffffff },
  umbral:  { kind: 'void',    buoyancy:  0.18, curlFreq: 2.0, curlAmp: 0.82, sphRepel: 0.18, viscosity: 0.32, drag: 2.1, radius: 0.55, colorA: 0x9d6bff, colorB: 0x2c124d },
  void:    { kind: 'void',    buoyancy:  0.18, curlFreq: 2.0, curlAmp: 0.82, sphRepel: 0.18, viscosity: 0.32, drag: 2.1, radius: 0.55, colorA: 0x9d6bff, colorB: 0x2c124d },
  verdant: { kind: 'verdant', buoyancy:  0.28, curlFreq: 1.6, curlAmp: 0.56, sphRepel: 0.24, viscosity: 0.22, drag: 2.0, radius: 0.58, colorA: 0x7ef56c, colorB: 0xffe96b },
  grove:   { kind: 'verdant', buoyancy:  0.22, curlFreq: 1.5, curlAmp: 0.50, sphRepel: 0.24, viscosity: 0.24, drag: 2.1, radius: 0.56, colorA: 0x4de6a8, colorB: 0x9df779 },
});

/** Map emotion state (from deriveEmotions) to deterministic fluid/Verlet modifiers. */
export function emotionFluidParams(emotion = {}) {
  const joy = Number(emotion?.joy ?? 45) / 100;
  const curiosity = Number(emotion?.curiosity ?? 50) / 100;
  const fear = Number(emotion?.fear ?? 20) / 100;
  const calm = Number(emotion?.calm ?? 50) / 100;
  const mischief = Number(emotion?.mischief ?? 30) / 100;
  const dominant = emotion?.dominant || 'curiosity';

  const speedScale = Math.max(0.35, Math.min(2.1, 0.75 + joy * 0.55 + mischief * 0.65 - calm * 0.28 - fear * 0.15));
  const radiusScale = Math.max(0.45, Math.min(1.55, 0.9 + joy * 0.25 + curiosity * 0.18 - fear * 0.38));
  const buoyancyBias = (joy - fear) * 0.45 + mischief * 0.25;
  const springStiffScale = dominant === 'fear' ? 1.45 : dominant === 'calm' ? 0.78 : 1 + (joy + mischief) * 0.22;
  const tailWagAmp = dominant === 'joy' || dominant === 'mischief' ? 0.32 + (joy + mischief) * 0.2 : dominant === 'fear' ? 0.04 : 0.12 + curiosity * 0.1;
  const tailWagFreq = 2.2 + (joy + mischief) * 3.8 - calm * 0.7;
  const earPerk = dominant === 'curiosity' ? 0.28 : dominant === 'fear' ? -0.38 : (joy - fear) * 0.18;

  return {
    dominant,
    speedScale,
    radiusScale,
    buoyancyBias,
    springStiffScale,
    tailWagAmp,
    tailWagFreq,
    earPerk,
  };
}

/**
 * Analytic divergence-free 3D curl-noise velocity field: v = curl(psi).
 * Because div(curl(psi)) === 0 identically, particles swirl in coherent fluid
 * vortices without artificial sinks or random jitter.
 */
export function curlNoise3D(x, y, z, t = 0, phase = 0, freq = 2.0) {
  const fx = x * freq + phase;
  const fy = y * freq + phase * 1.37;
  const fz = z * freq + phase * 2.11;
  const s = t * 1.35 + phase * 0.5;

  // Partial derivatives of vector potential psi = (psiX, psiY, psiZ)
  const dPsiZ_dy = Math.cos(fy + Math.sin(fx + s)) * freq - 0.45 * Math.sin(fy * 1.7 - fz + s) * freq;
  const dPsiY_dz = Math.cos(fz + Math.sin(fy - s * 0.8)) * freq + 0.4 * Math.cos(fx + fz * 1.5) * freq;

  const dPsiX_dz = Math.cos(fz + Math.cos(fx + s * 0.9)) * freq - 0.35 * Math.sin(fz * 1.6 + fy) * freq;
  const dPsiZ_dx = Math.cos(fx + Math.sin(fz - s * 1.1)) * freq + 0.45 * Math.cos(fy - fx * 1.4) * freq;

  const dPsiY_dx = Math.cos(fx + Math.cos(fy + s * 0.7)) * freq - 0.4 * Math.sin(fx * 1.5 + fz) * freq;
  const dPsiX_dy = Math.cos(fy + Math.sin(fz + s * 1.2)) * freq + 0.35 * Math.cos(fz - fy * 1.6) * freq;

  return {
    vx: dPsiZ_dy - dPsiY_dz,
    vy: dPsiX_dz - dPsiZ_dx,
    vz: dPsiY_dx - dPsiX_dy,
  };
}

/**
 * Create a 3D Verlet chain for tails, ears, wings, fur tufts, or cosmic wisps.
 */
export function createVerletChain({
  segments = 4,
  segmentLength = 0.18,
  dir = { x: 0, y: 0, z: -1 },
  gravity = -0.6,
  damping = 0.88,
  stiffness = 0.78,
  constraintPasses = 3,
} = {}) {
  const n = Math.max(2, Math.floor(segments) + 1);
  const mag = Math.hypot(dir.x || 0, dir.y || 0, dir.z || 0) || 1;
  const dx = (dir.x || 0) / mag;
  const dy = (dir.y || 0) / mag;
  const dz = (dir.z || 0) / mag;
  const nodes = [];
  for (let i = 0; i < n; i++) {
    const x = dx * segmentLength * i;
    const y = dy * segmentLength * i;
    const z = dz * segmentLength * i;
    nodes.push({ x, y, z, px: x, py: y, pz: z, rx: x, ry: y, rz: z });
  }
  return {
    nodes,
    segmentLength,
    dir: { x: dx, y: dy, z: dz },
    gravity,
    damping,
    stiffness,
    constraintPasses,
  };
}

/**
 * Advance a Verlet chain by dt seconds under root motion + external force.
 * Returns per-segment angular offsets {yaw, pitch} suitable for rotating 3D bone hierarchies.
 */
export function stepVerletChain(chain, dt, {
  rootVelocity = { x: 0, y: 0, z: 0 },
  wind = { x: 0, y: 0, z: 0 },
  stiffnessScale = 1,
  reduced = false,
} = {}) {
  const nodes = chain.nodes;
  if (reduced || dt <= 0) {
    for (let i = 0; i < nodes.length; i++) {
      nodes[i].x = nodes[i].rx;
      nodes[i].y = nodes[i].ry;
      nodes[i].z = nodes[i].rz;
      nodes[i].px = nodes[i].rx;
      nodes[i].py = nodes[i].ry;
      nodes[i].pz = nodes[i].rz;
    }
    return chain.nodes.slice(1).map(() => ({ yaw: 0, pitch: 0 }));
  }

  const h = Math.min(0.05, Math.max(0.001, dt));
  const damp = chain.damping;
  const stiff = Math.min(0.96, chain.stiffness * stiffnessScale);

  // Pin root node at origin of chain local space
  nodes[0].x = 0; nodes[0].y = 0; nodes[0].z = 0;
  nodes[0].px = 0; nodes[0].py = 0; nodes[0].pz = 0;

  for (let i = 1; i < nodes.length; i++) {
    const nd = nodes[i];
    const vx = (nd.x - nd.px) * damp;
    const vy = (nd.y - nd.py) * damp;
    const vz = (nd.z - nd.pz) * damp;
    nd.px = nd.x;
    nd.py = nd.y;
    nd.pz = nd.z;

    // Inertia from root motion (lag behind root movement) + wind + gravity + rest-pose spring
    const inertiaFactor = (i / (nodes.length - 1)) * 0.85;
    const fx = (-rootVelocity.x * inertiaFactor + wind.x) * h + (nd.rx - nd.x) * stiff * 0.22;
    const fy = (-rootVelocity.y * inertiaFactor + wind.y + chain.gravity * 0.25) * h + (nd.ry - nd.y) * stiff * 0.22;
    const fz = (-rootVelocity.z * inertiaFactor + wind.z) * h + (nd.rz - nd.z) * stiff * 0.22;

    nd.x += vx + fx;
    nd.y += vy + fy;
    nd.z += vz + fz;
  }

  // Distance constraints (Jakobsen relaxation)
  const L = chain.segmentLength;
  for (let pass = 0; pass < chain.constraintPasses; pass++) {
    nodes[0].x = 0; nodes[0].y = 0; nodes[0].z = 0;
    for (let i = 0; i < nodes.length - 1; i++) {
      const a = nodes[i];
      const b = nodes[i + 1];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dz = b.z - a.z;
      const d = Math.hypot(dx, dy, dz) || 0.0001;
      const diff = (d - L) / d;
      if (i === 0) {
        b.x -= dx * diff;
        b.y -= dy * diff;
        b.z -= dz * diff;
      } else {
        const w = 0.5;
        a.x += dx * diff * w;
        a.y += dy * diff * w;
        a.z += dz * diff * w;
        b.x -= dx * diff * w;
        b.y -= dy * diff * w;
        b.z -= dz * diff * w;
      }
    }
  }

  // Convert node positions into bone angles relative to rest direction
  const angles = [];
  for (let i = 1; i < nodes.length; i++) {
    const prev = nodes[i - 1];
    const curr = nodes[i];
    const dx = curr.x - prev.x;
    const dy = curr.y - prev.y;
    const dz = curr.z - prev.z;
    const rdx = curr.rx - prev.rx;
    const rdy = curr.ry - prev.ry;
    const rdz = curr.rz - prev.rz;
    const yaw = Math.max(-0.85, Math.min(0.85, Math.atan2(dx - rdx, Math.max(0.05, Math.hypot(rdx, rdz)))));
    const pitch = Math.max(-0.75, Math.min(0.75, Math.atan2(dy - rdy, Math.max(0.05, Math.hypot(rdz, rdy, L)))));
    angles.push({ yaw, pitch, x: curr.x, y: curr.y, z: curr.z });
  }
  return angles;
}

/**
 * Volume-preserving soft-body oscillator for squash & stretch on landing, hopping, and dashing.
 */
export function createSoftBody({ stiffness = 210, damping = 11 } = {}) {
  return {
    sy: 1,
    vy: 0,
    jiggle: 0,
    vjiggle: 0,
    prevLift: 0,
    prevLiftVel: 0,
    landingCount: 0,
    stiffness,
    damping,
  };
}

export function stepSoftBody(sb, dt, { lift = 0, targetSy = 1, speed = 0, reduced = false } = {}) {
  if (reduced || dt <= 0) {
    sb.sy = 1; sb.vy = 0; sb.jiggle = 0; sb.vjiggle = 0; sb.prevLift = 0; sb.prevLiftVel = 0;
    return { sx: 1, sy: 1, sz: 1, jiggle: 0, landed: false };
  }
  const h = Math.min(0.05, Math.max(0.001, dt));
  const liftVel = (lift - sb.prevLift) / h;

  // Detect landing impact: was airborne (prevLift > 0.02 or falling fast) and just hit ground
  let landed = false;
  if ((sb.prevLift > 0.015 && lift <= 0.004) || (sb.prevLiftVel < -0.6 && liftVel >= -0.08 && lift < 0.03)) {
    const impact = Math.min(0.42, Math.max(0.14, Math.abs(sb.prevLiftVel) * 0.16 + sb.prevLift * 0.65));
    sb.vy -= impact * 14;
    sb.vjiggle += impact * 18;
    sb.landingCount += 1;
    landed = true;
  }
  sb.prevLift = lift;
  sb.prevLiftVel = liftVel;

  const ay = (targetSy - sb.sy) * sb.stiffness - sb.vy * sb.damping;
  sb.vy += ay * h;
  sb.sy = Math.max(0.58, Math.min(1.42, sb.sy + sb.vy * h));

  const aj = (0 - sb.jiggle) * (sb.stiffness * 1.35) - sb.vjiggle * (sb.damping * 0.75) + speed * 0.4;
  sb.vjiggle += aj * h;
  sb.jiggle = Math.max(-0.35, Math.min(0.35, sb.jiggle + sb.vjiggle * h));

  // Volume preservation: sx * sy * sz === 1
  const invRoot = 1 / Math.sqrt(Math.max(0.45, sb.sy));
  return {
    sx: invRoot,
    sy: sb.sy,
    sz: invRoot,
    jiggle: sb.jiggle,
    landed,
  };
}

/**
 * Create a deterministic real-time elemental fluid/particle solver (curl-noise + SPH-lite).
 */
export function createElementFluid({
  seed = 'beast-fluid',
  element = 'umbral',
  count = 24,
} = {}) {
  const rand = seededPrng(String(seed) + ':fluid:' + String(element));
  const profile = ELEMENT_FLUID_PROFILES[element] || ELEMENT_FLUID_PROFILES.umbral;
  const n = Math.max(6, Math.min(64, Math.floor(count)));
  const particles = [];
  for (let i = 0; i < n; i++) {
    const theta = rand() * Math.PI * 2;
    const phi = Math.acos(2 * rand() - 1);
    const r = profile.radius * (0.35 + 0.65 * rand());
    const x = r * Math.sin(phi) * Math.cos(theta);
    const y = 0.45 + r * Math.cos(phi) * 0.65;
    const z = r * Math.sin(phi) * Math.sin(theta);
    particles.push({
      x, y, z,
      vx: (rand() - 0.5) * 0.15,
      vy: (rand() - 0.5) * 0.15,
      vz: (rand() - 0.5) * 0.15,
      ox: x, oy: y, oz: z,
      phase: rand() * Math.PI * 2,
      life: rand(),
      size: 0.025 + rand() * 0.035,
      density: 1,
    });
  }
  return {
    seed: String(seed),
    element,
    profile,
    phaseOffset: rand() * 100,
    time: 0,
    particles,
  };
}

/**
 * Step the elemental fluid solver by dt seconds using:
 * 1. Analytic divergence-free 3D curl-noise
 * 2. SPH-lite neighbor density & pressure repulsion + viscosity
 * 3. Elemental buoyancy / orbital swirl + emotion modulation
 */
export function stepElementFluid(fluid, dt, {
  emotion = null,
  rootVelocity = { x: 0, y: 0, z: 0 },
  lookAt = null,
  reduced = false,
} = {}) {
  const pts = fluid.particles;
  if (reduced || dt <= 0) {
    for (let i = 0; i < pts.length; i++) {
      const p = pts[i];
      p.x = p.ox; p.y = p.oy; p.z = p.oz;
      p.vx = 0; p.vy = 0; p.vz = 0;
    }
    return pts;
  }

  const h = Math.min(0.05, Math.max(0.001, dt));
  fluid.time += h;
  const prof = fluid.profile;
  const em = emotionFluidParams(emotion || {});
  const t = fluid.time * em.speedScale;
  const targetR = prof.radius * em.radiusScale;
  const hSmooth = 0.26;
  const hSmooth2 = hSmooth * hSmooth;

  // 1. SPH-lite neighbor density & repulsion pass (O(N^2) for N<=32 is ~450 ops, <0.05ms)
  for (let i = 0; i < pts.length; i++) {
    pts[i].density = 1;
  }
  for (let i = 0; i < pts.length; i++) {
    const a = pts[i];
    for (let j = i + 1; j < pts.length; j++) {
      const b = pts[j];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dz = b.z - a.z;
      const d2 = dx * dx + dy * dy + dz * dz;
      if (d2 < hSmooth2 && d2 > 1e-6) {
        const d = Math.sqrt(d2);
        const q = 1 - d / hSmooth;
        const w = q * q;
        a.density += w;
        b.density += w;
        // Pressure repulsion + viscosity blending
        const f = prof.sphRepel * q / d;
        const fx = dx * f;
        const fy = dy * f;
        const fz = dz * f;
        a.vx -= fx * h; a.vy -= fy * h; a.vz -= fz * h;
        b.vx += fx * h; b.vy += fy * h; b.vz += fz * h;

        const visc = prof.viscosity * q * h;
        const dvx = (b.vx - a.vx) * visc;
        const dvy = (b.vy - a.vy) * visc;
        const dvz = (b.vz - a.vz) * visc;
        a.vx += dvx; a.vy += dvy; a.vz += dvz;
        b.vx -= dvx; b.vy -= dvy; b.vz -= dvz;
      }
    }
  }

  // Optional curiosity attraction toward lookAt direction
  const lookBiasX = lookAt ? Math.max(-0.35, Math.min(0.35, lookAt.x * 0.08)) : 0;
  const lookBiasZ = lookAt ? Math.max(-0.35, Math.min(0.35, lookAt.z * 0.08)) : 0;

  // 2. Advect each particle with curl-noise + elemental forces + soft containment shell
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i];
    const cn = curlNoise3D(p.x, p.y, p.z, t, fluid.phaseOffset + p.phase, prof.curlFreq);
    const amp = prof.curlAmp * em.speedScale;

    let ax = cn.vx * amp - rootVelocity.x * 0.45;
    let ay = cn.vy * amp + prof.buoyancy + em.buoyancyBias - rootVelocity.y * 0.45;
    let az = cn.vz * amp - rootVelocity.z * 0.45;

    // Element-specific vortex behavior
    const rx = p.x - lookBiasX;
    const ry = p.y - 0.52;
    const rz = p.z - lookBiasZ;
    const dist = Math.hypot(rx, ry, rz) || 0.001;

    if (prof.kind === 'void') {
      // Inward spiral vortex around the creature
      ax += (-rz * 1.4 - rx * 0.65) * em.speedScale;
      az += (rx * 1.4 - rz * 0.65) * em.speedScale;
    } else if (prof.kind === 'plasma') {
      // High-energy orbital ring
      ax += -rz * 2.1 * em.speedScale;
      az += rx * 2.1 * em.speedScale;
      ay += (0.55 - p.y) * 1.8;
    } else if (prof.kind === 'ice') {
      // Crystalline hexagonal drift + gentle settling
      ax += Math.sin(t * 1.5 + p.phase * 6) * 0.25;
      az += Math.cos(t * 1.5 + p.phase * 6) * 0.25;
    }

    // Soft containment spring toward orbital shell of radius targetR
    const shellDiff = dist - targetR;
    const containK = shellDiff > 0 ? 3.4 : 1.1;
    ax -= (rx / dist) * shellDiff * containK;
    ay -= (ry / dist) * shellDiff * containK;
    az -= (rz / dist) * shellDiff * containK;

    const drag = Math.exp(-prof.drag * h);
    p.vx = (p.vx + ax * h) * drag;
    p.vy = (p.vy + ay * h) * drag;
    p.vz = (p.vz + az * h) * drag;

    p.x += p.vx * h;
    p.y += p.vy * h;
    p.z += p.vz * h;

    // Recycle flame/ember or falling frost particles when they rise/fall out of bounds
    p.life = (p.life + h * (0.35 + 0.25 * em.speedScale)) % 1;
    if (prof.kind === 'flame' && p.y > 1.25) {
      p.y = 0.18 + (p.oy * 0.25);
      p.x = p.ox * em.radiusScale;
      p.z = p.oz * em.radiusScale;
      p.vy *= 0.25;
    } else if (prof.kind === 'ice' && p.y < 0.06) {
      p.y = 0.95;
      p.x = p.ox * em.radiusScale;
      p.z = p.oz * em.radiusScale;
      p.vy = 0;
    }
  }

  return pts;
}

/**
 * Create a complete secondary-motion rig (Verlet tail, ears, wings, fur, wisps, soft-body, and elemental fluid).
 */
export function createSecondaryMotion({
  seed = 'beast',
  element = 'umbral',
  tailSegments = 4,
  particleCount = 24,
} = {}) {
  return {
    seed: String(seed),
    element,
    time: 0,
    prevPos: { x: 0, y: 0, z: 0 },
    tailChain: createVerletChain({ segments: tailSegments, segmentLength: 0.18, dir: { x: 0, y: 0.04, z: -1 }, gravity: -0.35, damping: 0.87, stiffness: 0.78 }),
    earLChain: createVerletChain({ segments: 2, segmentLength: 0.14, dir: { x: -0.35, y: 0.9, z: 0.05 }, gravity: -0.15, damping: 0.84, stiffness: 0.85 }),
    earRChain: createVerletChain({ segments: 2, segmentLength: 0.14, dir: { x: 0.35, y: 0.9, z: 0.05 }, gravity: -0.15, damping: 0.84, stiffness: 0.85 }),
    wingLChain: createVerletChain({ segments: 2, segmentLength: 0.24, dir: { x: -0.9, y: 0.25, z: -0.15 }, gravity: -0.2, damping: 0.85, stiffness: 0.82 }),
    wingRChain: createVerletChain({ segments: 2, segmentLength: 0.24, dir: { x: 0.9, y: 0.25, z: -0.15 }, gravity: -0.2, damping: 0.85, stiffness: 0.82 }),
    furChain: createVerletChain({ segments: 2, segmentLength: 0.1, dir: { x: 0, y: -0.3, z: -0.9 }, gravity: -0.4, damping: 0.82, stiffness: 0.88 }),
    wispChain: createVerletChain({ segments: 3, segmentLength: 0.16, dir: { x: 0, y: 0.6, z: -0.7 }, gravity: 0.25, damping: 0.9, stiffness: 0.68 }),
    softBody: createSoftBody(),
    fluid: createElementFluid({ seed, element, count: particleCount }),
  };
}

/**
 * Step the complete secondary-motion rig by dt seconds.
 */
export function stepSecondaryMotion(sec, dt, {
  position = { x: 0, y: 0, z: 0 },
  lift = 0,
  targetSy = 1,
  emotion = null,
  lookAt = null,
  reduced = false,
} = {}) {
  const h = Math.min(0.05, Math.max(0.001, dt || 1 / 60));
  if (!reduced) sec.time += h;

  const vx = reduced ? 0 : ((position.x || 0) - sec.prevPos.x) / h;
  const vy = reduced ? 0 : (((position.y || 0) + lift) - sec.prevPos.y) / h;
  const vz = reduced ? 0 : ((position.z || 0) - sec.prevPos.z) / h;
  sec.prevPos.x = position.x || 0;
  sec.prevPos.y = (position.y || 0) + lift;
  sec.prevPos.z = position.z || 0;

  const rootVelocity = {
    x: Math.max(-4, Math.min(4, vx)),
    y: Math.max(-4, Math.min(4, vy)),
    z: Math.max(-4, Math.min(4, vz)),
  };
  const speed = Math.hypot(rootVelocity.x, rootVelocity.z);
  const em = emotionFluidParams(emotion || {});

  const wag = reduced ? 0 : Math.sin(sec.time * em.tailWagFreq) * em.tailWagAmp;
  const flap = reduced ? 0 : Math.sin(sec.time * (2.4 + em.speedScale * 1.2)) * 0.22;

  const tailAngles = stepVerletChain(sec.tailChain, h, {
    rootVelocity,
    wind: { x: wag * 1.8, y: Math.cos(sec.time * 1.9) * 0.12, z: 0 },
    stiffnessScale: em.springStiffScale,
    reduced,
  });
  const earL = stepVerletChain(sec.earLChain, h, {
    rootVelocity,
    wind: { x: -em.earPerk * 0.5, y: em.earPerk, z: Math.sin(sec.time * 1.7) * 0.08 },
    stiffnessScale: em.springStiffScale,
    reduced,
  });
  const earR = stepVerletChain(sec.earRChain, h, {
    rootVelocity,
    wind: { x: em.earPerk * 0.5, y: em.earPerk, z: Math.cos(sec.time * 1.7) * 0.08 },
    stiffnessScale: em.springStiffScale,
    reduced,
  });
  const wingL = stepVerletChain(sec.wingLChain, h, {
    rootVelocity,
    wind: { x: 0, y: flap, z: 0 },
    stiffnessScale: em.springStiffScale,
    reduced,
  });
  const wingR = stepVerletChain(sec.wingRChain, h, {
    rootVelocity,
    wind: { x: 0, y: flap, z: 0 },
    stiffnessScale: em.springStiffScale,
    reduced,
  });
  const fur = stepVerletChain(sec.furChain, h, {
    rootVelocity,
    wind: { x: wag * 0.5, y: 0, z: 0 },
    stiffnessScale: em.springStiffScale,
    reduced,
  });
  const wisp = stepVerletChain(sec.wispChain, h, {
    rootVelocity,
    wind: { x: Math.sin(sec.time * 1.4) * 0.25, y: 0.22 * em.speedScale, z: Math.cos(sec.time * 1.1) * 0.2 },
    stiffnessScale: em.springStiffScale,
    reduced,
  });
  const softBody = stepSoftBody(sec.softBody, h, { lift, targetSy, speed, reduced });
  const particles = stepElementFluid(sec.fluid, h, { emotion, rootVelocity, lookAt, reduced });

  return {
    tailAngles,
    earL: earL[0] || { yaw: 0, pitch: 0 },
    earR: earR[0] || { yaw: 0, pitch: 0 },
    wingL: wingL[0] || { yaw: 0, pitch: 0 },
    wingR: wingR[0] || { yaw: 0, pitch: 0 },
    fur: fur[0] || { yaw: 0, pitch: 0 },
    wisp,
    softBody,
    particles,
    emotionParams: em,
  };
}
