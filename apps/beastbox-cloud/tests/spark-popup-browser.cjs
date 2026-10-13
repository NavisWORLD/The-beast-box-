/** Real static-Spark browser regression; no inference response fixture is used.
 * BEAST_BROWSER_EXECUTABLE selects an available Playwright Chromium executable.
 * With no URL argument, the built-in server deliberately returns honest offline
 * API responses. Provider success must be verified separately against a real host.
 */
const { chromium } = require('playwright');
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
  if(pathname.startsWith('/api/')) {requests.push({url:pathname,method:req.method});res.writeHead(503,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'Test server has no configured model provider.'}));return;}
  const file=path.resolve(publicRoot,'.'+decodeURIComponent(pathname));
  if(!file.startsWith(publicRoot+path.sep)){res.writeHead(403);res.end();return;}
  try {const content=await fs.readFile(file);res.writeHead(200,{'Content-Type':MIME[path.extname(file)]||'application/octet-stream'});res.end(content);}catch {res.writeHead(404);res.end();}
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 return {server,requests,url:'http://127.0.0.1:'+server.address().port};
}
(async()=>{
 const hosted=process.argv[2]?null:await serve(),url=process.argv[2]||hosted.url;
 const browser=await chromium.launch({headless:true,executablePath:process.env.BEAST_BROWSER_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const results=[];
 try {
  for(const viewport of [{width:320,height:740},{width:390,height:844},{width:844,height:390},{width:1280,height:820}]) {
   const context=await browser.newContext({viewport,hasTouch:viewport.width<850,isMobile:viewport.width<850});
   const page=await context.newPage(),errors=[];
   page.on('pageerror',error=>errors.push(error.message));
   await page.goto(url+'/spark/index.html');
   try {await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId,null,{timeout:30000});}catch(error){throw new Error(String(error)+'; browser='+JSON.stringify(errors)+'; status='+await page.locator('#status').textContent());}
   const card=page.locator('.roster-card').filter({has:page.getByText('Wraith',{exact:true})});
   await card.getByRole('button',{name:'Select with Wraith',exact:true}).click();
   try{await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId==='bb-4a61a8d5',null,{timeout:3000});}catch(error){throw new Error('Wraith roster did not select its canonical identity; browser='+JSON.stringify(errors)+'; '+error.message);}
   assert.deepEqual(errors,[],'registered creature selection must run without a shadowed callback');
   results.push({viewport,rosterSelect:true,canonicalIdentity:'bb-4a61a8d5'});
   await context.close();
  }
  console.log(JSON.stringify({passed:true,evidence:'Automated Chromium; not a physical iPhone',results},null,2));
 } finally {await browser.close();if(hosted){hosted.server.closeAllConnections();await new Promise(resolve=>hosted.server.close(resolve));}}
})().catch(error=>{console.error(error);process.exitCode=1});
