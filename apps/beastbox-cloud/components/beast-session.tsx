'use client';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { createTrail } from '../lib/companion/adventure.mjs';
import { openIndexedDb } from '../lib/companion/learn.mjs';
import { createSession, exportSession, importSession } from '../lib/companion/session.mjs';

const KEY = 'beastbox-companion-session-v1';

export type TrailPoint = { x: number; y: number };
export type Trail = { place: string; player: TrailPoint; beast: TrailPoint; facing: string; moving: boolean };

type Store = {
  ready: boolean;
  session: any;
  trail: Trail;
  sensorLog: string[];
  change: (mutate: (session: any) => void) => void;
  setTrail: (next: Trail) => void;
  noteSensor: (line: string) => void;
};

const Context = createContext<Store | null>(null);

function readLocal() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function BeastSessionProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [session, setSession] = useState<any>(null);
  const [trail, setTrailState] = useState<Trail>(createTrail());
  const [sensorLog, setSensorLog] = useState<string[]>([]);
  const db = useRef<Promise<{ get: (key: string) => Promise<unknown>; set: (key: string, value: unknown) => Promise<void> }> | null>(null);
  const extra = useRef({ trail: createTrail() as Trail, sensorLog: [] as string[] });

  const remember = useCallback((record: unknown) => {
    try { localStorage.setItem(KEY, JSON.stringify(record)); } catch { /* private browsing */ }
    const handle = db.current;
    if (handle) void handle.then((store) => store.set('session', record)).catch(() => undefined);
  }, []);

  useEffect(() => {
    let cancel = false;
    db.current = openIndexedDb().catch(() => null);
    void (async () => {
      let stored: Record<string, unknown> | null = null;
      try {
        const store = await db.current;
        const value = store ? await store.get('session') : null;
        if (value && typeof value === 'object') stored = value as Record<string, unknown>;
      } catch { /* IndexedDB unavailable */ }
      if (!stored) stored = readLocal();
      if (cancel) return;
      const next = importSession(stored);
      const place = typeof stored?.place === 'string' ? stored.place : 'grove';
      const restoredTrail = stored?.trail && typeof stored.trail === 'object' ? stored.trail as Trail : createTrail(place);
      const log = Array.isArray(stored?.sensorLog) ? stored.sensorLog.filter((line) => typeof line === 'string').slice(-8) : [];
      extra.current = { trail: restoredTrail, sensorLog: log };
      setSession(next);
      setTrailState(restoredTrail);
      setSensorLog(log);
      setReady(true);
    })();
    return () => { cancel = true; };
  }, []);

  const change = useCallback((mutate: (session: any) => void) => {
    setSession((current: any) => {
      const draft = importSession(exportSession(current || createSession()));
      mutate(draft);
      const record = { ...exportSession(draft), place: extra.current.trail.place, trail: extra.current.trail, sensorLog: extra.current.sensorLog };
      remember(record);
      return draft;
    });
  }, [remember]);

  const setTrail = useCallback((next: Trail) => {
    extra.current.trail = next;
    setTrailState(next);
    setSession((current: any) => {
      if (!current) return current;
      remember({ ...exportSession(current), place: next.place, trail: next, sensorLog: extra.current.sensorLog });
      return current;
    });
  }, [remember]);

  const noteSensor = useCallback((line: string) => {
    const text = line.trim().slice(0, 180);
    if (!text) return;
    const log = [...extra.current.sensorLog, text].slice(-8);
    extra.current.sensorLog = log;
    setSensorLog(log);
    setSession((sessionNow: any) => {
      if (sessionNow) remember({ ...exportSession(sessionNow), place: extra.current.trail.place, trail: extra.current.trail, sensorLog: log });
      return sessionNow;
    });
  }, [remember]);

  const value = useMemo(() => ({ ready, session, trail, sensorLog, change, setTrail, noteSensor }), [ready, session, trail, sensorLog, change, setTrail, noteSensor]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useBeastSession() {
  const value = useContext(Context);
  if (!value) throw new Error('Beast session is unavailable');
  return value;
}
