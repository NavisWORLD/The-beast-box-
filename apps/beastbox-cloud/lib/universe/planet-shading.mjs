// GENERATED from Cosmo's planets pack models.json (shading, clouds, atmosphere per type).
export const PLANET_SHADING={
 "temperate": {
  "shading": {
   "sky_color": [
    0.3,
    0.52,
    1.0
   ],
   "twilight_color": [
    1.0,
    0.52,
    0.42
   ],
   "atmo_amount": 0.85,
   "shallow_color": [
    0.2,
    0.62,
    0.78
   ],
   "deep_color": [
    0.04,
    0.16,
    0.42
   ],
   "glint_roughness": 0.2,
   "wave_strength": 0.8,
   "emissive_day_keep": 0.12,
   "night_lights": 1.0,
   "earthshine": 0,
   "is_moon": false
  },
  "clouds": {
   "texture_far": "textures/temperate_clouds_512x256.webp",
   "texture_near": "textures/temperate_clouds_2048x1024.webp",
   "altitude_frac": 0.006,
   "shadow_strength": 0.55,
   "near_shell": "models/temperate_near.glb scaled by 1+altitude_frac, transparent, depthWrite=false, no mipmaps if shadows use dirToUv",
   "rotation_deg_per_min": 0.4
  },
  "atmosphere": {
   "uDensity": 0.18,
   "uMie": 0.6,
   "uSkyColor": [
    0.3,
    0.52,
    1.0
   ],
   "uTwilightColor": [
    1.0,
    0.52,
    0.42
   ]
  },
  "shell": 1.045
 },
 "desert": {
  "shading": {
   "sky_color": [
    0.95,
    0.62,
    0.38
   ],
   "twilight_color": [
    0.75,
    0.4,
    0.95
   ],
   "atmo_amount": 0.55,
   "shallow_color": [
    0.18,
    0.62,
    0.66
   ],
   "deep_color": [
    0.05,
    0.3,
    0.4
   ],
   "glint_roughness": 0.26,
   "wave_strength": 0.7,
   "emissive_day_keep": 0.12,
   "night_lights": 1.0,
   "earthshine": 0,
   "is_moon": false
  },
  "clouds": {
   "texture_far": "textures/desert_clouds_512x256.webp",
   "texture_near": "textures/desert_clouds_2048x1024.webp",
   "altitude_frac": 0.005,
   "shadow_strength": 0.35,
   "near_shell": "models/desert_near.glb scaled by 1+altitude_frac, transparent, depthWrite=false, no mipmaps if shadows use dirToUv",
   "rotation_deg_per_min": 0.4
  },
  "atmosphere": {
   "uDensity": 0.14,
   "uMie": 0.8,
   "uSkyColor": [
    0.95,
    0.62,
    0.38
   ],
   "uTwilightColor": [
    0.75,
    0.4,
    0.95
   ]
  },
  "shell": 1.035
 },
 "ice": {
  "shading": {
   "sky_color": [
    0.55,
    0.8,
    1.0
   ],
   "twilight_color": [
    0.6,
    0.55,
    1.0
   ],
   "atmo_amount": 0.5,
   "shallow_color": [
    0.1,
    0.3,
    0.52
   ],
   "deep_color": [
    0.05,
    0.14,
    0.3
   ],
   "glint_roughness": 0.16,
   "wave_strength": 0.4,
   "emissive_day_keep": 0.2,
   "night_lights": 1.0,
   "earthshine": 0,
   "is_moon": false
  },
  "clouds": {
   "texture_far": "textures/ice_clouds_512x256.webp",
   "texture_near": "textures/ice_clouds_2048x1024.webp",
   "altitude_frac": 0.005,
   "shadow_strength": 0.3,
   "near_shell": "models/ice_near.glb scaled by 1+altitude_frac, transparent, depthWrite=false, no mipmaps if shadows use dirToUv",
   "rotation_deg_per_min": 0.4
  },
  "atmosphere": {
   "uDensity": 0.12,
   "uMie": 0.5,
   "uSkyColor": [
    0.55,
    0.8,
    1.0
   ],
   "uTwilightColor": [
    0.6,
    0.55,
    1.0
   ]
  },
  "shell": 1.035
 },
 "volcanic": {
  "shading": {
   "sky_color": [
    0.85,
    0.32,
    0.22
   ],
   "twilight_color": [
    1.0,
    0.3,
    0.45
   ],
   "atmo_amount": 0.6,
   "shallow_color": [
    0.13,
    0.07,
    0.2
   ],
   "deep_color": [
    0.05,
    0.03,
    0.09
   ],
   "glint_roughness": 0.3,
   "wave_strength": 0.5,
   "emissive_day_keep": 1.0,
   "night_lights": 0.5,
   "earthshine": 0,
   "is_moon": false
  },
  "clouds": {
   "texture_far": "textures/volcanic_clouds_512x256.webp",
   "texture_near": "textures/volcanic_clouds_2048x1024.webp",
   "altitude_frac": 0.006,
   "shadow_strength": 0.5,
   "near_shell": "models/volcanic_near.glb scaled by 1+altitude_frac, transparent, depthWrite=false, no mipmaps if shadows use dirToUv",
   "rotation_deg_per_min": 0.4
  },
  "atmosphere": {
   "uDensity": 0.16,
   "uMie": 0.5,
   "uSkyColor": [
    0.85,
    0.32,
    0.22
   ],
   "uTwilightColor": [
    1.0,
    0.3,
    0.45
   ]
  },
  "shell": 1.04
 },
 "moon": {
  "shading": {
   "sky_color": [
    0,
    0,
    0
   ],
   "twilight_color": [
    0,
    0,
    0
   ],
   "atmo_amount": 0.0,
   "shallow_color": [
    0,
    0,
    0
   ],
   "deep_color": [
    0,
    0,
    0
   ],
   "glint_roughness": 0.2,
   "wave_strength": 0,
   "emissive_day_keep": 0.3,
   "night_lights": 1.0,
   "earthshine": 0.035,
   "is_moon": true
  },
  "clouds": null,
  "atmosphere": null,
  "shell": null
 }
};
export const PLANET_LOD={"sprite_in": 0.004, "sprite_full_out": 0.012, "far_to_near_start": 0.3, "far_to_near_end": 0.55, "detail_start": 0.45, "detail_end": 0.9, "atmo_fade_in": 0.01, "atmo_fade_full": 0.03};
