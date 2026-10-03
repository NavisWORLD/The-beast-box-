const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
test('extracted canonical profile and GBA encoders retain pinned original bytes',()=>{
 const root=path.resolve(__dirname,'..'),record=require('../CANONICAL_SOURCE.json');
 for(const entry of record.files){
  const extracted=fs.readFileSync(path.join(root,entry.extracted));assert.equal(crypto.createHash('sha256').update(extracted).digest('hex'),entry.sha256);
  const original=path.resolve(root,'../..',entry.original);if(fs.existsSync(original))assert.deepEqual(extracted,fs.readFileSync(original),'Canonical code drift: '+entry.original);
 }
});
