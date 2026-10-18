/** 2D pixel companion for the sprite views: a tiny outline-only ("wireframe") pixel critter themed to its creature. */
import {companionTheme} from './companion-math.mjs';
// '#' = wire pixel (theme colour), '+' = accent/core pixel. Two frames: legs/wings/tentacles alternate.
export const PIXEL_SPRITES=Object.freeze({
 'cat-moth':[['#.......#','##.###.##','#.#+.+#.#','.#.....#.','..#####..','.#.....#.'],['.........','#..###..#','##+...+##','.#.....#.','..#####..','..#...#..']],
 'ice-spider':[['.........','#..###..#','.#.#+#.#.','#.##.##.#','.#.###.#.','#.......#'],['#.......#','.#.###.#.','#..#+#..#','.###.###.','#..###..#','.........']],
 'crystal-mite':[['....#....','...#+#...','..#...#..','.#.#.#.#.','#...#...#','.#.....#.'],['....#....','...#+#...','..#...#..','.#.#.#.#.','.#..#..#.','#.......#']],
 'scaled-jelly':[['..#####..','.#.#.#.#.','#..+.+..#','#########','.#.#.#.#.','#.#.#.#.#'],['..#####..','.#.#.#.#.','#..+.+..#','#########','#.#.#.#.#','.#.#.#.#.']],
 'star-beetle':[['...#.#...','..#####..','.#.+.+.#.','#.#####.#','.#.....#.','#.#...#.#'],['...#.#...','..#####..','.#.+.+.#.','.#######.','#.#...#.#','.#.....#.']],
 'horn-firefly':[['....#....','...#.#...','#.#+.+#.#','.#.###.#.','#..#.#..#','...#.#...'],['....#....','...#.#...','.##+.+##.','#..###..#','.#.#.#.#.','...#.#...']],
});
const hex=n=>'#'+n.toString(16).padStart(6,'0');
/** Draw onto a sprite canvas context; returns the pixel rect used (for tests). */
export function drawPixelCompanion(ctx,id,t,{w=288,h=288,px=4,glow=true}={}){
 const th=companionTheme(id);const frames=PIXEL_SPRITES[th.motif]||PIXEL_SPRITES['ice-spider'];const f=frames[Math.floor(t*4)%2];
 const ox=Math.round(w*.72+Math.sin(t*.9)*w*.12),oy=Math.round(h*.78+Math.sin(t*1.7)*4);
 ctx.save();if(glow){ctx.shadowColor=hex(th.color);ctx.shadowBlur=6;}
 for(let y=0;y<f.length;y++)for(let x=0;x<f[y].length;x++){const ch=f[y][x];if(ch==='.')continue;ctx.fillStyle=hex(ch==='+'?th.accent:th.color);ctx.fillRect(ox+x*px,oy+y*px,px,px);}
 ctx.restore();return {x:ox,y:oy,w:f[0].length*px,h:f.length*px,motif:th.motif};
}
