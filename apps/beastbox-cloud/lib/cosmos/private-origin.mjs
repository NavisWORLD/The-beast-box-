/** Next may canonicalize its internal request hostname to localhost.
 * The actual Host header identifies the browser-facing origin. Forwarded Host
 * and client owner fields never grant authority; cookies remain signed/server-only.
 */
export function samePrivateOrigin(req){
 try{
  const raw=req.headers.get('origin');if(!raw)return false;
  const origin=new URL(raw),request=new URL(req.url),host=req.headers.get('host');
  if(origin.origin!==raw||origin.protocol!==request.protocol)return false;
  if(host){const actual=new URL(request.protocol+'//'+host);if(actual.host!==host.toLowerCase()||actual.pathname!=='/'||actual.username||actual.password||actual.search||actual.hash)return false;return origin.host===actual.host;}
  return origin.origin===request.origin;
 }catch{return false;}
}
