// Cosmo's P1 post-chain look pack (p1post.json, SEEDED), frozen as a module. Generated from /workspace/cosmo-study/universe/p1post/p1post.json; do not hand-edit values.
// A designed screen effect, not a measurement. One sun only; no second light.
export const P1POST=Object.freeze({
 "pack": "p1post",
 "version": 1,
 "label": "SEEDED",
 "honesty": "Look settings for a post chain. A designed screen effect, not real physics, not a measurement. One sun only; no second light.",
 "chain_order": [
  "RenderPass (tone mapping ACES, exposure 0.85, outputColorSpace sRGB)",
  "GodRays (gated, additive on the ray sum only)",
  "Bloom (threshold above grass tips)",
  "Optics (grain, CA, vignette; subtle)",
  "OutputPass"
 ],
 "glare_budget": {
  "grass_tip_scene_lum_worst": 1.0469,
  "grass_tip_warm_hex": "#8B9B55 mixed 0.4 to #B5A45A",
  "label": "DERIVED",
  "rule": "bloom threshold (scene luminance after exposure, before ACES) >= 1.25 x worst lit grass tip and > sky horizon, so only the sun disc and lava/glow emissives bloom",
  "sky_horizon_lum": 0.6405
 },
 "sun_gate": {
  "apply": "final = base + rays * exposure * sun_visible (never multiply the base frame)",
  "label": "DERIVED",
  "occluded": "depth test of the sun disc centre (1 sample) or 0 if unavailable",
  "on_screen": "smoothstep(1.3, 0.9, max(|ndc.x|, |ndc.y|))",
  "pack_sun": {
   "dir": [
    0.5779,
    0.5154,
    -0.6328
   ],
   "elevation_deg": 31.0217,
   "intensity": 3.0283
  },
  "source": "the ONE engine sun (oneworld SUN, oneSunAt elevation); companion disc never gates or casts rays",
  "sun_visible": "smoothstep(-2, 6, sun_elevation_deg) * on_screen * (1 - occluded)"
 },
 "tier_rule": "cost and strength never decrease LOW->GOD; bloom threshold never increases; MED is the default and stays subtle",
 "tiers": {
  "GOD": {
   "bloom": {
    "enabled": true,
    "radius": 0.427,
    "resolution": "full",
    "strength": 0.5604,
    "threshold": 1.3119
   },
   "budget": {
    "frame_ms": 16.7,
    "max_dpr": 2.0,
    "render_scale": 1.0,
    "shadow_distance_m": 150,
    "shadow_map": 4096,
    "shadow_type": "PCFSoft"
   },
   "god_rays": {
    "bright_gate": [
     0.8,
     1.0
    ],
    "decay": 0.944,
    "density": 0.711,
    "enabled": true,
    "exposure": 0.2995,
    "samples": 32,
    "weight": 0.3227
   },
   "label": "SEEDED",
   "optics": {
    "chromatic_aberration": 0.0352,
    "edge_blur": 0.1,
    "exposure": 0.85,
    "gamma": 1.0,
    "grain": 0.0348,
    "grain_seed": "frame counter hashed from the pack seed, never Math.random",
    "tone_mapping": "ACESFilmic",
    "vignette": 0.15
   }
  },
  "HIGH": {
   "bloom": {
    "enabled": true,
    "radius": 0.3476,
    "resolution": "half",
    "strength": 0.4557,
    "threshold": 1.3495
   },
   "budget": {
    "frame_ms": 16.7,
    "max_dpr": 2.0,
    "render_scale": 1.0,
    "shadow_distance_m": 80,
    "shadow_map": 2048,
    "shadow_type": "PCFSoft"
   },
   "god_rays": {
    "bright_gate": [
     0.8,
     1.0
    ],
    "decay": 0.9362,
    "density": 0.6412,
    "enabled": true,
    "exposure": 0.2554,
    "samples": 20,
    "weight": 0.2824
   },
   "label": "SEEDED",
   "optics": {
    "chromatic_aberration": 0.025,
    "edge_blur": 0.05,
    "exposure": 0.85,
    "gamma": 1.0,
    "grain": 0.025,
    "grain_seed": "frame counter hashed from the pack seed, never Math.random",
    "tone_mapping": "ACESFilmic",
    "vignette": 0.12
   }
  },
  "LOW": {
   "bloom": {
    "enabled": false,
    "radius": 0.0,
    "resolution": "half",
    "strength": 0.0,
    "threshold": 1.4411
   },
   "budget": {
    "frame_ms": 16.7,
    "max_dpr": 1.0,
    "render_scale": 0.7,
    "shadow_distance_m": 0,
    "shadow_map": 0,
    "shadow_type": "none"
   },
   "god_rays": {
    "bright_gate": [
     0.8,
     1.0
    ],
    "decay": 0.0,
    "density": 0.0,
    "enabled": false,
    "exposure": 0.0,
    "samples": 0,
    "weight": 0.0
   },
   "label": "SEEDED",
   "optics": {
    "chromatic_aberration": 0.0,
    "edge_blur": 0.0,
    "exposure": 0.85,
    "gamma": 1.0,
    "grain": 0.0,
    "grain_seed": "frame counter hashed from the pack seed, never Math.random",
    "tone_mapping": "ACESFilmic",
    "vignette": 0.0
   }
  },
  "MED": {
   "bloom": {
    "enabled": true,
    "radius": 0.2525,
    "resolution": "half",
    "strength": 0.3218,
    "threshold": 1.3925
   },
   "budget": {
    "frame_ms": 16.7,
    "max_dpr": 1.5,
    "render_scale": 0.85,
    "shadow_distance_m": 40,
    "shadow_map": 1024,
    "shadow_type": "PCF"
   },
   "god_rays": {
    "bright_gate": [
     0.8,
     1.0
    ],
    "decay": 0.9189,
    "density": 0.549,
    "enabled": true,
    "exposure": 0.1967,
    "samples": 12,
    "weight": 0.2161
   },
   "label": "SEEDED",
   "optics": {
    "chromatic_aberration": 0.0149,
    "edge_blur": 0.0,
    "exposure": 0.85,
    "gamma": 1.0,
    "grain": 0.0151,
    "grain_seed": "frame counter hashed from the pack seed, never Math.random",
    "tone_mapping": "ACESFilmic",
    "vignette": 0.08
   }
  }
 },
 "seed": {
  "genesis": "RECORDED ibm_marrakesh job db4l2uclf4us73c2td10",
  "genesis_sha256": "f45ccdf9652f608b293bd2081e520aa0168804b6ee50c58d951fed4a1edb714e",
  "stream": "beastbox-p1post-v1"
 }
});
