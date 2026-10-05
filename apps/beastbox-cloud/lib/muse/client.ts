'use client';
/** Browser side of the Meta Muse pairing. The device secret stays in this browser only. */
export const LINK_KEY = 'beastbox-muse-link-v1';
export const LINK_EVENT = 'beastbox:muse-link';

export type MuseLink = { deviceSecret: string; linkedAt: string; applied: string[] };

export function readLink(): MuseLink | null {
  try {
    const raw = localStorage.getItem(LINK_KEY);
    const v = raw ? JSON.parse(raw) : null;
    return v && typeof v.deviceSecret === 'string' && v.deviceSecret.startsWith('bbm_dev_') ? { applied: [], ...v } : null;
  } catch { return null; }
}
export function writeLink(link: MuseLink | null) {
  try { link ? localStorage.setItem(LINK_KEY, JSON.stringify(link)) : localStorage.removeItem(LINK_KEY); } catch { /* private mode */ }
  window.dispatchEvent(new Event(LINK_EVENT));
}

export async function museApi(path: string, init: { method?: string; body?: unknown; secret?: string } = {}) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (init.secret) headers.Authorization = 'Bearer ' + init.secret;
  const res = await fetch('/api/muse/' + path, { method: init.method || 'GET', headers, body: init.body === undefined ? undefined : JSON.stringify(init.body), cache: 'no-store' });
  let data: any = null;
  try { data = await res.json(); } catch { data = null; }
  return { ok: res.ok, status: res.status, data };
}

export function museCodeSnippet(connectorUrl: string, token = '<paste a Beast Box token>') {
  return JSON.stringify({ mcp_servers: { beastbox: { transport: 'streamable_http', url: connectorUrl, headers: { Authorization: 'Bearer ' + token }, mode: 'optional' } } }, null, 2);
}
