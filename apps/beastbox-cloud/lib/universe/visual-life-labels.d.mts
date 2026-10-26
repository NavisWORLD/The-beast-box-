export const VL_TEXT:any;
export const VL_OUTPUT_LABELS:Readonly<Record<string,string>>;
export function receipt(key:string,vals?:Record<string,number|string|null|undefined>):string|null;
export function receiptChip(key:string,out:string,vals?:Record<string,number|string|null|undefined>):string|null;
