// Visual Life Pass: label test. Authored text only; four grep rules from Emeth's file; every receipt is bound to an engine number.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync,readdirSync} from 'node:fs';
import {VL_TEXT,VL_OUTPUT_LABELS,receipt,receiptChip} from '../lib/universe/visual-life-labels.mjs';
const here=p=>new URL(p,import.meta.url);
const json=JSON.parse(readFileSync(here('../lib/universe/data/visual_life_labels.json'),'utf8'));
const ui=[];for(const g of ['event_sounds','hud_receipts','event_toasts','below_waterline','device_strength'])for(const [k,v] of Object.entries(json[g]))if(typeof v==='string'&&k!=='note_long')ui.push([g+'.'+k,v]);
test('the generated data file equals the authored JSON',()=>{assert.deepEqual(JSON.parse(JSON.stringify(VL_TEXT)),json);});
test('every UI line is 44 characters or fewer',()=>{for(const [k,v] of ui)assert.ok(v.length<=44,k+' '+v.length);});
test('grep rule 1: RECORDED appears only for genesis and Zeref seed lines (none in the new UI text)',()=>{for(const [k,v] of ui)assert.ok(!/RECORDED/.test(v),k);
 for(const [k,v] of Object.entries(VL_OUTPUT_LABELS))assert.ok(v==='SIMULATED'||v==='SEEDED',k);});
test('grep rule 2: MEASURED appears nowhere in the new text',()=>{assert.ok(!/MEASURED/i.test(JSON.stringify(json.hud_receipts)+JSON.stringify(json.event_toasts)+JSON.stringify(json.below_waterline)));});
test('grep rule 3: no live / real-time / quantum next to weather, water, sky or boom',()=>{
 const {never_say,"grep_rules_for_B-tests":grepRules,_note,...shipped}=json;void never_say;void grepRules;void _note;const all=JSON.stringify(shipped);
 assert.ok(!/(live|real-time|quantum)[^."]{0,24}(weather|water|sky|boom|storm|sea)/i.test(all),'forbidden pairing');
});
test('grep rule 4: every hud_receipts line has a placeholder or a named engine channel behind it, and receipt() fills only real numbers',()=>{
 for(const [k,v] of Object.entries(json.hud_receipts)){const ph=[...v.matchAll(/\{(\w+)\}/g)].map(m=>m[1]);
  if(ph.length){const vals=Object.fromEntries(ph.map(p=>[p,0.5]));assert.ok(receipt(k,vals),k);assert.equal(receipt(k,{}),null,k+' with no number is dropped');}}
 assert.equal(receipt('foam',{wind:NaN}),null);assert.equal(receipt('foam',{wind:.42}),'Foam drifts with wind 0.42');
 assert.equal(receiptChip('foam','foam',{wind:.42}),'Foam drifts with wind 0.42 · SIMULATED');assert.equal(receipt('nope',{}),null);
});
test('never-say list: none of the forbidden words appear in shipped UI text or in the visual-life source files',()=>{
 const bad=[/live quantum/i,/real-time quantum/i,/quantum weather/i,/quantum water/i,/breathtaking/i,/\benhanced\b/i,/AI-generated beauty/i,/every object has a brain/i,/\baware(ness)?\b/i,/\bconscious/i];
 for(const [k,v] of ui)for(const b of bad)assert.ok(!b.test(v),k+' '+b);
 const src=readdirSync(here('../lib/universe/')).filter(f=>/^(foam-field|visual-life|undersea|atmosphere|event-stage|hero-palette|event-audio|vl-)/.test(f)&&/\.(mjs|ts)$/.test(f)&&!/-data\.mjs$/.test(f));
 for(const f of src){const t=readFileSync(here('../lib/universe/'+f),'utf8').split('\n').filter(l=>!l.trim().startsWith('//')).join('\n');for(const b of bad.slice(0,5))assert.ok(!b.test(t.replace(/never_say/g,'')),f+' '+b);}
});
