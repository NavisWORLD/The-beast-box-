/** True when WebGL runs on a CPU rasteriser (CI SwiftShader, llvmpipe, GPU-less VMs). Probed on a throwaway context so callers
 *  can pick antialias / pixel ratio / model tier BEFORE creating their renderer. Cached per page. */
let cached:boolean|null=null;
export function isSoftwareGL():boolean{if(cached!==null)return cached;cached=false;
 try{const c=document.createElement('canvas');const g=(c.getContext('webgl2')||c.getContext('webgl')) as WebGLRenderingContext|null;
  if(g){const d=g.getExtension('WEBGL_debug_renderer_info');cached=!!d&&/swiftshader|llvmpipe|software/i.test(String(g.getParameter(d.UNMASKED_RENDERER_WEBGL)));g.getExtension('WEBGL_lose_context')?.loseContext();}}catch{}
 return cached;}
