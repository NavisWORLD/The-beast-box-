// Speckle / black debris. The sources that paint the live frame sit in lib/universe and are not edited.
export const SPECKLE_STOP=Object.freeze({
 stopped:true,
 files:[
  'lib/universe/one-world-look.ts',
  'lib/universe/landforms-three.ts',
  'lib/universe/flashes-three.ts',
  'lib/universe/planet-body-three.ts',
 ],
 reason:'Colored speckle and black debris come from lib/universe: terrain and sky shaders dither after an sRGB encode with toneMapped off, landforms star points write alpha 1 without size attenuation, and flash points use sizeAttenuation:false. Those files stay read-only. Genesis materials do not add that pattern.',
});

/** Round point sprite so a Genesis point does not draw a hard square. */
export function roundPointTexture(THREE:typeof import('three')){
 if(typeof document==='undefined')return null;
 const c=document.createElement('canvas');c.width=c.height=32;
 const g=c.getContext('2d');
 if(g){
  const grd=g.createRadialGradient(16,16,0,16,16,16);
  grd.addColorStop(0,'rgba(255,255,255,1)');
  grd.addColorStop(.45,'rgba(255,255,255,.65)');
  grd.addColorStop(1,'rgba(255,255,255,0)');
  g.fillStyle=grd;g.fillRect(0,0,32,32);
 }
 const t=new THREE.CanvasTexture(c);t.needsUpdate=true;return t;
}

/** Genesis points: size attenuates, the sprite is a straight-alpha circle, the renderer tonemaps before its dither. */
export function genesisPoints(THREE:typeof import('three'),color=0xdde6ff,size=1.4){
 const map=roundPointTexture(THREE);
 return new THREE.PointsMaterial({
  color,size,sizeAttenuation:true,transparent:true,opacity:.9,depthWrite:false,alphaTest:.15,
  ...(map?{map}:{}),
 });
}
