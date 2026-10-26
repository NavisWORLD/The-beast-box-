// Tiny client-side hub so the consent panel and the pocket share the SAME numbers. Pure state: no storage, network or sensors.
// consent is false until the person grants it; revoke() drops the numbers at once.
let state={consent:false,numbers:null,measuredAtMs:0,version:0,pulseReading:false};
const subs=new Set();
const emit=()=>{state={...state,version:state.version+1};subs.forEach(f=>{try{f(state);}catch{}});};
export const getEnvironment=()=>state;
export const subscribeEnvironment=f=>{subs.add(f);return()=>subs.delete(f);};
export function grantEnvironment(){if(!state.consent){state={...state,consent:true};emit();}}
export function setEnvironmentNumbers(numbers,nowMs){if(!state.consent)return;state={...state,numbers,measuredAtMs:nowMs};emit();}
export function revokeEnvironmentLocal(){state={consent:false,numbers:null,measuredAtMs:0,version:state.version,pulseReading:state.pulseReading};emit();}
/** The camera does one job at a time. The fingertip-pulse flow says so explicitly: pulse_read_started / pulse_read_ended. While a pulse is being read, light waits. */
export function signalPulse(kind){if(kind==='pulse_read_started'&&!state.pulseReading){state={...state,pulseReading:true};emit();}else if(kind==='pulse_read_ended'&&state.pulseReading){state={...state,pulseReading:false};emit();}}
export const isPulseReading=()=>state.pulseReading;
/** The heartbeat is a one-shot reading from the IBM BIO flow; it is merged into the next sample only when consent is on. */
let heart=null;
export const setHeartNumbers=h=>{heart=h&&Number.isFinite(h.bpm)&&Number.isFinite(h.sqi)&&h.sqi>=0.6?{bpm:h.bpm,sqi:h.sqi,atMs:h.atMs}:null;};
export const getHeartNumbers=(nowMs,maxAgeMs=600000)=>heart&&nowMs-heart.atMs<=maxAgeMs?heart:null;
