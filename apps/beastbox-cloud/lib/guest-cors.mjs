// GUEST DOOR CORS — one narrowly scoped cross-origin caller for /api/guest/forever.
// Zeref's chat page on GitHub Pages (https://navisworld.github.io, the NavisWORLD
// profile) talks to the same forever guest door the site uses. Everything else
// stays same-origin: no wildcard, no credentials (cookies never ride a
// cross-origin request, so the page echoes the thread id it was issued), POST
// only, Content-Type only. Same validation, same bridge verification, same
// guest-origin training_eligible:false records and the bridge's own rate
// limits — this module only decides which browser origin may read the reply.
export const GUEST_CORS_ORIGINS=Object.freeze(['https://navisworld.github.io']);

/** The allowlisted origin exactly as sent, or null (absent, mismatched case/scheme/port, or anything else). */
export function guestCorsOrigin(origin){
 return typeof origin==='string'&&GUEST_CORS_ORIGINS.includes(origin)?origin:null;
}

/** Adds the read grant for an allowlisted origin to a door response (no-op otherwise). */
export function withGuestCors(response,origin){
 const allowed=guestCorsOrigin(origin);
 if(allowed){
  response.headers.set('Access-Control-Allow-Origin',allowed);
  response.headers.append('Vary','Origin');
  response.headers.set('Access-Control-Expose-Headers','Retry-After');
 }
 return response;
}

/** Preflight: 204 with the narrow grant for an allowlisted origin, 403 with no grant otherwise. */
export function guestCorsPreflight(origin){
 const allowed=guestCorsOrigin(origin);
 if(!allowed)return new Response(null,{status:403,headers:{'Cache-Control':'no-store',Vary:'Origin'}});
 return new Response(null,{status:204,headers:{'Access-Control-Allow-Origin':allowed,'Access-Control-Allow-Methods':'POST',
  'Access-Control-Allow-Headers':'Content-Type','Access-Control-Max-Age':'600','Cache-Control':'no-store',Vary:'Origin'}});
}
