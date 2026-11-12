// PUBLIC STATUS CORS — one narrowly scoped cross-origin caller for
// read-only public status routes (currently GET /api/cosmos/liveness).
// Zeref's profile card on GitHub Pages (https://navisworld.github.io)
// may read the JSON. Everything else stays same-origin: no wildcard,
// no credentials, GET/HEAD/OPTIONS only. This is separate from the
// guest-door CORS (POST + Content-Type only) and grants no write path.
export const PUBLIC_STATUS_CORS_ORIGINS=Object.freeze(['https://navisworld.github.io']);

/** The allowlisted origin exactly as sent, or null (absent, mismatched case/scheme/port, or anything else). */
export function publicStatusCorsOrigin(origin){
 return typeof origin==='string'&&PUBLIC_STATUS_CORS_ORIGINS.includes(origin)?origin:null;
}

/** Adds the read grant for an allowlisted origin to a status response (no-op otherwise). */
export function withPublicStatusCors(response,origin){
 const allowed=publicStatusCorsOrigin(origin);
 if(allowed){
  response.headers.set('Access-Control-Allow-Origin',allowed);
  response.headers.append('Vary','Origin');
 }
 return response;
}

/** Preflight: 204 with the narrow GET grant for an allowlisted origin, 403 with no grant otherwise. */
export function publicStatusCorsPreflight(origin){
 const allowed=publicStatusCorsOrigin(origin);
 if(!allowed)return new Response(null,{status:403,headers:{'Cache-Control':'no-store',Vary:'Origin'}});
 return new Response(null,{status:204,headers:{
  'Access-Control-Allow-Origin':allowed,
  'Access-Control-Allow-Methods':'GET, HEAD, OPTIONS',
  'Access-Control-Max-Age':'600',
  'Cache-Control':'no-store',
  Vary:'Origin'}});
}
