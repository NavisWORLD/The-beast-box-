'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const source=fs.readFileSync('apps/beastbox-cloud/tests/zeref-native-committed-movement-009.cjs','utf8');
const workflow=fs.readFileSync('.github/workflows/zeref-native-save-menu-009.yml','utf8');
test('native Game Boy START mapping is exact and neutral menu save is distinct from model actions',()=>{
 assert.match(source,/const INPUT=\{UP:4,DOWN:5,LEFT:6,RIGHT:7,A:8,B:0,START:3\}/);
 assert.match(source,/const nativeSaveMenuKeys=\['START','RIGHT','UP','A','DOWN','DOWN','DOWN','A','A','A'\]/);
 assert.match(source,/original_native_save_menu_acks:saveMenuAcks/);
 assert.ok(source.includes('content_v11_menus.h::v11_update_pause'),'V11 save route must be documented in native runner');
 assert.match(source,/failed real browser recording 38157714812/);
 assert.match(source,/await input\('B'\);await input\('B'\)/);
 assert.match(source,/neutral_ui_commands_not_part_of_model_or_script_policy:true/);
 assert.doesNotMatch(source,/gameManager\.(?:setSaveFile|writeMemory)\(/);
});
test('one-episode WAIT and RIGHT smoke MUST verify checksum-valid saved movement BEFORE full experiment',()=>{
 assert.match(source,/ZEREF_009_SAVE_SMOKE/);
 assert.match(source,/Math\.abs\(committedAfterNativeMenu\.committed_location\.x-firstSavedProgress\.committed_location\.x\)/);
 assert.match(source,/w\.real_saved_coordinate_manhattan_pixels,0/);
 assert.match(source,/r\.real_saved_coordinate_manhattan_pixels>0/);
 const sm=workflow.indexOf('ZEREF_009_SAVE_SMOKE=1');
 const full=workflow.indexOf('NODE_PATH=/tmp/zeref-009-browser/node_modules node',sm+1);
 assert.ok(sm>0&&full>sm,'Actual smoke must precede full controller benchmark');
});
test('the experiment does not create fresh quantum jobs or promote candidate weights',()=>{
 assert.match(workflow,/38129248023/);
 assert.match(source,/game_objective_outperformance_proven:false/);
 assert.match(source,/no_live_production_model_promotion:true/);
 assert.match(source,/new_ibm_hardware_jobs_in_this_run:0/);
 assert.doesNotMatch(workflow,/secrets\.IBM|SamplerV2|qiskit/);
});
