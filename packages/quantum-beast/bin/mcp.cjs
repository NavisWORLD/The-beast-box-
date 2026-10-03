const {BeastBridge}=require('../dist');
const {toolDefinitions,callTool}=require('../dist/tools.js');
const {parseStrictJson,MAX_BYTES}=require('../dist/verifier.js');
/** Deliberately small legacy stdio MCP adapter, protocol 2025-11-25. */
async function serve(store){
 let initialized=false,ready=false,buffer='';const decoder=new TextDecoder();
 const emit=x=>process.stdout.write(JSON.stringify(x)+'\n');
 async function handle(line){
  let request;
  try{request=parseStrictJson(line);}catch{emit({jsonrpc:'2.0',id:null,error:{code:-32700,message:'Invalid bounded JSON'}});return;}
  const id=request?.id;
  const error=(code,message)=>{if(id!==undefined)emit({jsonrpc:'2.0',id,error:{code,message}});};
  if(!request||Array.isArray(request)||request.jsonrpc!=='2.0'||typeof request.method!=='string'||(id!==undefined&&typeof id!=='string'&&!Number.isSafeInteger(id))){emit({jsonrpc:'2.0',id:null,error:{code:-32600,message:'Invalid request'}});return;}
  if(request.method==='notifications/initialized'){if(initialized)ready=true;return;}
  if(request.method.startsWith('notifications/'))return;
  let result;
  if(request.method==='initialize'){
   if(initialized){error(-32600,'Already initialized');return;}
   if(!request.params||typeof request.params.protocolVersion!=='string'||!request.params.clientInfo||!request.params.capabilities){error(-32602,'Invalid initialization');return;}
   initialized=true;result={protocolVersion:'2025-11-25',capabilities:{tools:{}},serverInfo:{name:'quantum-beast-bridge',version:'1.0.0'},instructions:'All content is public creature data. Proposals require independent host approval; no mutation authority is exposed.'};
  }else if(request.method==='ping')result={};
  else if(!ready){error(-32000,'Initialize and send notifications/initialized first');return;}
  else if(request.method==='tools/list')result={tools:toolDefinitions()};
  else if(request.method==='tools/call'){
   try{
    const params=request.params;if(!params||typeof params.name!=='string')throw new Error('Malformed tool request');
    const bridge=await BeastBridge.load(await store.load(),store.options),value=await callTool(bridge,params.name,params.arguments??{});
    if(value?.status==='pending_host_approval')await store.writeProposal(value);
    result={content:[{type:'text',text:JSON.stringify(value)}],structuredContent:{result:value},isError:false};
   }catch(e){result={content:[{type:'text',text:String(e.message)}],isError:true};}
  }else{error(-32601,'Method not supported');return;}
  if(id!==undefined)emit({jsonrpc:'2.0',id,result});
 }
 for await(const chunk of process.stdin){
  buffer+=decoder.decode(chunk,{stream:true});
  while(buffer.includes('\n')){const at=buffer.indexOf('\n'),line=buffer.slice(0,at);buffer=buffer.slice(at+1);if(line.trim())await handle(line);}
  if(Buffer.byteLength(buffer)>MAX_BYTES){emit({jsonrpc:'2.0',id:null,error:{code:-32600,message:'Input exceeds limit'}});process.stdin.destroy();return;}
 }
 if(buffer.trim())await handle(buffer);
}
module.exports={serve};
