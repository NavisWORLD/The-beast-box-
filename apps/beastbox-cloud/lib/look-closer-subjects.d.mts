export const LOOK_SUBJECT_IDS: readonly string[];
export function captionKeepsHonesty(text: unknown): boolean;
export function lookSubjectLabels(id: string, opts?: {activeName?: string; profileName?: string; labels?: any}): {id: string; button: string; headingName: string; stageName: string; caption: string | null; attributionKind: string | null; explainName: string};
