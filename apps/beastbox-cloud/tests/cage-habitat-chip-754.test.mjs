import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const css=readFileSync(new URL('../app/globals.css',import.meta.url),'utf8');
test('#754 Habitat chip sits inside the round cage mask (every corner within radius .5)',()=>{
 const m=css.match(/\.cage-habitat-visual \[data-world-menu=cage\]\{top:(\d+)%;right:(\d+)%\}/);assert.ok(m);
 const top=+m[1]/100,right=+m[2]/100;
 for(const [boxW,boxH] of [[612,601],[350,339],[800,800]]){const w=99/boxW,h=44/boxH;const x1=1-right,x0=x1-w,y0=top,y1=top+h;
  for(const [x,y] of [[x0,y0],[x1,y0],[x0,y1],[x1,y1]])assert.ok(Math.hypot(x-.5,y-.5)<.5,`corner ${x.toFixed(2)},${y.toFixed(2)} outside at ${boxW}`);}});
