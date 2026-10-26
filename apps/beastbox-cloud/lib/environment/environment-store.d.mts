import type {EnvNumbers} from './environment-link.mjs';
export type EnvState={consent:boolean;numbers:EnvNumbers|null;measuredAtMs:number;version:number;pulseReading:boolean};
export function getEnvironment():EnvState;export function subscribeEnvironment(f:(s:EnvState)=>void):()=>void;
export function grantEnvironment():void;export function setEnvironmentNumbers(n:EnvNumbers|null,nowMs:number):void;export function revokeEnvironmentLocal():void;
export function setHeartNumbers(h:{bpm:number;sqi:number;atMs:number}|null):void;export function getHeartNumbers(nowMs:number,maxAgeMs?:number):{bpm:number;sqi:number;atMs:number}|null;
export function signalPulse(kind:'pulse_read_started'|'pulse_read_ended'):void;export function isPulseReading():boolean;
