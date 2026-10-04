export const RECORDED_RUN: {
  key: string; backend: string; job_id: string; pub_index: number; num_bits: number;
  shots: number; counts: Record<string, number>; counts_sha256: string;
};
export const MOOD: Record<string, string>;
export function personalityFromGenome(genome: Record<string, any>): Record<string, any>;
export function birth(profile?: string): { genome: Record<string, any>; card: Record<string, any>; traits: { focus: number; calm: number; spark: number } };
export function refusal(card: Record<string, any>): string;
export function reply(card: Record<string, any>, user: string, memories?: Array<Record<string, any>>): string;
export function embed(text: string, dim?: number): number[];
export function searchRecords(records: Array<Record<string, any>>, query: string, k?: number): Array<Record<string, any>>;
export class CompanionMemory {
  records: Array<Record<string, any>>;
  constructor(records?: Array<Record<string, any>>);
  add(text: string, kind: string, source: string): Record<string, any>;
  search(query: string, k?: number): Array<Record<string, any>>;
  exportQbeast(genome: Record<string, any>): string;
}
export function acceptVision(event: Record<string, any>): Record<string, any>;
export function acceptHearing(event: Record<string, any>): Record<string, any>;
export function nudgeTraits(base: { focus: number; calm: number; spark: number }, events: Array<Record<string, any>>): { focus: number; calm: number; spark: number };
export function liveAnimation(traits: { focus: number; calm: number; spark: number }, events: Array<Record<string, any>>): string;
export function simulateLive(baseTraits: { focus: number; calm: number; spark: number }, events: Array<Record<string, any>>): Record<string, any>;
export function loopbackOnly(url: string): boolean;
