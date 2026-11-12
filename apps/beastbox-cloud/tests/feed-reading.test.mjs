import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildFeedIndex,matchFeed,composeFeedBlock,feedReadingEnabled,loadFeedIndex,_resetFeedCache,FEED_INDEX_URL,FEED_LABEL} from '../lib/cosmos/feed-reading.mjs';
import {assembleBridgeContext,BRIDGE_CONTEXT_CAPS} from '../lib/cosmos/live-context.mjs';

const raw={schema:'navisworld-zeref-reading-index/v1',label:'READ, NOT TRAINED (approved feed)',
 docs:[{id:'9-abc',title:"Alice's Adventures in Wonderland",source_url:'https://www.gutenberg.org/ebooks/11',license:'Public domain',sha256:'a'.repeat(64)}],
 chunks:[
  {doc:0,n:0,text:'Alice was beginning to get very tired of sitting by her sister on the bank, and of having nothing to do.'},
  {doc:0,n:1,text:'The Cheshire Cat only grinned when it saw Alice. It looked good-natured, she thought, but it had very long claws and a great many teeth.'},
  {doc:0,n:2,text:'Down, down, down. Would the fall never come to an end? I wonder how many miles I have fallen by this time?'}]};

test('flag: default reads only for the Pages chat; all/off override', () => {
 assert.equal(feedReadingEnabled(undefined,true),true);
 assert.equal(feedReadingEnabled(undefined,false),false);
 assert.equal(feedReadingEnabled('pages',false),false);
 assert.equal(feedReadingEnabled('all',false),true);
 assert.equal(feedReadingEnabled('off',true),false);
 assert.equal(feedReadingEnabled('garbage',false),false);
});

test('malformed or foreign indexes read nothing', () => {
 assert.equal(buildFeedIndex(null),null);
 assert.equal(buildFeedIndex({...raw,schema:'other'}),null);
 const empty=buildFeedIndex({...raw,docs:[],chunks:[]});
 assert.equal(matchFeed(empty,'anything at all'),null);
});

test('BM25 retrieves the matching approved passage, deterministically; misses read nothing', () => {
 const f=buildFeedIndex(raw);
 const hit=matchFeed(f,'What did the Cheshire cat do when it saw Alice?');
 assert.ok(hit);
 assert.equal(hit.title,"Alice's Adventures in Wonderland");
 assert.match(hit.passage,/Cheshire Cat only grinned/);
 assert.deepEqual(matchFeed(buildFeedIndex(raw),'What did the Cheshire cat do when it saw Alice?'),hit);
 assert.equal(matchFeed(f,'quantum spaceship kubernetes'),null);
 assert.equal(matchFeed(f,''),null);
 assert.equal(matchFeed(f,'Hi Zeref, it is Phera. Can you hear me here?'),null);
 assert.equal(matchFeed(f,'I am tired'),null); // one shared word is not a reading match
});

test('a one-passage shelf (a single approved excerpt) still matches on real overlap', () => {
 const one=buildFeedIndex({...raw,chunks:[{doc:0,n:0,text:'So she was considering in her own mind whether the pleasure of making a daisy-chain would be worth the trouble, when suddenly a White Rabbit with pink eyes ran close by her.'}]});
 assert.ok(matchFeed(one,'Have you ever seen a white rabbit with pink eyes?'));
 assert.equal(matchFeed(one,'What is your favourite colour?'),null);
});

test('the block fits the library byte cap and the excerpt is exactly what was composed', () => {
 const hit=matchFeed(buildFeedIndex(raw),'Cheshire cat with long claws and teeth');
 const b=composeFeedBlock(hit,BRIDGE_CONTEXT_CAPS.library);
 assert.ok(Buffer.byteLength(b.text,'utf8')<=BRIDGE_CONTEXT_CAPS.library);
 assert.ok(b.text.includes(FEED_LABEL) && b.text.endsWith(b.excerpt));
 assert.deepEqual(composeFeedBlock(hit,80),{text:'',excerpt:''});
});

test('assembly: a book fills the library field only on a shelf miss, with a read_from receipt', () => {
 const hit=matchFeed(buildFeedIndex(raw),'the Cheshire cat saw Alice');
 const a=assembleBridgeContext({continuity:'',world:null,shelfHits:[],feedHit:hit});
 assert.ok(a.context.library.startsWith('From an approved book you are reading (READ, NOT TRAINED)'));
 assert.equal(a.read_from.label,'READ, NOT TRAINED');
 assert.equal(a.read_from.title,hit.title);
 assert.ok(a.context.library.endsWith(a.read_from.excerpt));
 assert.equal(a.library.composed,false); // his shelves did not compose
 assert.ok(Object.keys(a.context).every(k=>['continuity','universe','library','sight','memory'].includes(k)));
 const shelf=[{shelf:'zeref-lessons-006',topic:'cats',user:'cats?',assistant:'Cats are soft and I like them very much, they purr and sleep in the sun all afternoon.',source:'x',license:null,score:3}];
 const b=assembleBridgeContext({continuity:'',world:null,shelfHits:shelf,feedHit:hit});
 assert.equal(b.read_from,null);
 assert.ok(b.context.library.startsWith('From your library'));
 const c=assembleBridgeContext({continuity:'',world:null,shelfHits:[]});
 assert.equal(c.read_from,null);
 assert.equal(c.context.library,undefined);
});

test('loader: fixed URL, failures and oversize read nothing', async () => {
 assert.equal(FEED_INDEX_URL,'https://raw.githubusercontent.com/NavisWORLD/NavisWORLD/main/zeref/feed/index/index.json');
 _resetFeedCache();
 assert.equal(await loadFeedIndex(0,async()=>({ok:false})),null);
 _resetFeedCache();
 assert.equal(await loadFeedIndex(0,async()=>{throw new Error('net');}),null);
 _resetFeedCache();
 assert.equal(await loadFeedIndex(0,async()=>({ok:true,headers:{get:()=>String(30_000_000)},text:async()=>'{}'})),null);
 _resetFeedCache();
 let urls=[];
 const f=await loadFeedIndex(0,async(u)=>{urls.push(u);return {ok:true,headers:{get:()=>null},text:async()=>JSON.stringify(raw)};});
 assert.deepEqual(urls,[FEED_INDEX_URL]);
 assert.ok(matchFeed(f,'the Cheshire cat saw Alice'));
 _resetFeedCache();
});

test('route wiring: flag-gated, shelf first, read_from only when context was sent; nothing writes or trains', () => {
 const src=readFileSync(new URL('../app/api/guest/forever/route.ts',import.meta.url),'utf8');
 assert.match(src,/feedReadingEnabled\(process\.env\.BEASTBOX_FEED_READING,allowedCrossOrigin\)/);
 assert.match(src,/const feedHit=!shelfHits\.length&&/);
 assert.match(src,/const readFrom=contextSent\?bridgeContext\.read_from:null;/);
 assert.match(src,/training_eligible:false/);
 const mod=readFileSync(new URL('../lib/cosmos/feed-reading.mjs',import.meta.url),'utf8');
 assert.doesNotMatch(mod,/writeFile|appendFile|Math\.random|embedding\(|method:\s*'POST'/);
});
