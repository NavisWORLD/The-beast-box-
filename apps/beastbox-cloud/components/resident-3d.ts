/**
 * True-3D artist residents (Frostmitt, Nyxbean): a visual-hull mesh carved from Cory's turntable
 * reference (front / side / back silhouettes) with those same three views projected back onto it,
 * so each resident keeps its own art from every angle. Artist-drawn: no quantum seed.
 * Assets: public/residents3d/<id>/{mesh.bin,meta.json,front.png,side.png,back.png}
 */
type T=typeof import('three');
export const RESIDENTS_3D=Object.freeze(['art-frostmitt','art-nyxbean']);
type Rect={u0:number;u1:number;v0:number;v1:number;flip:boolean};
export function loadResident3D(THREE:T,id:string):Promise<import('three').Mesh|null>{
 if(!RESIDENTS_3D.includes(id))return Promise.resolve(null);
 const base=`/residents3d/${id}/`;
 // One loader per request: a shared FileLoader's responseType would race between json and binary.
 const get=(f:string,type:'json'|'arraybuffer')=>new Promise<any>((ok,no)=>{const files=new THREE.FileLoader();files.setResponseType(type==='json'?'text':'arraybuffer');files.load(base+f,d=>ok(type==='json'?JSON.parse(String(d)):d),undefined,no);});
 const tl=new THREE.TextureLoader();const tex=(f:string)=>new Promise<import('three').Texture>((ok,no)=>tl.load(base+f,t=>{t.colorSpace=THREE.SRGBColorSpace;ok(t);},undefined,no));
 return Promise.all([get('meta.json','json'),get('mesh.bin','arraybuffer'),tex('front.png'),tex('side.png'),tex('back.png')]).then(([meta,buf,tF,tS,tB])=>{
  const n=meta.vertices,P=new Float32Array(buf,0,n*3),N=new Float32Array(buf,n*12,n*3);
  const I=meta.index==='u16'?new Uint16Array(buf,n*24,meta.triangles*3):new Uint32Array(buf,n*24,meta.triangles*3);
  // Marching cubes emits clockwise triangles here; rewind them so front-face culling keeps the near surface.
  for(let t=0;t<I.length;t+=3){const k=I[t+1];I[t+1]=I[t+2];I[t+2]=k;}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(P,3));g.setAttribute('normal',new THREE.BufferAttribute(N,3));g.setIndex(new THREE.BufferAttribute(I,1));
  const r=(v:Rect)=>new THREE.Vector4(v.u0,v.u1,v.v0,v.v1);const V=meta.views as Record<string,Rect>;
  const mat=new THREE.ShaderMaterial({toneMapped:false,fog:false,uniforms:{tF:{value:tF},tS:{value:tS},tB:{value:tB},rF:{value:r(V.front)},rS:{value:r(V.side)},rB:{value:r(V.back)},sideFlip:{value:V.side.flip?1:0}},
   vertexShader:'varying vec3 vP;varying vec3 vN;void main(){vP=position;vN=normal;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
   fragmentShader:'uniform sampler2D tF;uniform sampler2D tS;uniform sampler2D tB;uniform vec4 rF;uniform vec4 rS;uniform vec4 rB;uniform float sideFlip;varying vec3 vP;varying vec3 vN;'+
    'vec4 at(sampler2D t,vec4 r,float u){vec2 uv=vec2((u-r.x)/(r.y-r.x),(vP.y-r.z)/(r.w-r.z));return texture2D(t,clamp(uv,0.0,1.0));}'+
    'void main(){vec3 n=normalize(vN);float wf=pow(max(n.z,0.0),3.0),wb=pow(max(-n.z,0.0),3.0),ws=pow(abs(n.x),3.0);'+
    'vec4 f=at(tF,rF,vP.x),b=at(tB,rB,-vP.x),s=at(tS,rS,sideFlip>.5?-vP.z:vP.z);'+
    'float a=wf*f.a+wb*b.a+ws*s.a+1e-4;vec3 c=(f.rgb*wf*f.a+b.rgb*wb*b.a+s.rgb*ws*s.a)/a;gl_FragColor=vec4(c*1.08,1.0);\n#include <colorspace_fragment>\n}'});
  const m=new THREE.Mesh(g,mat);m.name=id+'-3d';return m;
 }).catch(()=>null);
}
