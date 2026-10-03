/** Optional local demo client. Starts only the installed Beast stdio server. */
const {spawn}=require('node:child_process');
const path=require('node:path');
const {parseStrictJson,MAX_BYTES}=require('../dist/verifier.js');

class McpClient{
 constructor(store,{trustedPublicKey,timeoutMs=5000}={}){
  this.serial=0;this.pending=new Map();this.buffer='';this.stderr='';this.closed=false;this.timeoutMs=timeoutMs;this.transcript=[];
  const args=[path.join(__dirname,'../bin/quantum-beast.cjs'),'mcp','--store',path.resolve(store)];
  if(trustedPublicKey)args.push('--trust-key',trustedPublicKey);
  this.child=spawn(process.execPath,args,{stdio:['pipe','pipe','pipe']});
  this.exited=new Promise(resolve=>this.child.once('close',(code,signal)=>resolve({code,signal})));
  this.child.on('error',e=>this.fail(e));
  this.child.on('exit',()=>this.fail(Error('MCP server disconnected')));
  this.child.stdin.on('error',e=>this.fail(e));
  this.child.stdout.setEncoding('utf8');
  this.child.stdout.on('data',chunk=>{
   try{
    this.buffer+=chunk;
    while(this.buffer.includes('\n')){
     const end=this.buffer.indexOf('\n'),line=this.buffer.slice(0,end);this.buffer=this.buffer.slice(end+1);
     if(!line.trim())continue;
     const reply=parseStrictJson(line),pending=this.pending.get(reply.id);
     if(!pending)throw Error('Unexpected MCP response');
     this.pending.delete(reply.id);clearTimeout(pending.timer);
     this.transcript.push({direction:'server',message:reply});
     if(reply.error)pending.reject(Error(reply.error.message));else pending.resolve(reply.result);
    }
    if(Buffer.byteLength(this.buffer)>MAX_BYTES)throw Error('MCP response exceeds limit');
   }catch(e){this.fail(e);this.child.kill();}
  });
  this.child.stderr.on('data',chunk=>{this.stderr=(this.stderr+chunk).slice(-4096);});
 }
 static async connect(store,options={}){
  const client=new McpClient(store,options);
  try{
   const result=await client.request('initialize',{protocolVersion:'2025-11-25',capabilities:{},clientInfo:{name:'quantum-beast-demo',version:require('../package.json').version}});
   if(result.protocolVersion!=='2025-11-25')throw Error('Unsupported MCP protocol');
   client.send({jsonrpc:'2.0',method:'notifications/initialized'});
   return client;
  }catch(e){await client.close();throw e;}
 }
 fail(error){
  this.closed=true;
  for(const pending of this.pending.values()){clearTimeout(pending.timer);pending.reject(error);}
  this.pending.clear();
 }
 send(message){
  if(this.closed)throw Error('MCP client is closed');
  const line=JSON.stringify(message)+'\n';
  if(Buffer.byteLength(line)>MAX_BYTES)throw Error('MCP request exceeds limit');
  this.transcript.push({direction:'client',message});this.child.stdin.write(line);
 }
 request(method,params={}){
  return new Promise((resolve,reject)=>{
   const id=++this.serial;
   const timer=setTimeout(()=>{this.pending.delete(id);reject(Error('MCP timeout'));this.fail(Error('MCP timeout'));this.child.kill();},this.timeoutMs);
   this.pending.set(id,{resolve,reject,timer});
   try{this.send({jsonrpc:'2.0',id,method,params});}catch(e){this.pending.delete(id);clearTimeout(timer);reject(e);}
  });
 }
 async tool(name,args={}){
  const result=await this.request('tools/call',{name,arguments:args});
  if(result.isError)throw Error(result.content?.[0]?.text??'MCP tool failed');
  return result.structuredContent.result;
 }
 async close(){
  this.fail(Error('MCP client closed'));
  this.child.stdin.end();
  const timer=setTimeout(()=>this.child.kill(),1000);
  try{return await this.exited;}finally{clearTimeout(timer);}
 }
}
module.exports={McpClient};
