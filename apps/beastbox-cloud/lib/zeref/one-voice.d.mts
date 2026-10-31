export const ONE_VOICE_SCHEMA:string;export const ONE_VOICE_RULE:string;
export function keeperLine(prompt:string):string;export function draftScore(reply:string,prompt:string):number;
export function chooseOneVoice(prompt:string,gated:{reply:string}|null,growing:{reply:string}|null):{reply:string|null;chosen:'gated'|'growing'|null;scores:{gated:number|null;growing:number|null}};
