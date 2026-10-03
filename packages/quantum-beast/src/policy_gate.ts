import {exactKeys,requireCondition,type EventKind} from './verifier';
export type HostGrant={allow?:EventKind[];public_memory?:boolean};
/** Host-selected permission only; never exposed as an agent tool. */
export function checkHostPermission(grant:unknown,kind:EventKind):void{
 exactKeys(grant,[],['allow','public_memory']);
 requireCondition(Array.isArray(grant.allow)&&grant.allow.length<=3&&grant.allow.every(x=>['message','action','memory'].includes(x))&&new Set(grant.allow).size===grant.allow.length,'Malformed host permission allowlist');
 requireCondition(grant.public_memory===true&&grant.allow.includes(kind),'Host did not approve this public outcome');
}
