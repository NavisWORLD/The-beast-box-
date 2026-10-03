const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto');
const {MAX_BYTES,parseSnapshot,serializeSnapshot,hex}=require('../dist/verifier.js');
async function noLinks(target){
 const absolute=path.resolve(target),root=path.parse(absolute).root;let current=root;
 for(const part of absolute.slice(root.length).split(path.sep)){current=path.join(current,part);try{const s=await fs.lstat(current);if(s.isSymbolicLink())throw new Error('Symlink paths are forbidden');}catch(e){if(e.code!=='ENOENT')throw e;}}
 return absolute;
}
async function privateDirectory(folder){await noLinks(folder);await fs.mkdir(folder,{recursive:true,mode:0o700});await noLinks(folder);}
async function boundedRead(file){await noLinks(file);const fd=await fs.open(file,'r');try{const stat=await fd.stat();if(!stat.isFile()||stat.size>MAX_BYTES)throw new Error('Invalid or oversized file');return await fd.readFile('utf8');}finally{await fd.close();}}
async function exclusiveWrite(file,text){await noLinks(file);const fd=await fs.open(file,'wx',0o600);try{await fd.writeFile(text);await fd.sync();}finally{await fd.close();}}
class FileStore{
 constructor(file,options={}){this.path=path.resolve(file);this.options=options;}
 async load(){return parseSnapshot(await boundedRead(this.path),this.options);}
 async install(snapshot){
  const text=await serializeSnapshot(snapshot,this.options);await privateDirectory(path.dirname(this.path));
  // Exclusive create protects every existing save. An interrupted initial create
  // is rejected as incomplete; no automatic deletion or salvage of user data.
  await exclusiveWrite(this.path,text);
 }
 async compareAndSwap(expectedDigest,snapshot){
  const text=await serializeSnapshot(snapshot,this.options);await noLinks(this.path);
  const lock=this.path+'.lock';await exclusiveWrite(lock,'host-writer\n');let temp;
  try{
   const current=await this.load();if(current.digest!==expectedDigest)throw new Error('Stale snapshot: reload and re-propose');
   const {canonical}=require('../dist/verifier.js');
   if(canonical(current.profile)!==canonical(snapshot.profile)||canonical(current.public_state)!==canonical(snapshot.public_state)||canonical(current.progress)!==canonical(snapshot.progress))throw new Error('Persistent writes cannot replace this Beast or its protected origin');
   if(snapshot.generation<=current.generation||canonical(snapshot.events.slice(0,current.generation))!==canonical(current.events))throw new Error('Persistent writes must append without rewriting or truncating history');
   temp=path.join(path.dirname(this.path),'.'+path.basename(this.path)+'.'+crypto.randomBytes(12).toString('hex')+'.tmp');
   await exclusiveWrite(temp,text);await noLinks(this.path);await fs.rename(temp,this.path);temp=null;
   const dir=await fs.open(path.dirname(this.path),'r');try{await dir.sync();}finally{await dir.close();}
  }finally{if(temp)await fs.unlink(temp).catch(()=>{});await fs.unlink(lock);}
 }
 proposalPath(id){hex(id);return path.join(path.dirname(this.path),'proposals',id+'.json');}
 async writeProposal(proposal){
  const file=this.proposalPath(proposal.proposal_id),folder=path.dirname(file);await privateDirectory(folder);
  const text=JSON.stringify(proposal)+'\n';if(Buffer.byteLength(text)>4096)throw new Error('Proposal exceeds bounded queue record size');
  const lock=folder+'.lock';await exclusiveWrite(lock,'proposal-writer\n');
  try{
   const entries=await fs.readdir(folder);if(entries.length>=64)throw new Error('Pending proposal quota reached; host review is required');
   let bytes=Buffer.byteLength(text);
   for(const entry of entries){
    if(!/^[a-f0-9]{64}\.json$/.test(entry))throw new Error('Unexpected pending queue file');
    const stat=await fs.lstat(path.join(folder,entry));if(!stat.isFile()||stat.isSymbolicLink()||stat.size>4096)throw new Error('Invalid pending queue record');bytes+=stat.size;
   }
   if(bytes>262144)throw new Error('Pending proposal byte quota reached');
   await exclusiveWrite(file,text);return proposal.proposal_id;
  }finally{await fs.unlink(lock);}
 }
 async removeApprovedProposal(id){await noLinks(this.proposalPath(id));await fs.unlink(this.proposalPath(id));}
 async readProposal(id){const {parseStrictJson}=require('../dist/verifier.js');return parseStrictJson(await boundedRead(this.proposalPath(id)));}
}
module.exports={FileStore,boundedRead,noLinks};
