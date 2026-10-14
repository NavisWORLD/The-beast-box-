/** Static Spark popup interaction regression. The built-in server has no model:
 * all API calls return explicit offline errors. No simulated model success is
 * used here. BEAST_TEST_BROWSER=webkit also checks the installed WebKit engine;
 * these automated checks are not physical iPhone verification.
 */
const { chromium,webkit } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');
const publicRoot = path.resolve(__dirname, '../public');
const MIME = {'.html':'text/html','.mjs':'application/javascript','.js':'application/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.ico':'image/x-icon','.webmanifest':'application/manifest+json'};
async function serve() {
 const requests=[];
 const server=http.createServer(async(req,res)=>{
  const pathname=new URL(req.url,'http://127.0.0.1').pathname;
  if(pathname.startsWith('/api/')) {
   let body='';for await(const chunk of req)body+=chunk;
   requests.push({url:pathname,method:req.method,body:body?JSON.parse(body):null});
   res.writeHead(503,{'Content-Type':'application/json'});
   res.end(JSON.stringify({error:'Test server has no configured model provider.',...(pathname.startsWith('/api/cosmos/private/')?{status:'Offline test server has no private cloud configured.'}:{})}));return;
  }
  const file=path.resolve(publicRoot,'.'+decodeURIComponent(pathname));
  if(!file.startsWith(publicRoot+path.sep)){res.writeHead(403);res.end();return;}
  try{const content=await fs.readFile(file);res.writeHead(200,{'Content-Type':MIME[path.extname(file)]||'application/octet-stream'});res.end(content);}catch{res.writeHead(404);res.end();}
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 return {server,requests,url:'http://127.0.0.1:'+server.address().port};
}
async function popupFits(page) {
 const measurements=await page.evaluate(()=>{
  const dialog=document.querySelector('[role="dialog"]'),box=dialog.getBoundingClientRect(),form=document.querySelector('#talk-form').getBoundingClientRect(),v=window.visualViewport;
  return {box:{x:box.x,y:box.y,right:box.right,bottom:box.bottom,width:box.width,height:box.height},form:{bottom:form.bottom,width:form.width},viewport:{left:v?.offsetLeft||0,top:v?.offsetTop||0,width:v?.width||innerWidth,height:v?.height||innerHeight},documentWidth:document.documentElement.scrollWidth};
 });
 const {box,form,viewport}=measurements;
 assert.ok(box.x>=viewport.left-1&&box.y>=viewport.top-1,'popup starts within the visible viewport');
 assert.ok(box.right<=viewport.left+viewport.width+1&&box.bottom<=viewport.top+viewport.height+1,'popup stays within the visible viewport: '+JSON.stringify(measurements));
 assert.ok(form.bottom<=box.bottom+1&&form.width<=box.width+1,'composer stays inside the popup');
 assert.ok(measurements.documentWidth<=Math.ceil(viewport.width)+1,'popup does not widen the document');
 return measurements;
}
async function clickTalkAfterReload(page){
 // The selected creature can render before the popup event handler is wired.
 // Require the real ready signal and a visible modal after a real click.
 const talk=page.locator('#talk[data-chat-ready="true"]');
 await talk.waitFor({state:'visible'});
 await talk.click();
 await page.getByRole('dialog',{name:'Talk to Wraith',exact:true}).waitFor({state:'visible'});
}
(async()=>{
 const hosted=await serve();
 const engine=process.env.BEAST_TEST_BROWSER==='webkit'?'webkit':'chromium';
 let browser;
 const results=[];
 try {
  // This Canvas2D page does not require a forced software WebGL backend.
  browser=await (engine==='webkit'?webkit:chromium).launch({headless:true,...(engine==='chromium'?{executablePath:process.env.BEAST_BROWSER_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']}: {})});
  const startupContext=await browser.newContext({viewport:{width:390,height:844}}),startupPage=await startupContext.newPage();
  startupPage.setDefaultTimeout(7000);
  let releaseArchive;const archiveGate=new Promise(resolve=>{releaseArchive=resolve;});
  await startupContext.route('**/spark/user-seeds-20261004.json',async route=>{await archiveGate;if(!startupPage.isClosed())await route.fallback();});
  try{
   // Delay a real archive response; do not substitute fake model/state data.
   await Promise.all([startupPage.waitForRequest(request=>request.url().endsWith('/spark/user-seeds-20261004.json')),startupPage.goto(hosted.url+'/spark/index.html')]);
   const trigger=startupPage.locator('#talk');
   assert.equal(await trigger.isVisible(),true);
   assert.equal(await trigger.isDisabled(),true,'unwired Talk must be disabled during delayed archive startup');
   assert.equal(await trigger.getAttribute('aria-busy'),'true');
   assert.equal(await trigger.getAttribute('data-chat-ready'),null);
   releaseArchive();await startupPage.locator('#talk[data-chat-ready="true"]').waitFor({state:'visible'});
   assert.equal(await trigger.isDisabled(),false);assert.equal(await trigger.getAttribute('aria-busy'),null);
   await trigger.click();await startupPage.getByRole('dialog').waitFor({state:'visible'});
   await startupPage.getByRole('button',{name:'Close conversation',exact:true}).click();
   assert.equal(hosted.requests.filter(request=>request.method!=='GET').length,0,'startup cannot infer or opt in to cloud');
  }finally{releaseArchive();await startupContext.close();}
  for(const viewport of [{width:320,height:740},{width:375,height:812},{width:390,height:844},{width:430,height:932},{width:844,height:390},{width:1280,height:820}]) {
   const context=await browser.newContext({viewport,hasTouch:viewport.width<850,isMobile:viewport.width<850});
   const page=await context.newPage(),errors=[];page.setDefaultTimeout(7000);
   page.on('pageerror',error=>errors.push(error.message));
   await page.goto(hosted.url+'/spark/index.html');
   await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId);
   const card=page.locator('.roster-card').filter({has:page.getByText('Wraith',{exact:true})});
   await card.getByRole('button',{name:'Select with Wraith',exact:true}).click();
   await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId==='bb-4a61a8d5');
   await page.evaluate(()=>history.replaceState({sparkPageMarker:'keep this page state'},''));
   const pageUrl=page.url(),historyLength=await page.evaluate(()=>history.length);
   await page.locator('#talk[data-chat-ready="true"]').click();
   const dialog=page.getByRole('dialog',{name:'Talk to Wraith',exact:true});
   await dialog.waitFor({state:'visible'});
   assert.equal(await dialog.getAttribute('aria-modal'),'true');
   assert.equal(await page.locator('#talk-text').evaluate(node=>document.activeElement===node),true,'opening focuses the composer');
   assert.ok(await page.locator('#talk-text').evaluate(node=>parseFloat(getComputedStyle(node).fontSize)>=16),'composer uses readable phone text without focus zoom');
   assert.equal(await page.evaluate(()=>document.body.style.position),'fixed','open modal locks the background');
   assert.equal(await page.locator('main').evaluate(node=>node.inert),true,'background controls are inert while the modal is open');
   const lockedScroll=await page.evaluate(()=>-parseFloat(document.body.style.top));
   if(viewport.width===1280){for(let i=0;i<8;i++)await page.keyboard.press('Tab');assert.equal(await dialog.evaluate(node=>node.contains(document.activeElement)),true,'keyboard focus stays within the modal');}
   const bounds=await popupFits(page);
   if(viewport.width===320){
    assert.equal(hosted.requests.filter(r=>r.url.startsWith('/api/cosmos/private/')).length,0,'opening the popup makes no private cloud request');
    await page.getByText('Conversation settings',{exact:true}).click();
    assert.equal(await page.getByRole('button',{name:'Restore my cloud conversation',exact:true}).count(),1,'private restore is an explicit action');
    const cloudSync=page.getByLabel('Save new verified exchanges to my private cloud',{exact:true});
    assert.equal(await cloudSync.isChecked(),false);assert.equal(await cloudSync.isDisabled(),true,'cloud saving requires restored identity and server consent');
    await Promise.all([page.waitForResponse(response=>response.url().endsWith('/api/cosmos/private/session')),page.getByRole('button',{name:'Restore my cloud conversation',exact:true}).click()]);
    await page.waitForFunction(()=>document.getElementById('talk-cloud-status')?.textContent.includes('Offline test server'));
    assert.equal(await cloudSync.isChecked(),false);assert.equal(await cloudSync.isDisabled(),true,'failed private restore cannot authorize a save');
    assert.equal(await page.locator('[data-talk-turn]').count(),0,'failed cloud restore does not replace conversation');
    assert.equal(await page.getByLabel('Share recent conversation with the selected provider',{exact:true}).isChecked(),false,'cloud restore never enables provider history sharing');
    assert.equal(await page.getByRole('button',{name:'Retry cloud save',exact:true}).count(),0,'offline model and failed restore offer no fabricated exchange to retry');
    await page.getByText('Conversation settings',{exact:true}).click();
   }
   assert.equal(await page.evaluate(()=>history.length),historyLength+1,'opening a popup creates one same-page history marker for Android Back');
   assert.equal(await page.evaluate(()=>history.state.sparkPageMarker),'keep this page state','popup history preserves existing page state');
   const draft='A private draft for Wraith';
   await page.locator('#talk-text').fill(draft);
   await page.goBack();await dialog.waitFor({state:'hidden'});
   assert.equal(page.url(),pageUrl,'Back dismisses chat without leaving Spark');
   assert.equal(await page.evaluate(()=>document.body.style.position),'','Back releases body scroll');
   assert.equal(await page.locator('#talk').evaluate(node=>document.activeElement===node),true,'Back restores focus to Talk');
   await page.locator('#talk').click();assert.equal(await page.locator('#talk-text').inputValue(),draft,'Back keeps the conversation draft');
   await page.getByRole('button',{name:'Minimize conversation',exact:true}).click();
   assert.equal(await dialog.count(),0,'minimized popup leaves the accessibility dialog tree');
   assert.equal(await page.evaluate(()=>document.body.style.position),'','minimizing releases background scroll');
   await page.getByRole('button',{name:'Resume conversation with Wraith',exact:true}).click();
   assert.equal(await page.locator('#talk-text').inputValue(),draft,'minimizing preserves the draft');
   await page.getByRole('button',{name:'Expand conversation',exact:true}).click();
   await popupFits(page);
   await page.getByRole('button',{name:'Restore conversation size',exact:true}).click();
   if(viewport.width===375){
    await page.evaluate(()=>{Object.defineProperties(window.visualViewport,{height:{value:300,configurable:true},offsetTop:{value:90,configurable:true}});window.visualViewport.dispatchEvent(new Event('resize'));});
    await popupFits(page);
    const keyboardMetrics=await page.evaluate(()=>Object.fromEntries(['talk-dialog','talk-scroll','talk-brain-bar','talk-form'].map(id=>[id,document.getElementById(id).getBoundingClientRect().height])));
    assert.ok(keyboardMetrics['talk-scroll']>=40,'simulated keyboard leaves an operable history scroll area: '+JSON.stringify(keyboardMetrics));
    await page.evaluate(()=>{delete window.visualViewport.height;delete window.visualViewport.offsetTop;window.visualViewport.dispatchEvent(new Event('resize'));});
   }
   await page.getByRole('button',{name:'Send message',exact:true}).click();
   await page.getByRole('alert').filter({hasText:'No model reply received'}).waitFor();
   assert.ok((await page.locator('#talk-reply').textContent()).includes('offline'),'model status reports offline');
   assert.equal(await page.locator('#talk-text').inputValue(),draft,'an offline request keeps the draft');
   assert.equal(await page.locator('[data-talk-turn]').count(),0,'offline errors never create a model turn');
   assert.ok(!(await dialog.textContent()).includes('Connected ·'),'offline never claims model connection');
   await page.getByRole('button',{name:'Try on-device pattern',exact:true}).click();
   assert.ok((await page.locator('[data-talk-pattern]').textContent()).includes('scripted'),'pattern output is explicitly labeled');
   assert.equal(await page.locator('[data-talk-turn]').count(),0,'scripted patterns stay out of verified model history');
   await page.getByRole('button',{name:'Change teacher',exact:true}).click();
   await page.getByLabel('My local Ollama',{exact:true}).check();
   await page.getByLabel('Ollama address',{exact:true}).fill('https://example.com');
   await page.getByRole('button',{name:'Send message',exact:true}).click();
   await page.getByRole('alert').filter({hasText:'Local Ollama must be on this computer'}).waitFor();
   await page.getByLabel('My Hugging Face key',{exact:true}).check();
   await page.getByRole('button',{name:'Send message',exact:true}).click();
   await page.getByRole('alert').filter({hasText:'Paste your personal Hugging Face token'}).waitFor();
   await page.getByLabel('Connected Brain Bay',{exact:true}).check();
   await page.getByRole('button',{name:'Send message',exact:true}).click();
   await page.getByRole('alert').filter({hasText:'Pair your owner session'}).waitFor();
   assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-talk-prefs-v1')).route),'connected-brain-bay','uses the shared brain preference key');
   await page.getByRole('button',{name:'Close conversation',exact:true}).click();
   assert.equal(await page.evaluate(()=>document.body.style.position),'');
   assert.ok(Math.abs(await page.evaluate(()=>window.scrollY)-lockedScroll)<2,'closing restores the original page scroll position');
   assert.equal(await page.locator('#talk').evaluate(node=>document.activeElement===node),true,'close restores focus to the talk button');
   await page.waitForFunction(()=>!history.state?.beastboxChat);assert.equal(page.url(),pageUrl,'button dismissal consumes only the chat history marker');
   const identity=await page.locator('#view').getAttribute('data-creature-id');
   await page.reload();
   await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId==='bb-4a61a8d5');
   try{await clickTalkAfterReload(page);}catch(error){console.error('STATIC_RELOAD_DIAGNOSTIC',JSON.stringify({url:page.url(),viewport,...await page.evaluate(()=>({ready:document.readyState,title:document.title,talk:!!document.querySelector('#talk'),talkDetails:(()=>{const el=document.querySelector('#talk');if(!el)return null;const r=el.getBoundingClientRect(),s=getComputedStyle(el);return {display:s.display,visibility:s.visibility,pointerEvents:s.pointerEvents,rect:{x:r.x,y:r.y,width:r.width,height:r.height},disabled:el.disabled,hidden:el.hidden,closestInert:el.closest('[inert]')?.tagName,closestHidden:el.closest('[hidden]')?.tagName,ariaHidden:el.closest('[aria-hidden="true"]')?.tagName,bodyStyle:document.body.getAttribute('style')};})(),inert:document.querySelector('main')?.inert,dialogHidden:document.querySelector('#spark-chat')?.hidden,history:history.state,body:document.body?.innerText.slice(0,300)}))}));throw error;}
   assert.equal(await page.locator('#talk-text').inputValue(),draft,'device draft survives reload for the same canonical Beast');
   await page.getByText('Conversation settings',{exact:true}).click();
   await page.getByLabel('Keep this conversation',{exact:true}).selectOption('session');
   const storage=await page.evaluate(()=>({retention:localStorage.getItem('beastbox-talk-retention-v1'),deviceDraft:localStorage.getItem('beastbox-talk-draft-v1:spark:bb-4a61a8d5'),tabDraft:sessionStorage.getItem('beastbox-talk-draft-v1:spark:bb-4a61a8d5')}));
   assert.equal(storage.retention,'session');assert.equal(storage.deviceDraft,null);assert.equal(storage.tabDraft,draft);
   assert.equal(await page.getByLabel('Share recent conversation with the selected provider',{exact:true}).isChecked(),false,'history sharing defaults to off');
   await page.keyboard.press('Escape');
   assert.equal(await page.evaluate(()=>document.body.style.position),'','Escape restores body styles');
   assert.equal(await page.locator('#talk').evaluate(node=>document.activeElement===node),true);
   if(viewport.width===430){
    const requestCount=hosted.requests.length;
    await page.evaluate(()=>window.dispatchEvent(new CustomEvent('beastbox:open-chat',{detail:{draft:'Android bounded draft'}})));
    await page.getByRole('dialog',{name:'Talk to Wraith',exact:true}).waitFor();
    assert.equal(await page.locator('#talk-text').inputValue(),'Android bounded draft');
    assert.equal(hosted.requests.length,requestCount,'opening a native draft never triggers hidden inference');
    await page.locator('#talk-text').fill(draft);await page.keyboard.press('Escape');
   }
   if(viewport.width===390){
    await page.getByRole('button',{name:'Talk with Lumenwisp',exact:true}).click();
    await page.getByRole('dialog',{name:'Talk to Lumenwisp',exact:true}).waitFor();
    assert.equal(await page.locator('#talk-text').inputValue(),'','a different canonical creature has its own draft');
    await page.locator('#talk-text').fill('A separate Lumenwisp draft');
    await page.getByRole('button',{name:'Close conversation',exact:true}).click();
    await page.getByRole('button',{name:'Talk with Wraith',exact:true}).click();
    await page.getByRole('dialog',{name:'Talk to Wraith',exact:true}).waitFor();
    assert.equal(await page.locator('#talk-text').inputValue(),draft,'returning to Wraith restores only its draft');
    await page.keyboard.press('Escape');
   }
   // A bounded older verified log exercises real per-creature storage and scroll
   // rendering, without pretending that the offline test server answered it.
   await page.evaluate(()=>{
    localStorage.setItem('beastbox-talk-retention-v1','device');
    localStorage.setItem('beastbox-talk-log-v1:spark:bb-4a61a8d5',JSON.stringify(Array.from({length:24},(_,i)=>({role:i%2?'beast':'you',text:'Previously stored conversation '+i+' '+('star '.repeat(25)),...(i%2?{model:'previously verified provider'}:{})}))));
   });
   await page.reload();await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId==='bb-4a61a8d5');
   await clickTalkAfterReload(page);
   assert.equal(await page.locator('[data-talk-turn]').count(),24,'loads shared bounded history');
   assert.equal(await page.locator('#talk-scroll').evaluate(node=>node.scrollHeight>node.clientHeight),true,'conversation history is scrollable');
   await popupFits(page);
   if(process.env.BEAST_POPUP_SCREENSHOTS){await fs.mkdir(process.env.BEAST_POPUP_SCREENSHOTS,{recursive:true});await page.screenshot({path:path.join(process.env.BEAST_POPUP_SCREENSHOTS,`spark-chat-${viewport.width}x${viewport.height}.png`),animations:'disabled'});}
   assert.deepEqual(errors,[],'popup and canonical roster selection produce no browser exceptions');
   results.push({viewport,canonicalIdentity:identity,bounds:bounds.box,offline:true,persistentDraft:true,tabRetention:true,accessibleDismissal:true,scrollableHistory:true});
   await context.close();
  }
  assert.equal(hosted.requests.filter(r=>r.url==='/api/guest').length,results.length,'one guest request per offline send, with no automatic retry or paid fallback');
  assert.equal(hosted.requests.filter(r=>r.url==='/api/status').length,results.length,'explicit Brain Bay choice uses the shared status gate');
  assert.ok(hosted.requests.every(r=>!r.body||r.body.provider==='rawrphos-local'),'invalid BYOK/local configuration never reaches a paid provider');
  assert.ok(hosted.requests.filter(r=>r.body).every(r=>!r.body.text.includes('Previously stored conversation')),'history is private by default');
  assert.equal(hosted.requests.filter(r=>r.url.startsWith('/api/cosmos/private/')).length,1,'private cloud is contacted only for the explicit restore');
  assert.ok(hosted.requests.filter(r=>r.url.startsWith('/api/cosmos/private/')).every(r=>r.method==='GET'&&r.body===null),'offline tests never provision private worlds, save histories, or set server consent');
  console.log(JSON.stringify({passed:true,engine,physicalDevice:false,samePageBack:true,privateCloudExplicitRestore:true,privateCloudOfflineOnly:true,evidence:'Automated browser with honest offline API stub; not a model success or physical iPhone test',results},null,2));
 } finally {await browser?.close();hosted.server.closeAllConnections();await new Promise(resolve=>hosted.server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1});
