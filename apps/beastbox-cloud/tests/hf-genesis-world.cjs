/* Actual guest UI plus explicit browser failure fixtures. No live inference/QPU. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs/promises');
const expect=require('playwright/test').expect.configure({timeout:25000});
const origin=process.argv[2]||'http://127.0.0.1:3000',out=process.argv[3]||'/tmp/hf-genesis-world';
const key='beastbox-companion-session-v1';
const get=page=>page.evaluate(k=>JSON.parse(localStorage.getItem(k)),key);
(async()=>{
 await fs.mkdir(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:process.env.BEAST_BROWSER_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,acceptDownloads:true});
 await context.addInitScript(()=>{
  const getContext=HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext=function(kind,...args){if(/^webgl/.test(kind))return null;return getContext.call(this,kind,...args);};
 });
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const results={renderer_fixture:'WebGL context creation returns null; real 2D remains',physical_iphone:'UNVERIFIED',tests:[]};
 try{
  await page.goto(origin+'/');
  await expect(page.getByRole('link',{name:/Meet My Beast/i}).first()).toBeVisible();
  await page.getByRole('link',{name:/Meet My Beast/i}).first().click();
  await expect(page.locator('#view')).toHaveAttribute('data-creature-id',/^.+$/);
  const original=await get(page),id=original.beast.qbeast.profile.id;
  await page.locator('#beast-name').fill('Juniper');await page.locator('#name-form button[type=submit]').click();
  await expect(page.locator('#status')).toContainText('Named Juniper');
  await page.goto(origin+'/beast-cage');
  const care=page.locator('[data-care-deck]');
  await expect(care.getByLabel('Beast name')).toBeEnabled();
  assert.equal((await get(page)).beast.displayName,'Juniper');
  await expect(page.getByRole('figure',{name:'Active Spark Beast companion',exact:true})).toHaveAttribute('data-creature-id',id);
  await expect(page.getByRole('figure',{name:'Active Spark Beast companion',exact:true})).toBeVisible();
  await care.getByRole('button',{name:'Pet',exact:true}).click();
  await expect(care.locator('[data-care-status]')).toContainText('Your bond grew');
  await care.getByRole('button',{name:'Feed',exact:true}).click();
  await expect(care.locator('[data-care-status]')).toContainText('little energy');
  await care.getByRole('button',{name:'Rest',exact:true}).click();
  await expect(care.locator('[data-care-status]')).toContainText('recover');
  for(let n=0;n<6;n++)await care.getByRole('button',{name:/^Train/}).click();
  await expect(care.locator('[data-care-status]')).toContainText('Training complete');
  assert.equal((await get(page)).train.rounds,1);
  await care.getByLabel('Tell your companion something').fill('grove explore');
  await care.getByRole('button',{name:'Learn this phrase'}).click();
  await expect(care.locator('[data-care-status]')).toContainText('kept the exchange');
  await page.getByRole('button',{name:'Offer a floating star toy'}).click();
  await page.waitForFunction(k=>JSON.parse(localStorage.getItem(k)).beast.behavior?.events?.at(-1)?.input.toy===1,key,{timeout:15000});
  await page.getByRole('button',{name:/^Encourage /}).click();
  await expect(page.getByText('Encouragement remembered on this device.',{exact:false})).toBeVisible();
  const remembered=await get(page);assert.ok(remembered.mind.associations.observations>=2);assert.deepEqual(remembered.beast.qbeast,original.beast.qbeast);
  await page.getByRole('button',{name:'Pause activity',exact:true}).click();
  const checkpoint=await get(page);await page.waitForTimeout(8500);assert.deepEqual((await get(page)).beast.behavior,checkpoint.beast.behavior);
  results.tests.push('create/name/pet/feed/rest/train 6/6/learn/real toy tick/encourage/pause');

  // Quota is a failure fixture: the visible alias and confirmed record must stay unchanged.
  await page.evaluate(()=>{window.__originalSet=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='beastbox-companion-session-v1'&&JSON.parse(v).beast?.displayName==='MustNotSave')throw Error('Controlled storage quota failure');return window.__originalSet.call(this,k,v);};});
  await care.getByLabel('Beast name').fill('MustNotSave');await care.getByRole('button',{name:'Name',exact:true}).click();
  await expect(care.locator('[data-care-status]')).toContainText('Controlled storage quota failure');assert.equal((await get(page)).beast.displayName,'Juniper');
  await page.evaluate(()=>{Storage.prototype.setItem=window.__originalSet;});
  await care.getByRole('button',{name:'Save on this device',exact:true}).click();await expect(care.locator('[data-care-status]')).toContainText('Saved on this device');
  const saved=await get(page);await page.reload();await expect(page.locator('[data-creature-habitat]')).toHaveAttribute('data-creature-id',id);
  assert.deepEqual((await get(page)).mind,saved.mind);assert.deepEqual((await get(page)).beast.behavior,saved.beast.behavior);
  results.tests.push('failed save stays failed; successful save/reload preserves exact memory and behavior');

  await care.locator('summary').filter({hasText:'Carry your beast'}).click();
  const downloaded=page.waitForEvent('download');await care.getByRole('button',{name:'Download device journey'}).click();const artifact=await downloaded;
  const journeyPath=out+'/juniper.beastjourney';await artifact.saveAs(journeyPath);
  const newContext=await browser.newContext({viewport:{width:375,height:812},isMobile:true,hasTouch:true});
  const restore=await newContext.newPage();await restore.goto(origin+'/beast-cage');
  await restore.locator('[data-care-deck] input[type=file]').setInputFiles(journeyPath);
  await expect(restore.locator('[data-care-status]')).toContainText('Device journey restored');
  const imported=await get(restore);assert.equal(imported.beast.qbeast.profile.id,id);assert.deepEqual(imported.mind,saved.mind);assert.deepEqual(imported.beast.behavior,saved.beast.behavior);assert.equal(imported.beast.nativeStage,1);
  await newContext.close();results.tests.push('real .beastjourney download/import in a separate fresh browser context');

  for(const route of ['/beast-cage','/brain-bay','/settings','/research#god-core','/spark/index.html']){
   await page.goto(origin+route);
   await page.waitForFunction(k=>JSON.parse(localStorage.getItem(k))?.beast?.qbeast?.profile?.id,key);
   for(const width of [320,375,390,430,1280]){
    await page.setViewportSize({width,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),route+' overflow at '+width);
   }
   await page.setViewportSize({width:390,height:844});
   if(route==='/research#god-core'){await expect(page.getByRole('button',{name:'Export local observation'})).toBeVisible();await page.locator('#god-core').screenshot({path:out+'/lab-core-390.png'});}
   if(route==='/beast-cage')await page.screenshot({path:out+'/habitat-390.png',fullPage:true});
   assert.equal((await get(page)).beast.qbeast.profile.id,id);
  }
  results.tests.push('320/375/390/430/1280 layouts, same QBEAST, forced WebGL failure retains sprite');
  await page.goto(origin+'/settings');
  await page.getByRole('switch',{name:'Reduce motion'}).click();
  await page.goto(origin+'/beast-cage');await expect(page.locator('html')).toHaveAttribute('data-beastbox-reduced-motion','true');
  assert.equal((await get(page)).beast.qbeast.profile.id,id);
  results.tests.push('saved reduced-motion preference reaches actual habitat renderer');
  assert.deepEqual(errors,[]);results.page_errors=errors;results.qbeast_id=id;
  await fs.writeFile(out+'/results.json',JSON.stringify(results,null,2)+'\n');console.log('HF_GENESIS_WORLD_PASS '+JSON.stringify(results));
 }catch(error){await page.screenshot({path:out+'/failure.png',fullPage:true}).catch(()=>{});throw error;}finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
