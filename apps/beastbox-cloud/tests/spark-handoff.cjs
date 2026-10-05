/* Actual cross-origin parent handoff and vendored native core; no owner/model calls. */
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs/promises');
const root=process.argv[2]||'http://127.0.0.1:3000',out=process.argv[3]||'/tmp/sol-handoff',localGame=process.argv[4];
(async()=>{
 await fs.mkdir(out,{recursive:true});const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true}),page=await context.newPage(),errors=[],wrong=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/SIM_EARTH|Pocket.Reality|standalone\//i.test(r.url()))wrong.push(r.url())});
 if(localGame)await context.route('https://navisworld.github.io/**',async route=>{
  const url=new URL(route.request().url()),prefix='/Cosmic-synapse-the-living-universe-sim-engine-';
  assert.ok(url.pathname.startsWith(prefix));const response=await route.fetch({url:localGame+url.pathname.slice(prefix.length)+url.search});await route.fulfill({response});
 });
 try{
  await page.goto(root+'/spark/index.html');await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId);
  await page.locator('#generate').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Spawned'));
  const snapshot=await page.evaluate(()=>JSON.parse(JSON.parse(localStorage.getItem('beastbox-quantum-beast-public-v1')).text));
  await page.locator('#lost-cosmos').click();const player=page.locator('main [data-spark-player]');await player.getByRole('button',{name:'SEND BEAST & PLAY 🎮',exact:true}).click();
  await player.getByRole('status').filter({hasText:'same QBEAST verified'}).waitFor({timeout:60000});
  const gate=player.frameLocator('iframe'),hand=gate.frameLocator('#handheld');await hand.locator('#status').filter({hasText:'cartridge mailbox'}).waitFor();
  await hand.locator('#consent').check();await hand.locator('#play').click();await hand.getByText(/^start game$/i).click({timeout:60000});
  await hand.locator('#status').filter({hasText:/Cartridge running|Journey restored/}).waitFor({timeout:90000});
  const core=page.frames().find(f=>f.url().includes('/sol-spark-gate/handheld.html'));assert.ok(core);
  const verified=await core.evaluate(async snapshot=>{
   const {importPayload}=await import('../spark-beasts/trade.mjs');
   const record=await importPayload(new TextEncoder().encode(JSON.stringify(snapshot))),gm=EJS_emulator.gameManager,save=gm.getSaveFile(false),dv=new DataView(save.buffer,save.byteOffset,save.byteLength);
   return {id:record.publicId,seed:record.profile.gameSeed,nativeId:dv.getUint32(24712,true),nativeSeed:dv.getUint32(24716,true),bytes:save.length,art:String.fromCharCode(...save.subarray(24704,24708))};
  },snapshot);
  assert.equal(verified.id,verified.nativeId);assert.equal(verified.seed,verified.nativeSeed);assert.equal(verified.art,'SPK1');assert.equal(verified.bytes,32768);
  await hand.locator('#game canvas').first().screenshot({path:out+'/native-public-title.png'});
  assert.deepEqual(wrong,[]);assert.deepEqual(errors,[]);await fs.writeFile(out+'/report.json',JSON.stringify({passed:true,qbeast:snapshot.profile.id,seed:snapshot.profile.seed,verified,realNativeCore:true,noSimEarth:true,consoleErrors:errors},null,2));console.log('PASS: public Spark → shared identity → actual current GBA core, same art and BCP1');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
