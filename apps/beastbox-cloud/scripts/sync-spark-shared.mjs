// Publish the existing browser-only care rules for the existing static Spark page.
// These are byte-for-byte copies, never a second implementation.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
for(const name of ['session','learn','adventure','beast-audio','beast-audio-engine','behavior','recorded-qvm-stimulus','qpack/canon','qpack/sha']){
 const src=new URL(`../lib/companion/${name}.mjs`,import.meta.url);
 const dest=new URL(`../public/spark/shared/${name}.mjs`,import.meta.url);
 mkdirSync(new URL('.',dest),{recursive:true});
 writeFileSync(dest,readFileSync(src));
}
