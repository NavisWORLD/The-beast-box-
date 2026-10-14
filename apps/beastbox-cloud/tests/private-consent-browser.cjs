/** Real React controls against explicitly synthetic private API fixtures.
 * This regression does not claim Azure execution, quantum jobs or inference. */
const {chromium,webkit}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises'),path=require('node:path');
const expect=require('playwright/test').expect.configure({timeout:10000});
const engine=process.env.BEAST_TEST_BROWSER==='webkit'?'webkit':'chromium';
const origin=process.argv[2]||'http://127.0.0.1:3000',owner='u_'+'1'.repeat(32);

(async()=>{
 const browser=await (engine==='webkit'?webkit:chromium).launch({headless:true,
  ...(process.env.BEAST_BROWSER_EXECUTABLE?{executablePath:process.env.BEAST_BROWSER_EXECUTABLE}:{}),
  args:engine==='chromium'?['--no-sandbox','--disable-dev-shm-usage']:[]});
 const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
 let record,version=1;const mutations=[],errors=[],inference=[];
 page.on('pageerror',error=>errors.push(error.message));
 await page.route('**/api/guest',async route=>{inference.push(route.request().url());await route.abort();});
 await page.route('**/api/cosmos/private/**',async route=>{
  const request=route.request(),url=new URL(request.url());
  if(url.pathname.endsWith('/session'))return route.fulfill({json:{configured:true,authorized:true,owner}});
  if(request.method()==='PUT'){
   const body=request.postDataJSON();mutations.push(body);
   assert.equal(body.expectedOwner,owner);assert.equal(body.version,version);
   // A delayed acknowledgment must not display an uncommitted consent state.
   await new Promise(resolve=>setTimeout(resolve,150));
   if(body.action.kind==='chat-consent')record.sync.conversationConsent=body.action.enabled;
   if(body.action.kind==='growth-consent'){
    record.growth.optedIn=body.action.enabled;
    record.growth.schedule=body.action.enabled&&body.action.schedule===true;
   }
   version++;
  }
  return route.fulfill({json:{ok:true,record,version}});
 });
 try{
  await page.goto(origin+'/spark/index.html');
  await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId);
  await page.locator('#generate').click();await expect(page.locator('#status')).toContainText('Spawned');
  await page.locator('#beast-name').fill('Release Test Beast');
  await page.getByRole('button',{name:'NAME MY BEAST',exact:true}).click();
  await expect(page.locator('#status')).toContainText('Named Release Test Beast');
  const beast=await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')).beast);
  record={owner,beastId:beast.qbeast.profile.id,
   profile:{name:'PRIVATE PROTOCOL FIXTURE',provenance:{seed:beast.seed}},
   identity:{qbeastId:beast.qbeast.profile.id,seed:beast.seed},memory:[],
   conversations:[{role:'you',id:'layout-fixture-you',text:'PRIVATE LAYOUT FIXTURE: check the conversation and options bounds.'},
    {role:'beast',id:'layout-fixture-beast',text:'PRIVATE LAYOUT FIXTURE ONLY. '.repeat(14)}],
   personalityState:{curiosity:50,engagement:0},growth:{status:'OFF',optedIn:false,schedule:false},
   sync:{conversationConsent:false}};
  await page.goto(origin+'/settings');
  const cloud=page.getByRole('region',{name:'Private creature cloud memory'});
  await cloud.getByRole('button',{name:'Restore cloud memory',exact:true}).click();
  await expect(cloud.getByRole('status')).toContainText('Read back the private memory');
  const consent=cloud.getByRole('checkbox',{name:'Allow this Beast’s conversation to be saved privately in the cloud',exact:true});
  await expect(consent).not.toBeChecked();
  await consent.click();await expect(consent).toBeChecked();
  assert.equal(mutations.length,1);assert.equal(mutations[0].action.enabled,true);
  await consent.click();await expect(consent).not.toBeChecked();
  assert.equal(mutations.length,2);assert.equal(mutations[1].action.enabled,false);
  const growth=cloud.getByRole('checkbox',{name:'Allow bounded simulator growth',exact:true});
  const schedule=cloud.getByRole('checkbox',{name:'Schedule bounded growth (at most one attempt per Beast per day)',exact:true});
  await expect(schedule).toBeDisabled();
  await growth.click();await expect(growth).toBeChecked();await expect(schedule).toBeEnabled();
  await schedule.click();await expect(schedule).toBeChecked();
  await growth.click();await expect(growth).not.toBeChecked();
  await expect(schedule).not.toBeChecked();await expect(schedule).toBeDisabled();
  assert.equal(mutations.length,5);
  assert.deepEqual(mutations.slice(2).map(row=>row.action),[
   {kind:'growth-consent',enabled:true,schedule:false},
   {kind:'growth-consent',enabled:true,schedule:true},
   {kind:'growth-consent',enabled:false,schedule:false}]);
  // Settings consent and popup saving are independent user choices.
  await consent.click();await expect(consent).toBeChecked();
  await page.locator('button[data-critical-control][aria-controls="beast-chat-overlay"]').click();
  const dialog=page.locator('[data-companion-chat-overlay]');await expect(dialog).toBeVisible();
  await dialog.getByText('Conversation & observation settings',{exact:true}).click();
  await dialog.getByRole('button',{name:'Restore my private cloud conversation',exact:true}).click();
  await expect(dialog.getByText(/Restored this Beast’s private conversation/)).toBeVisible();
  const saving=dialog.getByLabel(/Save new verified exchanges to my private cloud/);
  await expect(saving).not.toBeChecked();await saving.click();await expect(saving).toBeChecked();
  const history=dialog.getByLabel('Share recent conversation with the selected provider',{exact:true});
  await expect(history).not.toBeChecked();await history.click();await expect(history).toBeChecked();
  await history.click();await expect(history).not.toBeChecked();
  await dialog.getByRole('button',{name:'Close chat',exact:true}).click();await expect(dialog).toBeHidden();
  await page.locator('button[data-critical-control][aria-controls="beast-chat-overlay"]').click();
  await expect(saving).toBeChecked();await saving.click();await expect(saving).not.toBeChecked();
  // Real long text exposed flex shrinking that let replies paint into options.
  // These imported fixture rows are unverified text, never fabricated inference.
  for(const viewport of [{width:390,height:844},{width:320,height:568},{width:844,height:390}]){
   await page.setViewportSize(viewport);
   await expect.poll(()=>dialog.locator('[aria-label^="Conversation with"]').evaluate(log=>{
    const rect=log.getBoundingClientRect(),rows=Array.from(log.children).filter(node=>node.textContent.trim());
    const summary=Array.from(log.parentElement.querySelectorAll('details>summary'))
     .find(node=>node.textContent==='Conversation & observation settings').getBoundingClientRect();
    return rows.every(node=>node.getBoundingClientRect().bottom<=rect.bottom+1)&&rect.bottom<=summary.top+1;
   })).toBe(true);
   const composer=dialog.locator('form');
   await expect.poll(()=>composer.evaluate(node=>{const r=node.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight+1;})).toBe(true);
  }
  await page.setViewportSize({width:390,height:844});
  assert.equal(mutations.length,6,'Popup preference controls never write cloud data by themselves');
  assert.equal(inference.length,0);assert.deepEqual(errors,[]);
  if(process.env.BEAST_EVIDENCE_DIR){
   await fs.mkdir(process.env.BEAST_EVIDENCE_DIR,{recursive:true});
   await page.screenshot({path:path.join(process.env.BEAST_EVIDENCE_DIR,'private-consent-390.png')});
  }
  console.log(JSON.stringify({status:'PASSED',engine,viewport:'390x844',classification:'SYNTHETIC_PRIVATE_API_FIXTURE',mutations:6,inference:0,
   gates:['conversation enable/revoke acknowledged','growth/schedule dependency','independent popup saving','provider-history opt-in/revoke','close/reopen retains saving','no text overlap in portrait/landscape','pinned composer','no unsolicited writes or inference']}));
 }catch(error){
  if(process.env.BEAST_EVIDENCE_DIR){
   await fs.mkdir(process.env.BEAST_EVIDENCE_DIR,{recursive:true});
   await page.screenshot({path:path.join(process.env.BEAST_EVIDENCE_DIR,'failure.png')});
  }
  throw error;
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
