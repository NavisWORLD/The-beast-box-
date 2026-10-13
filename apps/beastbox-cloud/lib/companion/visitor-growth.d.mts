export type VisitorGrowth = {
 schema: 'beastbox-visitor-growth-v1'; visitorId: string; beastKey: string;
 exchanges: number; curiosity: number; resonance: number; stability: number; signal: number;
 stimulus: { source: 'LOCAL_CLASSICAL_QVM_INSPIRED'; shots: number; counts: Record<'00'|'01'|'10'|'11',number> };
};
export const VISITOR_ID_KEY: string;
export const GROWTH_PREFIX: string;
export const GROWTH_SOURCE: string;
export function getOrCreateVisitorId(storage: Pick<Storage,'getItem'|'setItem'> | null, createId?: () => string): string | null;
export function freshGrowth(visitorId: string, beastKey: string): VisitorGrowth;
export function readVisitorGrowth(storage: Pick<Storage,'getItem'> | null, visitorId: string, beastKey: string): VisitorGrowth;
export function writeVisitorGrowth(storage: Pick<Storage,'setItem'> | null, growth: VisitorGrowth): boolean;
export function advanceVisitorGrowth(previous: VisitorGrowth, input?: {text?: string;reply?: string;verified?: boolean}): VisitorGrowth;
export function growthModelContext(growth: VisitorGrowth | null): string;
