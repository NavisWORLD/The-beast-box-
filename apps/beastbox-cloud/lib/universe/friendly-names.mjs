/** Friendly names for the raw ids the universe uses (star-1, star-1-p1). The ids stay in the data; only the words shown to players change.
 * Pure: no clock, no random. */
const num=s=>{const m=String(s||'').match(/(\d+)$/);return m?m[1]:null;};
/** star-1 -> "Star 1". Unknown shapes fall back to a plain word, never the raw id. */
export function starName(id){const m=String(id||'').match(/^star-(\d+)$/);return m?'Star '+m[1]:'a star';}
/** star-1-p2 -> "Planet 2 of Star 1"; the home planet reads "your home world", the hearth "Hearth". */
export function planetName(id,{home=null,hearth=null}={}){
 if(id&&id===hearth)return 'Hearth';
 if(id&&id===home)return 'your home world';
 const m=String(id||'').match(/^star-(\d+)-p(\d+)$/);return m?'Planet '+m[2]+' of Star '+m[1]:'a planet';}
/** Age is a count of simulation steps; players read it as "moments". */
export const ageWords=n=>'age '+(Number.isFinite(Number(n))?Number(n):0)+' moments';
export {num as _tail};
