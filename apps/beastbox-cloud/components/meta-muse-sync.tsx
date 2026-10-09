'use client';
import { useEffect, useRef } from 'react';
import { useBeastSession } from './beast-session';
import { care, nameBeast, rememberExchange } from '../lib/companion/adventure.mjs';
import { exportSession } from '../lib/companion/session.mjs';
import { minimalSnapshot } from '../lib/muse/snapshot.mjs';
import { LINK_EVENT, museApi, readLink, writeLink } from '../lib/muse/client';

const EVERY_MS = 20_000;

/**
 * Opt-in Meta Muse sync. Renders nothing. Does nothing until this browser was paired
 * in the Pair with Meta Muse panel. Then it pushes a minimal beast snapshot and pulls
 * back care actions Muse made, applying them with the same care rules as the cage.
 */
export default function MetaMuseSync() {
  const { ready, session, trail, change } = useBeastSession();
  const latest = useRef({ session, trail });
  latest.current = { session, trail };
  const busy = useRef(false);
  const kick = useRef<() => void>(() => undefined);

  useEffect(() => {
    if (!ready) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    async function sync() {
      const link = readLink();
      if (!link || busy.current || stopped || document.visibilityState === 'hidden') return;
      busy.current = true;
      try {
        const { session: s, trail: t } = latest.current;
        const snapshot = s ? minimalSnapshot(exportSession(s), t) : undefined;
        const res = await museApi('sync', { method: 'POST', secret: link.deviceSecret, body: { snapshot, ack: link.applied } });
        if (res.status === 401) { writeLink(null); return; }
        if (!res.ok || !res.data) return;
        const actions: Array<{ id: string; type: string; args: any; seed?: string }> = Array.isArray(res.data.actions) ? res.data.actions : [];
        const seen = new Set(link.applied);
        const fresh = actions.filter((a) => !seen.has(a.id));
        if (fresh.length) {
          const saved=await change((draft) => {
            for (const a of fresh) {
              if (!draft.beast || (a.seed && draft.beast.seed !== a.seed)) continue;
              if (a.type === 'feed') care(draft, 'feed');
              else if (a.type === 'play') care(draft, a.args?.activity === 'spark' ? 'spark' : 'pet');
              else if (a.type === 'rename') nameBeast(draft, String(a.args?.name || ''));
              else if (a.type === 'talk') rememberExchange(draft, String(a.args?.you || ''), String(a.args?.beast || ''));
            }
          });
          if(!saved.ok)return;
        }
        const still = new Set(actions.map((a) => a.id));
        const applied = [...link.applied.filter((id) => still.has(id)), ...fresh.map((a) => a.id)].slice(-100);
        const now = readLink();
        if (now && now.deviceSecret === link.deviceSecret) writeLink({ ...now, applied });
        if (fresh.length) setTimeout(() => kick.current(), 1500);
      } catch { /* offline: try again on the next tick */ }
      finally { busy.current = false; }
    }
    kick.current = () => { void sync(); };
    const loop = () => { timer = setTimeout(async () => { await sync(); if (!stopped) loop(); }, EVERY_MS); };
    void sync();
    loop();
    const onLink = () => { void sync(); };
    window.addEventListener(LINK_EVENT, onLink);
    document.addEventListener('visibilitychange', onLink);
    return () => { stopped = true; if (timer) clearTimeout(timer); window.removeEventListener(LINK_EVENT, onLink); document.removeEventListener('visibilitychange', onLink); };
  }, [ready, change]);

  // Push soon after a local care change while paired (debounced).
  useEffect(() => {
    if (!ready || !session?.beast) return;
    if (!readLink()) return;
    const t = setTimeout(() => kick.current(), 3000);
    return () => clearTimeout(t);
  }, [ready, session?.beast?.xp, session?.beast?.bond, session?.beast?.displayName, session?.beast?.seed]);

  return null;
}
