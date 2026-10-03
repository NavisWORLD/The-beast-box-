#!/usr/bin/env node
const fs=require('node:fs/promises'),path=require('node:path');
const core=require('../dist'),{FileStore,boundedRead,noLinks}=require('./file-store.cjs');
async function main(){
 const args=process.argv.slice(2),command=args.shift();
 function flag(name,fallback){const i=args.indexOf('--'+name);if(i<0)return fallback;if(i+1>=args.length)throw new Error('Missing --'+name+' value');const value=args[i+1];args.splice(i,2);return value;}
 const storePath=flag('store',path.join(process.cwd(),'quantum-beast-state','beast.qbeast')),trustedPublicKey=flag('trust-key',undefined);
 const store=new FileStore(storePath,trustedPublicKey?{trustedPublicKey}:{});
 let result;
 switch(command){
  case 'create':{const seed=args.shift();if(!seed)throw new Error('create requires a public seed');const family=flag('family',undefined),output=flag('output','beast.qbeast');const snapshot=await core.createSnapshot(core.generateCreature(seed,family));await noLinks(output);await fs.writeFile(output,await core.serializeSnapshot(snapshot),{flag:'wx',mode:0o600});result={file:path.resolve(output),...(await core.verifySnapshot(snapshot))};break;}
  case 'install':{const file=args.shift();if(!file)throw new Error('install requires beast.qbeast');const snapshot=await core.parseSnapshot(await boundedRead(file),store.options);await store.install(snapshot);result={installed:store.path,...(await core.verifySnapshot(snapshot,store.options))};break;}
  case 'verify':{const snapshot=args[0]?await core.parseSnapshot(await boundedRead(args[0]),store.options):await store.load();result=await core.verifySnapshot(snapshot,store.options);break;}
  case 'mcp':return require('./mcp.cjs').serve(store);
  case 'discard':{const id=args.shift();if(!id)throw new Error('discard requires a reviewed pending proposal ID');await store.removeApprovedProposal(id);result={discarded:id,lineage_changed:false};break;}
  case 'call':{const name=args.shift(),{parseStrictJson}=require('../dist/verifier.js'),{callTool}=require('../dist/tools.js');const value=await callTool(await core.BeastBridge.load(await store.load(),store.options),name,parseStrictJson(args.shift()??'{}'));if(value?.status==='pending_host_approval')await store.writeProposal(value);result=value;break;}
  case 'approve':{const id=args.shift(),kind=flag('kind',undefined),publicFlag=args.includes('--public');if(!id||!kind||!publicFlag)throw new Error('Host approval requires proposal ID, --kind message|action|memory and explicit --public after reviewing the proposal');const current=await store.load(),proposal=await store.readProposal(id),next=await core.approveProposal(current,proposal,{allow:[kind],public_memory:true},store.options);if(current.signature||current.public_state.mode!=='unavailable'||Object.values(current.progress).some(x=>x!==0))throw new Error('Signed host state must be updated through the host signing API; CLI never strips its attestation');await store.compareAndSwap(current.digest,next);let pending_cleanup='removed';try{await store.removeApprovedProposal(id);}catch{pending_cleanup='retained; approval is committed, host may discard the stale queue file';}result={approved:id,lineage_head:next.lineage_head,digest:next.digest,pending_cleanup};break;}
  case 'export':{const output=flag('output','beast.qbeast');await noLinks(output);await fs.writeFile(output,await core.serializeSnapshot(await store.load(),store.options),{flag:'wx',mode:0o600});result={file:path.resolve(output)};break;}
  case 'export-gba':{const output=flag('output','beast-gba.zip'),pack=await core.exportGba(await store.load(),store.options);await noLinks(output);await fs.writeFile(output,pack.zip,{flag:'wx',mode:0o600});result={file:path.resolve(output),sha256:pack.sha256};break;}
  default:throw new Error('Commands: create SEED, install FILE, verify [FILE], mcp, call TOOL JSON, approve ID --kind KIND --public, discard ID, export, export-gba. Optional --store FILE and --trust-key HEX. Outputs use exclusive create.');
 }
 process.stdout.write(JSON.stringify(result,null,2)+'\n');
}
main().catch(e=>{process.stderr.write('Quantum Beast: '+e.message+'\n');process.exitCode=1;});
