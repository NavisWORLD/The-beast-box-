export const NODE_RIG_FORMAT: string;
export const NODE_ACTIONS: readonly string[];
export const ROLE_TO_ACTION: Readonly<Record<string, string>>;
export type NodePose = {p: number[]; r: [number[], number][]; s: number[]};
export function isNodeRig(rig: any): boolean;
export function validateNodeRig(rig: any): string[];
export function applyActionMultipliers(rig: any, mult?: {amp?: number; tempo?: number; blink_hold?: number}): any;
export function blinkClosure(blink: any, t: number): number;
export function nodeRigPose(rig: any, t: number, o?: {action?: string; w?: number; sleepK?: number}): {nodes: Record<string, NodePose>; eye: number};
