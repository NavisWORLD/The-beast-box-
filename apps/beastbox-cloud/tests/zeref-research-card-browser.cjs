// Real static evidence + rendered production build. No model or sensor request.
// Requires Playwright with local browser binaries; npm test remains unit-only.
const {spawn}=require('node:child_process');
const {writeFileSync}=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const {chromium,webkit}=require('playwright');
const app=path.resolve(__dirname,'..');
const port=Number(process.env.RESEARCH_CARD_TEST_PORT||3114);
const origin=`http://127.0.0.1:${port}`;
const server=spawn(process.execPath,[require.resolve('next/dist/bin/next'),'start','--hostname','127.0.0.1','--port',String(port)],{cwd:app,stdio:['ignore','pipe','pipe']});
let serverLog='';server.stdout.on('data',b=>serverLog+=b);server.stderr.on('data',b=>serverLog+=b);
const results=[];
const delay=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 try{
  let ready=false;
  for(let n=0;n<120;n++){try{const r=await fetch(origin+'/spark/zeref-learning/research-status.json');if(r.ok){ready=true;break;}}catch{}await delay(250);}
  assert.ok(ready,'built Next server did not become ready: '+serverLog);
  const engines=[{name:'Chromium',type:chromium,options:{executablePath:process.env.CHROMIUM_EXECUTABLE_PATH}},
   {name:'WebKit',type:webkit,options:{executablePath:process.env.WEBKIT_EXECUTABLE_PATH,env:{...process.env,WEBKIT_EXEC_PATH:process.env.WEBKIT_EXEC_PATH,WEBKIT_INJECTED_BUNDLE_PATH:process.env.WEBKIT_INJECTED_BUNDLE_PATH,WEBKIT_INSPECTOR_RESOURCES_PATH:process.env.WEBKIT_INSPECTOR_RESOURCES_PATH,LD_LIBRARY_PATH:process.env.WEBKIT_LD_LIBRARY_PATH||process.env.LD_LIBRARY_PATH}}}];
  for(const engine of engines){
   const browser=await engine.type.launch({...engine.options,headless:true});
   try{
    for(const width of [320,390,1440]){
     const context=await browser.newContext({viewport:{width,height:844},isMobile:width<600,hasTouch:width<600,reducedMotion:'reduce'});
     try{
      const page=await context.newPage();
      for(const route of ['/research','/beast-cage']){
       const response=await page.goto(origin+route,{waitUntil:'domcontentloaded'});assert.equal(response.status(),200);
       const card=page.locator('[data-zeref-research]');
       await card.locator('h3').waitFor();
       await page.waitForFunction(()=>document.querySelector('[data-zeref-research]')?.dataset.researchStatus==='approved-research-parent');
       await card.scrollIntoViewIfNeeded();
       const text=await card.innerText();assert.match(text,/14,448 training steps/);assert.match(text,/bb-deada969/);assert.match(text,/bb-7f9c2a03/);
       await card.locator('[data-experiment="012"] summary').click();assert.match(await card.innerText(),/generated grounded answers stayed 0\/7/);
       await card.locator('[data-experiment="013"] summary').click();assert.match(await card.innerText(),/worse than matched action-blind/);
       await card.locator('details').last().locator('summary').click();assert.match(await card.innerText(),/14,000-step/);assert.match(await card.innerText(),/Goal completion.*unproven/s);
       const geometry=await card.evaluate(el=>({left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right,width:innerWidth,cardScroll:el.scrollWidth,cardClient:el.clientWidth,summaryHeights:[...el.querySelectorAll('summary')].map(x=>x.getBoundingClientRect().height)}));
       assert.ok(geometry.left>=-1&&geometry.right<=width+1,JSON.stringify(geometry));assert.ok(geometry.cardScroll<=geometry.cardClient+1,JSON.stringify(geometry));assert.ok(geometry.summaryHeights.every(h=>h>=44),JSON.stringify(geometry));
       if(route==='/beast-cage')assert.equal(await page.locator('[data-neural-accepted="false"]').count(),1,'historical 011 rejection remains visible');
       results.push({engine:engine.name,width,route,passed:true,geometry});
      }
     }finally{await context.close();}
    }
   }finally{await browser.close();}
  }
  const out={schema:'zeref-research-card-browser/v1',at:new Date().toISOString(),evidence:'automated Chromium and WebKit; no physical device, no model inference',cases:results};
  if(process.env.RESEARCH_CARD_TEST_OUTPUT)writeFileSync(process.env.RESEARCH_CARD_TEST_OUTPUT,JSON.stringify(out,null,2)+'\n');
  console.log(JSON.stringify(out));
 }finally{server.kill('SIGTERM');}
})().catch(e=>{console.error(e);process.exitCode=1;});
