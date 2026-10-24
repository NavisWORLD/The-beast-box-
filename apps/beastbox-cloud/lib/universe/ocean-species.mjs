// Species table for Cosmo's ocean-life pack v1. GENERATED from public/universe/livingworld/oceanlife/models/models.json (sizes, depth bands,
// speeds, LOD distances, school sizes, clip periods are Cosmo's numbers). water_biomes keeps only tags that exist in the engine's water
// LEGEND ids (deep_ocean, shallow_ocean, jelly_geyser, frozen_sea); land tags (rainforest, beach, grassland, ...) are dropped because a fish cannot live there.
export const OCEAN_SPECIES=Object.freeze({
 "fish_a": {
  "size_m": 0.32,
  "depth_m": [
   0.5,
   8.0
  ],
  "cruise_mps": 0.9,
  "burst_mps": 2.2,
  "lod_near_to_far_m": 4.6,
  "lod_far_to_billboard_m": 18.5,
  "school_n": [
   12,
   40
  ],
  "school_radius_m": 1.6,
  "water_biomes": [
   "shallow_ocean"
  ],
  "clips": {
   "swim": 0.7
  },
  "bbox_near": [
   [
    -0.101,
    -0.106,
    -0.208
   ],
   [
    0.101,
    0.126,
    0.16
   ]
  ]
 },
 "fish_b": {
  "size_m": 0.26,
  "depth_m": [
   6.0,
   40.0
  ],
  "cruise_mps": 0.7,
  "burst_mps": 1.8,
  "lod_near_to_far_m": 3.8,
  "lod_far_to_billboard_m": 15.0,
  "school_n": [
   8,
   24
  ],
  "school_radius_m": 2.2,
  "water_biomes": [
   "deep_ocean",
   "frozen_sea",
   "jelly_geyser"
  ],
  "clips": {
   "swim": 0.55
  },
  "bbox_near": [
   [
    -0.077,
    -0.088,
    -0.169
   ],
   [
    0.077,
    0.088,
    0.164
   ]
  ]
 },
 "fish_c": {
  "size_m": 0.44,
  "depth_m": [
   2.0,
   20.0
  ],
  "cruise_mps": 1.1,
  "burst_mps": 2.6,
  "lod_near_to_far_m": 6.4,
  "lod_far_to_billboard_m": 25.4,
  "school_n": [
   10,
   30
  ],
  "school_radius_m": 2.0,
  "water_biomes": [
   "shallow_ocean",
   "deep_ocean"
  ],
  "clips": {
   "swim": 0.9
  },
  "bbox_near": [
   [
    -0.129,
    -0.123,
    -0.286
   ],
   [
    0.129,
    0.163,
    0.218
   ]
  ]
 },
 "jelly": {
  "size_m": 0.72,
  "depth_m": [
   3.0,
   45.0
  ],
  "cruise_mps": 0.2,
  "burst_mps": 0.5,
  "lod_near_to_far_m": 10.4,
  "lod_far_to_billboard_m": 41.6,
  "school_n": [
   5,
   25
  ],
  "school_radius_m": 4.0,
  "water_biomes": [
   "jelly_geyser",
   "deep_ocean"
  ],
  "clips": {
   "pulse": 2.4
  },
  "bbox_near": [
   [
    -0.374,
    -1.219,
    -0.374
   ],
   [
    0.374,
    0.36,
    0.374
   ]
  ]
 },
 "manta": {
  "size_m": 4.2,
  "depth_m": [
   1.0,
   18.0
  ],
  "cruise_mps": 2.0,
  "burst_mps": 4.5,
  "lod_near_to_far_m": 60.6,
  "lod_far_to_billboard_m": 242.5,
  "school_n": [
   1,
   5
  ],
  "school_radius_m": 12.0,
  "water_biomes": [
   "shallow_ocean",
   "deep_ocean"
  ],
  "clips": {
   "glide": 6.0
  },
  "bbox_near": [
   [
    -2.1,
    -0.22,
    -2.1
   ],
   [
    2.1,
    0.231,
    1.671
   ]
  ]
 },
 "turtle": {
  "size_m": 1.0,
  "depth_m": [
   0.0,
   10.0
  ],
  "cruise_mps": 0.6,
  "burst_mps": 1.4,
  "lod_near_to_far_m": 14.4,
  "lod_far_to_billboard_m": 57.8,
  "school_n": [
   1,
   4
  ],
  "school_radius_m": 6.0,
  "water_biomes": [
   "shallow_ocean"
  ],
  "clips": {
   "paddle": 3.2
  },
  "bbox_near": [
   [
    -0.919,
    -0.188,
    -0.634
   ],
   [
    0.919,
    0.346,
    0.692
   ]
  ]
 },
 "seabird": {
  "size_m": 0.4,
  "depth_m": [
   -0.05,
   0.05
  ],
  "cruise_mps": 0.15,
  "burst_mps": 9.0,
  "lod_near_to_far_m": 5.8,
  "lod_far_to_billboard_m": 23.1,
  "school_n": [
   3,
   14
  ],
  "school_radius_m": 5.0,
  "water_biomes": [
   "frozen_sea",
   "shallow_ocean"
  ],
  "clips": {
   "flap": 0.35,
   "float": 3.2
  },
  "bbox_near": [
   [
    -0.4,
    -0.065,
    -0.27
   ],
   [
    0.4,
    0.265,
    0.295
   ]
  ]
 },
 "whale": {
  "size_m": 12.0,
  "depth_m": [
   0.0,
   60.0
  ],
  "cruise_mps": 2.5,
  "burst_mps": 7.5,
  "lod_near_to_far_m": 173.2,
  "lod_far_to_billboard_m": 693.0,
  "school_n": [
   1,
   3
  ],
  "school_radius_m": 40.0,
  "water_biomes": [
   "deep_ocean",
   "frozen_sea"
  ],
  "clips": {
   "tail_swim": 4.0,
   "fin_sweep": 5.0,
   "breach": 6.0
  },
  "bbox_near": [
   [
    -2.739,
    -2.096,
    -6.751
   ],
   [
    2.739,
    2.205,
    5.938
   ]
  ]
 }
});
