import type {GrowthNode, GrowthState} from './seeded-growth-nodes.mjs';
export const WISH_NODE_SOURCE: 'zeref-message-center';
export type WishSeed = {word: string; planted_at_utc?: string | null; wish_text?: string; wish_sha256: string; prompt_seed?: string | null; tag?: string | null; step?: number | null; evidence?: string};
export type WishSeedRegistry = {schema?: string; planted?: string[]; seeds?: WishSeed[]; planted_without_evidence?: string[]};
export type WishGrowthNode = GrowthNode & {wish_word: string; wish_sha256: string; planted_at_utc: string | null; prompt_seed: string | null; source: 'zeref-message-center'};
export type WishGrowthNodeAt = WishGrowthNode & GrowthState & {tick: number};
type U = {seed?: any; planets?: any[]; history?: any[]; storms?: any[]; entanglement_E?: number; tick?: number};
export function wishSeededGrowthNodes(registry: WishSeedRegistry | null | undefined, u: U, o?: {home?: string | null}): WishGrowthNode[];
export function wishGrowthNodesAt(registry: WishSeedRegistry | null | undefined, u: U, tick?: number, o?: {home?: string | null}): WishGrowthNodeAt[];
