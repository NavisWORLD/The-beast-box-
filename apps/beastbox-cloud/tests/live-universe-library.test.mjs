import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildWorldLive,WORLD_LIVE_LABELS} from '../lib/zeref/world-live.mjs';
import {assembleServedPreface,buildShelfIndex,composeLiveUniverseLines,composeShelfLines,
 loadShelfIndex,matchShelf,parseShelfDialogue} from '../lib/cosmos/live-context.mjs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const readRepo=p=>readFileSync(new URL('../../../'+p,import.meta.url),'utf8');

const NOW=Date.now();
const PIN={training_steps:33904,checkpoint_sha256:'f'.repeat(64)};
function worldFixture(){
 const sec=Math.floor(NOW/1000);
 return buildWorldLive({
  spark:{simulated:true,beast_id:'bb-deada969',tick:6772,at_epoch:sec,status:'ok',late:false,
   consecutive_failures:0,interval_target_s:60,counts_sha256:'a'.repeat(64),
   last_ok:{tick:6772,at_epoch:sec,counts:{'000':100,'111':156}}},
  liveTick:{schema:'beast-live-tick/v1',label:'SIMULATED',recorded_tick:245,seconds_since_recorded:12,xp_live:4239.5,signals:{}},
  liveHead:{at_ms:NOW},
  diary:{ok:true,tick:32,last_tick_at:new Date(NOW).toISOString()},
  pin:PIN,nowMs:NOW});
}

test('live universe lines: channel states with labels verbatim, nothing paraphrased',()=>{
 const out=composeLiveUniverseLines(worldFixture());
 assert.ok(out.includes(WORLD_LIVE_LABELS.spark),'spark label copied verbatim');
 assert.ok(out.includes(WORLD_LIVE_LABELS.liveTick),'liveTick label copied verbatim');
 assert.match(out,/spark link CONNECTED/);
 assert.match(out,/tick 6772/);
 assert.match(out,/live tick CONNECTED/);
 // a DOWN channel is stated as DOWN with its label; its numbers are not invented
 const down=composeLiveUniverseLines(buildWorldLive({spark:null,liveTick:null,liveHead:null,diary:null,pin:PIN,nowMs:NOW}));
 assert.match(down,/spark link DOWN/);
 assert.ok(down.includes(WORLD_LIVE_LABELS.spark));
 assert.doesNotMatch(down,/tick \d/,'no invented tick for a DOWN channel');
 // budget pressure never ships a truncated label: the block is whole or absent
 const tiny=composeLiveUniverseLines(worldFixture(),40);
 assert.ok(tiny===''||tiny.includes(WORLD_LIVE_LABELS.spark));
 assert.equal(composeLiveUniverseLines(null),'' );
});

test('library: a topic match composes the entry\'s own teaching, with its shelf id',()=>{
 const rows=parseShelfDialogue(readRepo('evidence/zeref-lessons-006/dialogue.jsonl'),'zeref-lessons-006');
 assert.ok(rows.length>=250,'the landed lessons shelf parses');
 const idx=buildShelfIndex(rows);
 const hits=matchShelf(idx,'what do your eyes measure');
 assert.equal(hits.length,1);
 assert.equal(hits[0].shelf,'zeref-lessons-006');
 assert.equal(hits[0].topic,'senses-light');
 const block=composeShelfLines(hits);
 assert.ok(block.includes('brightness'),'the entry\'s own teaching is composed');
 assert.ok(block.includes('zeref-lessons-006'),'the shelf id rides with it');
});

test('library: a miss composes nothing — never a fake book',()=>{
 const rows=parseShelfDialogue(readRepo('evidence/zeref-lessons-006/dialogue.jsonl'),'zeref-lessons-006');
 const idx=buildShelfIndex(rows);
 assert.deepEqual(matchShelf(idx,'zxqv jkwx qqqq'),[]);
 assert.deepEqual(matchShelf(idx,''),[]);
 assert.equal(composeShelfLines([]),'');
 assert.equal(composeShelfLines(matchShelf(idx,'zxqv jkwx qqqq')),'');
});

test('library: the loader reads the real approved shelves, read-only',async()=>{
 const idx=await loadShelfIndex();
 assert.ok(idx.rows>=2900,`approved shelves loaded (${idx.rows} rows)`);
 const hits=matchShelf(idx,'what is water made of');
 assert.equal(hits.length,1);
 assert.match(hits[0].shelf,/^zeref-knowledge-/);
 assert.match(hits[0].assistant,/Hydrogen and oxygen/);
});

test('library: parsing skips malformed lines instead of repairing them',()=>{
 const text=['{"user":"What is water made of?","assistant":"Hydrogen and oxygen.","topic":"science"}',
  'not json at all','{"user":"missing the teaching"}','', '{"user":"  ","assistant":"blank"}'].join('\n');
 const rows=parseShelfDialogue(text,'zeref-knowledge-002');
 assert.equal(rows.length,1);
 assert.equal(rows[0].topic,'science');
});

test('hostile input cannot reach a shelf writer — the module has none',()=>{
 const src=read('lib/cosmos/live-context.mjs');
 assert.doesNotMatch(src,/putBlob|appendExchange|appendGuestEvent|createWriteStream|writeFileSync/);
 assert.doesNotMatch(src,/method:\s*['"]POST/,'the only fetch is a GET of the shelf files');
 const rows=parseShelfDialogue(readRepo('evidence/zeref-lessons-006/dialogue.jsonl'),'zeref-lessons-006');
 const idx=buildShelfIndex(rows);
 for(const hostile of ['../../etc/passwd','<script>alert(1)</script>','\x00\x1f control chars','x'.repeat(5000),'"; DROP TABLE shelves; --'])
  assert.ok(Array.isArray(matchShelf(idx,hostile)),'hostile text is only ever a lookup key');
});

test('assembly: priority is continuity, then live universe, then library',()=>{
 const world=worldFixture();
 const shelfHits=[{shelf:'zeref-lessons-006',topic:'senses-light',user:'Zeref, what do your eyes measure?',
  assistant:'My eyes measure brightness and colour, and whether things are moving.',source:'zeref-lessons-006',license:null,score:9}];
 const continuity='CONTINUITY STATE LINE. '.repeat(8).trim(); // 183 chars
 const liveFull=composeLiveUniverseLines(world,360);
 const full=assembleServedPreface({continuity,recompose:n=>'C'.repeat(n),world,shelfHits,budget:1700});
 assert.ok(full.preface.includes('CONTINUITY STATE LINE'));
 assert.ok(full.preface.includes('spark link CONNECTED'));
 assert.ok(full.preface.includes('From your library'));
 assert.equal(full.live.composed,true);
 assert.equal(full.live.channels.spark.label,WORLD_LIVE_LABELS.spark);
 assert.equal(full.library.composed,true);
 assert.equal(full.library.matched,true);
 assert.deepEqual(full.library.shelf_ids,['zeref-lessons-006']);
 // tight budget: the library block is cut before the live universe block
 const tight=assembleServedPreface({continuity,recompose:n=>'C'.repeat(n),world,shelfHits,
  budget:continuity.length+1+liveFull.length});
 assert.equal(tight.library.composed,false);
 assert.equal(tight.live.composed,true);
 assert.ok(!tight.preface.includes('From your library'));
 assert.ok(tight.preface.includes('spark link CONNECTED'));
 // bare budget: continuity is re-rendered at the cap, both blocks gone
 const bare=assembleServedPreface({continuity,recompose:n=>'C'.repeat(n),world,shelfHits,budget:60});
 assert.equal(bare.preface,'C'.repeat(60));
 assert.equal(bare.live.composed,false);
 assert.equal(bare.library.composed,false);
 // no world at all: the receipt says unreachable instead of inventing channels
 const blind=assembleServedPreface({continuity,recompose:n=>'C'.repeat(n),world:null,shelfHits:[],budget:1700});
 assert.equal(blind.live.composed,false);
 assert.equal(blind.live.reason,'world-live unreachable');
});

test('forever door route: composes live universe + library, receipts state them, writes stay guestbook-only',()=>{
 const src=read('app/api/guest/forever/route.ts');
 assert.match(src,/live-context\.mjs/);
 assert.match(src,/assembleServedPreface/);
 assert.match(src,/loadShelfIndex/);
 assert.match(src,/matchShelf\(shelf,text\)/,'the lookup key is the visitor\'s own words');
 assert.match(src,/live_universe:served\.live/);
 assert.match(src,/library:served\.library/);
 assert.match(src,/appendExchange/,'the only writes remain the #668 guestbook writes');
 assert.doesNotMatch(src,/putBlob|storeLesson|stepDiary/);
});

test('the stateless door stays untouched by the live layer',()=>{
 const src=read('app/api/guest/route.ts');
 assert.match(src,/guest_stateless:true/);
 assert.doesNotMatch(src,/live-context|loadShelfIndex|assembleServedPreface|guestbook|forever-store/);
});
