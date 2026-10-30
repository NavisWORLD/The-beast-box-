export const LOOP_STATUS_SCHEMA:string;
export const STATUS_WORDS:Readonly<Record<string,string>>;
export const LINKS:ReadonlyArray<{id:string;from:string;to:string;status:string;label:string;code:{path:string;has:string}[];tests:string[];note?:string}>;
export function loopStatus():{schema:string;honesty:string;links:{id:string;from:string;to:string;status:string;status_text:string;label:string;code:string[];tests:string[];note:string|null}[];counts:Record<string,number>};
