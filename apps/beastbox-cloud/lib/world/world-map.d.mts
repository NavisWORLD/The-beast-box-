export type Piece={key:string;name:string;short:string;icon:string;href:string;role:string;neighbors:string[]};
export const PIECES:readonly Piece[];
export function pieceForPath(path:string|null|undefined):{piece:Piece;sub:string|null}|null;
export function pieceIndex(key:string):number;
export function neighborsOf(key:string):Piece[];
export function journeyStep(key:string,dir:number):Piece|null;
export function worldHere(path:string|null|undefined):{piece:Piece;sub:string|null;index:number;total:number;prev:Piece|null;next:Piece|null;neighbors:Piece[]}|null;
export const WORLD_LABELS:{title:string;line:string;honesty:string};
