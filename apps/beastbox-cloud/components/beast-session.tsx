'use client';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { createTrail } from '../lib/companion/adventure.mjs';
import { openIndexedDb } from '../lib/companion/learn.mjs';
import { createSession, exportSession, importSession } from '../lib/companion/session.mjs';
import {replaySpark,readSparkSession} from '../public/spark/identity.mjs';
import {serializeQbeast} from '../public/spark/qbeast.mjs';
import {loadSparkRuns} from '../public/spark/runs.mjs';

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
      // The static generator writes the same local record; it is authoritative
      // over an older IndexedDB mirror after a full-page navigation.
      stored = readLocal() || stored;
      if (cancel) return;
      let next: any = importSession(stored);
      if(next.beast?.qbeast){
       try{next=readSparkSession(localStorage);const runs=await loadSparkRuns();const replay=replaySpark(serializeQbeast(next.beast.qbeast),new Map(runs.map(run=>[run.key,run])));next.beast.genome=replay.gen;next.beast.stage=next.beast.nativeStage||1;}
       catch{next=createSession();}
      }
      if(cancel)return;
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

  useEffect(()=>{
    const reload=()=>{try{const next=readSparkSession(localStorage);setSession(next);}catch{/* invalid local records remain available for recovery */}};
    const changed=(event:StorageEvent)=>{if(event.key===KEY)reload();};
    window.addEventListener('storage',changed);window.addEventListener('beastbox:spark-selected',reload);
    return()=>{window.removeEventListener('storage',changed);window.removeEventListener('beastbox:spark-selected',reload);};
  },[]);

  const value = useMemo(() => ({ ready, session, trail, sensorLog, change, setTrail, noteSensor }), [ready, session, trail, sensorLog, change, setTrail, noteSensor]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useBeastSession() {
  const value = useContext(Context);
  if (!value) throw new Error('Beast session is unavailable');
  return value;
}
