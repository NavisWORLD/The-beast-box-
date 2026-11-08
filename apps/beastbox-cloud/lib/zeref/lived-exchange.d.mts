export const LIVED_MOUTH_SCHEMA: string;
export function mintExchangeId(scope: string, identity: string, text: string): Promise<string>;
export function environmentIsNotCanonical(environment: unknown): {ignored: boolean; snapshot: null};
export function mouthReceipt(raw: unknown, options?: {
  exchangeId?: string | null; scope?: 'guest' | 'visitor' | 'owner'; spokenBy?: string | null; environment?: unknown;
}): Record<string, unknown> | null;
export function speakLived(input: {
  exchangeId?: string; gated?: unknown; growing?: unknown; chosen?: string | null; growingFailed?: boolean;
}): Record<string, unknown> | null;
export function ownerTalkReceipt(payload: unknown, exchangeId?: string | null): Record<string, unknown> | null;
