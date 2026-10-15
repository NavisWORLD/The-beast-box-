export const CATALOG_BODIES: string[];
export const MAX_MOBILE_TRIANGLES: number;
export function catalogRowToGenome(catalogIndex: any, rowOrIndex?: number | any[]): any;
export function deriveCatalogPalette(genome?: any): {
  island: string;
  base: number;
  baseShadow: number;
  baseLight: number;
  alt: number;
  belly: number;
  accent: number;
  glow: number;
  cheek: number;
  dark: number;
  nose: number;
  beak: number;
  white: number;
  eye: number;
  iris: number;
};
export function buildCatalogCreatureRig(THREE: any, genome?: any, opts?: { stage?: number; quality?: 'auto' | 'low' }): {
  body: string;
  element: string;
  palette: ReturnType<typeof deriveCatalogPalette>;
  root: any;
  joints: any;
  secondary: any;
  triangles: number;
  dispose: () => void;
};
export function poseCatalogCreature(rig: any, opts?: {
  actorPose?: any;
  emotion?: any;
  dt?: number;
  time?: number;
  lookAt?: { x: number; z: number } | null;
  speaking?: boolean;
  reduced?: boolean;
}): {
  state: string;
  sx: number;
  sy: number;
  sz: number;
  lift: number;
  blink: number;
  shadowScale: number;
  tailYaw: number;
  wingFlap: number;
};
export function measureCatalogSilhouette(THREE: any, rig: any): Record<'front' | 'side' | 'back' | 'threeQuarter', {
  width: number;
  height: number;
  depth: number;
  noseZ: number;
  minY: number;
}>;
