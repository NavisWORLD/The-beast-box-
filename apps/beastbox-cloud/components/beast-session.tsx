'use client';
import {createContext,useCallback,useContext,useEffect,useMemo,useRef,useState} from 'react';
import {createTrail} from '../lib/companion/adventure.mjs';
import {openIndexedDb} from '../lib/companion/learn.mjs';
import {advanceCreature,exportSession,importSession} from '../lib/companion/session.mjs';
import {selectedIdentity,updateDeviceSession,recoverMirroredSession} from '../lib/companion/session-store.mjs';
import {environmentFor} from '../lib/companion/behavior.mjs';
import {replaySpark,readSparkSession,withSparkLock,SESSION_KEY} from '../public/spark/identity.mjs';
import {serializeQbeast} from '../public/spark/qbeast.mjs';
import {loadSparkRuns} from '../public/spark/runs.mjs';
export type TrailPoint={x:number;y:number};
export type Trail={place:string;player:TrailPoint;beast:TrailPoint;facing:string;moving:boolean};
type ChangeResult={ok:boolean;reason?:string};
type Store={ready:boolean;session:any;trail:Trail;sensorLog:string[];storageStatus:string;change:(mutate:(session:any)=>void,options?:{allowUnsignedAdoption?:boolean})=>Promise<ChangeResult>;setTrail:(next:Trail)=>void;noteSensor:(line:string)=>void;};
const Context=createContext<Store|null>(null);
const readLocal=()=>{try{const raw=localStorage.getItem(SESSION_KEY);return raw?JSON.parse(raw):null;}catch{return null;}};
export function BeastSessionProvider({children}:{children:React.ReactNode}){
 const [ready,setReady]=useState(false),[session,setSession]=useState<any>(null),[trail,setTrailState]=useState<Trail>(createTrail()),[sensorLog,setSensorLog]=useState<string[]>([]),[storageStatus,setStorageStatus]=useState('Finding your device save…');
 const current=useRef<any>(null),alive=useRef(true),busy=useRef(0),queue=useRef<Promise<unknown>>(Promise.resolve());
 const extra=useRef({trail:createTrail() as Trail,sensorLog:[] as string[]});
 const environment=useRef(environmentFor());
 const db=useRef<Promise<any>|null>(null);
 const mirrorBusy=useRef(false),mirrorPending=useRef<any>(null);
 const publish=useCallback((next:any)=>{if(!alive.current)return;current.current=next;setSession(next);},[]);
 // Read the latest record inside the generator's cross-tab lock. No React updater writes.
 const change=useCallback((mutate:(session:any)=>void,options:{allowUnsignedAdoption?:boolean}={}):Promise<ChangeResult>=>{
  const expected=selectedIdentity(current.current);busy.current++;
  const task=queue.current.catch(()=>undefined).then(async():Promise<ChangeResult>=>{
   try{
    const next=await withSparkLock(()=>updateDeviceSession(localStorage,expected,mutate,{place:extra.current.trail.place,trail:extra.current.trail,sensorLog:extra.current.sensorLog},options));
    publish(next);if(alive.current)setStorageStatus('Saved on this device');
    // Coalesced recovery mirror. A hung IDB cannot stall confirmed care or ticks.
    mirrorPending.current={...exportSession(next),place:extra.current.trail.place,trail:extra.current.trail,sensorLog:extra.current.sensorLog};
    if(db.current&&!mirrorBusy.current){mirrorBusy.current=true;void(async()=>{try{const store=await db.current;while(store&&mirrorPending.current&&alive.current){const record=mirrorPending.current;mirrorPending.current=null;await store.set('session',record);}}catch{/* local save remains valid */}finally{mirrorBusy.current=false;}})();}
    return {ok:true};
   }catch(error){const reason=error instanceof Error?error.message:'The device save could not be written.';if(alive.current)setStorageStatus(reason);return {ok:false,reason};}
   finally{busy.current--;}
  });
  queue.current=task;return task;
 },[publish]);
 useEffect(()=>{
  alive.current=true;let cancelled=false;db.current=openIndexedDb().catch(()=>null);
  void(async()=>{
   let stored:any=readLocal(),recovering=false;
   try{recovering=!stored&&localStorage.getItem(SESSION_KEY)===null;}catch{publish(null);setStorageStatus('Device storage is unavailable. Keep a downloaded Beast file.');setReady(true);return;}
   if(!stored)try{stored=await Promise.race([(async()=>{const store=await db.current;return store?await store.get('session'):null;})(),new Promise(resolve=>setTimeout(()=>resolve(null),600))]);}catch{}
   let next:any=importSession(stored);
   try{
    if(next.beast?.qbeast){
     const runs=await loadSparkRuns({includeQvm:true});if(cancelled)return;
     // Archive loading is asynchronous: re-read instead of resurrecting stale state.
     next=await withSparkLock(()=>recovering?recoverMirroredSession(localStorage,stored,new Map(runs.map((run:any)=>[run.key,run]))):readSparkSession(localStorage));
     if(next.beast?.qbeast){const replay=replaySpark(serializeQbeast(next.beast.qbeast),new Map(runs.map((run:any)=>[run.key,run])));next.beast.genome=replay.gen;next.beast.stage=next.beast.nativeStage||1;}
    }
    if(cancelled)return;
    if(recovering&&next.beast&&!next.beast.qbeast)next=await withSparkLock(()=>recoverMirroredSession(localStorage,stored,new Map()));
    const restored=stored?.trail&&typeof stored.trail==='object'?stored.trail:createTrail(typeof stored?.place==='string'?stored.place:'grove');
    const log=Array.isArray(stored?.sensorLog)?stored.sensorLog.filter((x:unknown)=>typeof x==='string').slice(-8):[];
    extra.current={trail:restored,sensorLog:log};environment.current=environmentFor({place:restored.place});setTrailState(restored);setSensorLog(log);publish(next);setStorageStatus(next.beast?'Saved on this device':'Meet a Beast to begin');
   }catch(error){publish(null);setStorageStatus(error instanceof Error?error.message:'The saved Beast could not be verified. Its file was retained.');}
   if(!cancelled)setReady(true);
  })();
  return()=>{cancelled=true;alive.current=false;};
 },[publish]);
 const setTrail=useCallback((next:Trail)=>{extra.current.trail=next;environment.current=environmentFor({...environment.current,place:next.place});setTrailState(next);},[]);
 const noteSensor=useCallback((line:string)=>{const text=line.trim().slice(0,180);if(!text)return;const log=[...extra.current.sensorLog,text].slice(-8);extra.current.sensorLog=log;setSensorLog(log);},[]);
 // Coalesce frequent trail changes; never rewrite a stale session with metadata.
 useEffect(()=>{if(!ready||!current.current)return;const timer=setTimeout(()=>{void change(()=>undefined);},900);return()=>clearTimeout(timer);},[trail,sensorLog,ready,change]);
 useEffect(()=>{
  const reload=()=>{try{publish(readSparkSession(localStorage));setStorageStatus('Saved on this device');}catch(error){setStorageStatus(error instanceof Error?error.message:'The changed save could not be verified.');}};
  const changed=(event:StorageEvent)=>{if(event.key===SESSION_KEY)reload();};
  const stimulus=(event:Event)=>{environment.current=environmentFor((event as CustomEvent).detail||{});};
  window.addEventListener('storage',changed);window.addEventListener('beastbox:spark-selected',reload);window.addEventListener('beastbox:environment',stimulus);
  return()=>{window.removeEventListener('storage',changed);window.removeEventListener('beastbox:spark-selected',reload);window.removeEventListener('beastbox:environment',stimulus);};
 },[publish]);
 useEffect(()=>{
  if(!ready)return;
  // Fixed simulation tick, independent of display FPS. Hidden time invents no experiences.
  const timer=setInterval(()=>{if(document.hidden||busy.current||!current.current?.beast?.seed)return;try{if(localStorage.getItem('beastbox-behavior-paused-v1')==='true')return;}catch{return;}void change(draft=>{if(!document.hidden&&localStorage.getItem('beastbox-behavior-paused-v1')!=='true')advanceCreature(draft,environment.current);});},8000);
  return()=>clearInterval(timer);
 },[ready,change]);
 const value=useMemo(()=>({ready,session,trail,sensorLog,storageStatus,change,setTrail,noteSensor}),[ready,session,trail,sensorLog,storageStatus,change,setTrail,noteSensor]);
 return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useBeastSession(){const value=useContext(Context);if(!value)throw Error('Beast session is unavailable');return value;}
