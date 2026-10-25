export const MODEL_SLOT_SCHEMA: string;
export const MODEL_SLOT_BASE: string;
export const CLIP_ROLES: readonly string[];
export function validateRig(rig: any, id: string): {ok: boolean; errors: string[]};
export function resolveModelEntry(manifest: any, id: string, base?: string): {id: string; glb: string; rig: string; glbLow: string | null} | null;
export function pickClipName(names: string[], role: string, rigClips?: Record<string, string>): string | null;
export function fitScale(h: number, target: number): number;
export function roleFor(l?: {speed?: number; sleep?: number; startle?: number; joy?: number}): string;
