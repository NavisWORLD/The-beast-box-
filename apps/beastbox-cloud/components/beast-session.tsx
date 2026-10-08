'use client';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { createTrail } from '../lib/companion/adventure.mjs';
import { openIndexedDb } from '../lib/companion/learn.mjs';
import { createSession, exportSession, importSession, advanceCreature } from '../lib/companion/session.mjs';
import {replaySpark,readSparkSession,withSparkLock} from '../public/spark/identity.mjs';
import {selectedIdentity,updateDeviceSession} from '../lib/companion/session-store.mjs';
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
  storageStatus: string;
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
  const latest = useRef<any>(null);
  const writes = useRef<Promise<unknown>>(Promise.resolve());
  const [storageStatus,setStorageStatus] = useState('Checking local save…');
  const db = useRef<Promise<{ get: (key: string) => Promise<unknown>; set: (key: string, value: unknown) => Promise<void> }> | null>(null);
  const extra = useRef({ trail: createTrail() as Trail, sensorLog: [] as string[] });


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
      latest.current=next;
      setSession(next);
      setStorageStatus(next.beast?'Saved on this device':'Meet a Beast to begin');
      setTrailState(restoredTrail);
      setSensorLog(log);
      setReady(true);
    })();
    return () => { cancel = true; };
  }, []);

  // Every care, model, native-game and behavior mutation starts from the latest saved
  // snapshot under the generator's existing cross-tab Web Lock. Never save a stale React state.
  const change = useCallback((mutate: (session: any) => void) => {
    const expected = selectedIdentity(latest.current);
    writes.current = writes.current.catch(() => undefined).then(async () => {
      const next = await withSparkLock(() => updateDeviceSession(localStorage, expected, mutate, {
        place:extra.current.trail.place,trail:extra.current.trail,sensorLog:extra.current.sensorLog
      }));
      latest.current = next;
      setSession(next);
      setStorageStatus('Saved on this device');
      // IndexedDB is an ordered recovery mirror. LocalStorage remains authoritative.
      try {
        const store = await db.current;
        if (store) await store.set('session', {
          ...exportSession(next),place:extra.current.trail.place,
          trail:extra.current.trail,sensorLog:extra.current.sensorLog
        });
      } catch { /* device-local authoritative write already succeeded */ }
    }).catch((error) => {
      setStorageStatus(error instanceof Error ? error.message : 'The Beast could not be saved on this device.');
    });
  }, []);

  const setTrail = useCallback((next: Trail) => {
    extra.current.trail=next;
    setTrailState(next);
  }, []);

  const noteSensor = useCallback((line: string) => {
    const text=line.trim().slice(0,180);
    if(!text)return;
    const log=[...extra.current.sensorLog,text].slice(-8);
    extra.current.sensorLog=log;
    setSensorLog(log);
  }, []);

  // Store small UI metadata after movement settles. This can never overwrite care or a
  // game return because its write re-reads the current selected Beast within the same lock.
  useEffect(() => {
    if(!ready || !latest.current?.beast)return;
    const timer=setTimeout(() => change(() => undefined),900);
    return () => clearTimeout(timer);
  }, [trail,sensorLog,ready,change]);

  useEffect(()=>{
    const reload=()=>{try{const next=readSparkSession(localStorage);latest.current=next;setSession(next);setStorageStatus('Saved on this device');}catch{/* invalid local records remain available for recovery */}};
    const changed=(event:StorageEvent)=>{if(event.key===KEY)reload();};
    window.addEventListener('storage',changed);window.addEventListener('beastbox:spark-selected',reload);
    return()=>{window.removeEventListener('storage',changed);window.removeEventListener('beastbox:spark-selected',reload);};
  },[]);

  // Bounded simulation at 8s; no background catch-up, no rendering loop.
  const activeQbeastId=session?.beast?.qbeast?.profile?.id;
  useEffect(() => {
    if(!ready||!activeQbeastId)return;
    const timer=window.setInterval(() => {
      if(document.hidden)return;
      change((draft:any) => {
        if(draft.beast?.qbeast?.profile?.id!==activeQbeastId)throw Error('The active Beast changed.');
        advanceCreature(draft,{place:extra.current.trail.place});
      });
    },8000);
    return()=>window.clearInterval(timer);
  },[ready,activeQbeastId,change]);

  const value = useMemo(() => ({ ready, session, trail, sensorLog, storageStatus, change, setTrail, noteSensor }), [ready, session, trail, sensorLog, storageStatus, change, setTrail, noteSensor]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useBeastSession() {
  const value = useContext(Context);
  if (!value) throw new Error('Beast session is unavailable');
  return value;
}
