// First-person look keys (additive). Page-wide keys must never steal arrows from a text field.
export function isTypingTarget(t: unknown): boolean {
  const el = t as any;
  if (!el || typeof el !== 'object') return false;
  const tag = String(el.tagName || '').toUpperCase();
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (el.isContentEditable) return true;
  if (typeof el.closest === 'function' && el.closest('[contenteditable=""],[contenteditable="true"],[role="textbox"]')) return true;
  return false;
}
export function isScrollPanel(t: unknown): boolean {
  const el = t as any;
  return !!(el && typeof el.closest === 'function' && el.closest('[data-lw-scroll],dialog,[role="dialog"]'));
}
/** One tap = a visible step. Up looks up (+pitch), Left turns left (+yaw). */
export function fpLookKeyStep(k: string): { yaw: number; pitch: number } {
  switch (k.toLowerCase()) {
    case 'arrowup': case 'pageup': return { yaw: 0, pitch: 0.12 };
    case 'arrowdown': case 'pagedown': return { yaw: 0, pitch: -0.12 };
    case 'arrowleft': return { yaw: 0.2, pitch: 0 };
    case 'arrowright': return { yaw: -0.2, pitch: 0 };
    default: return { yaw: 0, pitch: 0 };
  }
}
