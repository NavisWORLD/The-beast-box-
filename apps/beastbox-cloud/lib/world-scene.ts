// Shared "world scene" backdrop (Cosmo's visual audit): night sky, aurora band, distant hills and a grassy floor, in place of
// the old dark-purple boxed backdrops on Look Closer, Field game and Open Field. Pure CSS layers; no images, no randomness.
export const WORLD_SCENE_BG=[
 'radial-gradient(1.5px 1.5px at 12% 18%,#fff9 50%,transparent 51%)','radial-gradient(1px 1px at 34% 9%,#fffa 50%,transparent 51%)',
 'radial-gradient(1.5px 1.5px at 61% 22%,#fff8 50%,transparent 51%)','radial-gradient(1px 1px at 82% 12%,#fff9 50%,transparent 51%)',
 'radial-gradient(1px 1px at 72% 34%,#fff7 50%,transparent 51%)','radial-gradient(1px 1px at 22% 38%,#fff6 50%,transparent 51%)',
 'radial-gradient(ellipse 70% 18% at 50% 30%,#5be3d533,transparent 70%)',
 'radial-gradient(ellipse 90% 30% at 20% 74%,#1f3a4a 60%,transparent 61%)','radial-gradient(ellipse 80% 26% at 85% 76%,#243d52 60%,transparent 61%)',
 'linear-gradient(180deg,#0b0f2e 0%,#1b1f56 42%,#3b2d6b 62%,#1e5a47 70%,#174a36 82%,#0e2f22 100%)'].join(',');
export const WORLD_SCENE_STYLE={background:WORLD_SCENE_BG} as const;
