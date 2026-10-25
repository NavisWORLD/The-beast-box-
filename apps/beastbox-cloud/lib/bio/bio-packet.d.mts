import type {PpgResult} from './ppg.mjs';
export const BIO_SCHEMA:string;export const BIO_SOURCE:string;export const BIO_HONESTY:string;export const BIO_VECTOR_CHANNELS:readonly string[];
export type BioPacket={schema:string;source:string;heartbeat_label:'MEASURED';honesty:string;pulse:{bpm:number;hrv_rmssd_ms:number|null;sqi:number;beats:number;duration_s:number;fs_hz:number};light:{red_mean:number;green_mean:number;blue_mean:number;red_ac_dc:number};audio:{enabled:boolean;rms_mean:number;zcr:number;centroid_norm:number};bio_vector_12:number[];raw_audio_published:false;raw_video_published:false;raw_frames_in_packet:false;packet_sha256:string};
export function canonical(v:unknown):string;
export function validateBioPacket(p:unknown):{ok:boolean;errors:string[]};
export function buildBioPacket(i:{ppg:PpgResult;light:{red_mean:number;green_mean:number;blue_mean:number;red_ac_dc:number};audio?:{enabled:boolean;rms_mean:number;zcr:number;centroid_norm:number}|null},sha256Hex:(s:string)=>string|Promise<string>):Promise<BioPacket>;
export function packetHash(p:BioPacket,sha256Hex:(s:string)=>string|Promise<string>):Promise<string>;
export function existingBioInjection(p:BioPacket):{action:'preview';source:'browser_sensor';consent:true;readings:Record<string,number>};
