import test from 'node:test';
import assert from 'node:assert/strict';

let runBlobVerification;
try { ({runBlobVerification} = await import('../../../scripts/zeref_cloud_blob_probe.mjs')); } catch {}
const key = Buffer.alloc(64, 17).toString('base64');
const env = extra => ({
  BEASTBOX_BLOB_PROBE_APPROVAL: 'YES_ISOLATED_CREATE_READ_DELETE',
  GITHUB_RUN_ID: '38123456789', GITHUB_RUN_ATTEMPT: '1',
  AZURE_STORAGE_CONTAINER_SAS_URL: 'https://auditacct.blob.core.windows.net/beast-cosmos?sv=2021-08-06&sr=c&sp=rcwdl&se=2099-01-01T00%3A00%3A00Z&sig=private-test-signature',
  ...extra,
});
const run = async options => {
  assert.equal(typeof runBlobVerification, 'function', 'isolated Blob verifier must exist');
  return runBlobVerification(options);
};

// External storage is represented at its HTTP boundary. No cloud account or
// credentials are used by these tests; the actual client constructs requests.
function blobService({uncertainWrite=false, changedReadback=false, deleteDenied=false, conflict=false}={}) {
  const blobs = new Map(), requests = []; let writes=0, readsAfterWrite=0;
  return {blobs, requests, fetch: async (url, options) => {
    const u=new URL(url), name=decodeURIComponent(u.pathname.slice('/beast-cosmos/'.length));
    requests.push({url:u, ...options});
    const h=Object.fromEntries(Object.entries(options.headers).map(([k,v])=>[k.toLowerCase(),v]));
    if(options.method==='GET') {
      if(writes)readsAfterWrite++;
      if(changedReadback && readsAfterWrite===1)blobs.set(name,{text:'foreign replacement',etag:'"foreign"'});
      const item=blobs.get(name);
      return item?new Response(item.text,{status:200,headers:{etag:item.etag}}):new Response('',{status:404});
    }
    if(options.method==='PUT') {
      writes++;
      if(conflict) {
        blobs.set(name,{text:'foreign existing object',etag:'"foreign"'});
        return new Response('<Code>BlobAlreadyExists</Code>',{status:409});
      }
      blobs.set(name,{text:options.body,etag:'"owned"'});
      if(uncertainWrite)throw Error('lost acknowledgement '+url);
      return new Response('',{status:201,headers:{etag:'"owned"'}});
    }
    if(options.method==='DELETE') {
      if(deleteDenied)return new Response('<Code>AuthorizationPermissionMismatch</Code>',{status:403});
      const current=blobs.get(name);
      if(current?.etag!==h['if-match'])return new Response('<Code>ConditionNotMet</Code>',{status:412});
      blobs.delete(name);return new Response(null,{status:202});
    }
    throw Error('Unexpected storage operation');
  }};
}

async function withBlob(service, options) {
  const previous=globalThis.fetch;globalThis.fetch=service.fetch;
  try{return await run(options);}finally{globalThis.fetch=previous;}
}

test('missing credentials report BLOCKED without accessing storage',async()=>{
  const storage=blobService();
  const receipt=await withBlob(storage,{env:env({AZURE_STORAGE_CONTAINER_SAS_URL:''})});
  assert.equal(receipt.status,'BLOCKED');
  assert.equal(receipt.reason,'STORAGE_CREDENTIAL_MISSING');
  assert.equal(receipt.credentials.AZURE_STORAGE_CONTAINER_SAS_URL,false);
  assert.equal(storage.requests.length,0);
});

test('approval and numeric run identity are required before any access',async()=>{
  for(const extra of [{BEASTBOX_BLOB_PROBE_APPROVAL:''},{GITHUB_RUN_ID:'../beasts'},{GITHUB_RUN_ATTEMPT:'0'}]) {
    const storage=blobService();const receipt=await withBlob(storage,{env:env(extra)});
    assert.equal(receipt.status,'BLOCKED');assert.equal(storage.requests.length,0);
  }
});

test('unsafe URLs, expired SAS and missing cleanup permission refuse all writes',async()=>{
  const good=env().AZURE_STORAGE_CONTAINER_SAS_URL;
  for(const url of [good.replace('https:','http:'),good.replace('auditacct.blob.core.windows.net','attacker.invalid'),
    good.replace('sp=rcwdl','sp=rcwl'),good.replace('2099-01-01','2000-01-01'),good.replace('sr=c','sr=b')]) {
    const storage=blobService();const receipt=await withBlob(storage,{env:env({AZURE_STORAGE_CONTAINER_SAS_URL:url})});
    assert.equal(receipt.status,'BLOCKED');assert.equal(storage.requests.length,0);
    assert.ok(!JSON.stringify(receipt).includes('private-test-signature'));
  }
});

test('isolated synthetic object is byte-verified, conditionally deleted, and read back absent',async()=>{
  const storage=blobService();const receipt=await withBlob(storage,{env:env()});
  assert.equal(receipt.status,'PASSED');assert.equal(receipt.readback.sha256_matches,true);
  assert.equal(receipt.cleanup.confirmed_absent,true);assert.equal(storage.blobs.size,0);
  assert.match(receipt.object_name,/^verification\/zeref-cloud\/38123456789-1\/[a-f0-9-]+\.json$/);
  assert.equal(receipt.provider_jobs_submitted,0);assert.equal(receipt.model_calls,0);
  const write=storage.requests.find(r=>r.method==='PUT');
  const del=storage.requests.find(r=>r.method==='DELETE');
  assert.equal(write.headers['If-None-Match'],'*');assert.equal(del.headers['If-Match'],'"owned"');
  assert.ok(storage.requests.every(r=>r.url.pathname==='/beast-cosmos/'+receipt.object_name));
  assert.ok(storage.requests.every(r=>r.redirect==='error'));
  assert.ok(!JSON.stringify(receipt).includes('private-test-signature'));
});

test('ambiguous write acknowledgement is reported honestly and reconciled before cleanup',async()=>{
  const storage=blobService({uncertainWrite:true});const receipt=await withBlob(storage,{env:env()});
  assert.equal(receipt.status,'FAILED');assert.equal(receipt.reason,'WRITE_NOT_ACKNOWLEDGED');
  assert.equal(receipt.cleanup.confirmed_absent,true);assert.equal(storage.blobs.size,0);
  assert.ok(!JSON.stringify(receipt).includes('private-test-signature'));
  assert.ok(!JSON.stringify(receipt).includes('https://'));
});

test('create-only conflict never deletes an object owned by someone else',async()=>{
  const storage=blobService({conflict:true});const receipt=await withBlob(storage,{env:env()});
  assert.equal(receipt.status,'BLOCKED');assert.equal(receipt.reason,'CREATE_CONFLICT');
  assert.equal(storage.blobs.size,1);assert.equal(storage.requests.filter(r=>r.method==='DELETE').length,0);
});

test('changed readback is not deleted and cannot be reported as passed',async()=>{
  const storage=blobService({changedReadback:true});const receipt=await withBlob(storage,{env:env()});
  assert.equal(receipt.status,'CLEANUP_FAILED');assert.equal(receipt.cleanup.reason,'OBJECT_CHANGED_REFUSING_DELETE');
  assert.equal(storage.blobs.size,1);assert.equal(storage.requests.filter(r=>r.method==='DELETE').length,0);
});

test('delete rejection is a cleanup failure with sanitized Azure status and code',async()=>{
  const storage=blobService({deleteDenied:true});const receipt=await withBlob(storage,{env:env()});
  assert.equal(receipt.status,'CLEANUP_FAILED');assert.equal(receipt.cleanup.confirmed_absent,false);
  assert.equal(receipt.cleanup.error.http_status,403);
  assert.equal(receipt.cleanup.error.azure_code,'AuthorizationPermissionMismatch');
  assert.equal(storage.blobs.size,1);assert.ok(!JSON.stringify(receipt).includes('private-test-signature'));
});

test('existing connection-string credentials use the same isolated lifecycle without exposing key',async()=>{
  const storage=blobService();const receipt=await withBlob(storage,{env:env({
    AZURE_STORAGE_CONTAINER_SAS_URL:'',
    AZURE_STORAGE_CONNECTION_STRING:`DefaultEndpointsProtocol=https;AccountName=auditacct;AccountKey=${key};EndpointSuffix=core.windows.net`,
  })});
  assert.equal(receipt.status,'PASSED');assert.equal(receipt.credential_mode,'key');
  assert.equal(receipt.credentials.AZURE_STORAGE_CONNECTION_STRING,true);assert.equal(storage.blobs.size,0);
  assert.ok(!JSON.stringify(receipt).includes(key));
});
