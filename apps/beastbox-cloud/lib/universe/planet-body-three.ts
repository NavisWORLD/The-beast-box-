// A /universe planet built the way the pocket globe is built: a displaced, normal-mapped, sun-lit ground sphere with ocean depth,
// glint and foam, a night glow, cloud shell + cloud shadow and an atmosphere rim, using Cosmo's planets pack (public/universe/planets,
// shaders generated from the pack's glsl). One light only: the real star (direction + colour + Cory's inverse-square falloff).
// LOD per ZOOM_GUIDE.md: point sprite -> far mesh (512 maps) -> near mesh (2048 maps, displaced) -> (ground handoff: next PR).
import * as THREE from 'three';
import {PLANET_VERT,PLANET_FRAG,CLOUD_FRAG,ATMO_VERT,ATMO_FRAG} from './planet-glsl';
import {PLANET_SHADING} from './planet-shading.mjs';
import {SPRITE_TINT,planetLod,glowSet} from './planet-types.mjs';

const BASE='/universe/planets/';
type TexSet={albedo:THREE.Texture;normal:THREE.Texture;rough:THREE.Texture;height:THREE.Texture;ocean:THREE.Texture;emissive:THREE.Texture;clouds:THREE.Texture;ready:boolean};
export type PlanetCtx={t:number;cam:THREE.PerspectiveCamera;sunPos:THREE.Vector3;sunColor:THREE.Color;exposure:number;viewH:number;glow:string};
export function createPlanetKit(){
  const tl=new THREE.TextureLoader();const sets=new Map<string,TexSet>();
  const blank=new THREE.DataTexture(new Uint8Array([0,0,0,255]),1,1);blank.needsUpdate=true;
  const wave=tl.load(BASE+'water_normal_1024.png');wave.wrapS=wave.wrapT=THREE.RepeatWrapping;wave.flipY=false;
  const glows=new Map<string,THREE.Texture>();
  const glowTex=(n:string)=>{let g=glows.get(n);if(!g){g=tl.load(BASE+`star_glow_${n}_256.png`);g.colorSpace=THREE.SRGBColorSpace;glows.set(n,g);}return g;};
  const mk=(file:string,srgb:boolean,opt?:{noMip?:boolean})=>{const t=tl.load(BASE+file);t.flipY=false;t.wrapS=THREE.RepeatWrapping;if(srgb)t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=4;
    if(opt?.noMip){t.generateMipmaps=false;t.minFilter=THREE.LinearFilter;} // cloud map: no mipmaps or the atan seam shows (pack note)
    return t;};
  function getSet(type:string,res:'512x256'|'2048x1024'):TexSet{const key=type+res;let s=sets.get(key);if(s)return s;
    const f=(k:string,ext='webp')=>`${type}_${k}_${res}.${ext}`;const moon=type==='moon';
    const set:TexSet={albedo:mk(f('albedo'),true),normal:mk(f('normal'),false),rough:mk(f('roughness'),false),height:mk(f('height'),false),
      ocean:moon?blank:mk(f('ocean_mask'),false),emissive:mk(f('emissive'),true),clouds:mk(f('clouds'),false,{noMip:true}),ready:false};
    // ready once the albedo (the last thing the eye needs) is in; the rest stream in within the same frame budget
    const img:any=set.albedo;const poll=()=>{if(set.albedo.image&&(set.albedo.image as any).width){set.ready=true;}else setTimeout(poll,100);};poll();
    sets.set(key,set);return s=set;}
  const flipV=(g:THREE.SphereGeometry)=>{const uv=g.attributes.uv;for(let i=0;i<uv.count;i++)uv.setY(i,1-uv.getY(i));return g;}; // v=0 at the north pole, as the pack's shaders expect
  const geoFar=flipV(new THREE.SphereGeometry(1,64,32)),geoNear=flipV(new THREE.SphereGeometry(1,160,80)),geoShell=new THREE.SphereGeometry(1,48,32);
  function uniformsFor(type:string,set:TexSet,near:boolean){const S=PLANET_SHADING[type],sh=S.shading,moon=!!sh.is_moon;
    const v3=(a:number[])=>new THREE.Vector3(a[0],a[1],a[2]);
    return{uAlbedo:{value:set.albedo},uNormal:{value:set.normal},uRough:{value:set.rough},uOceanMask:{value:set.ocean},uEmissive:{value:set.emissive},uClouds:{value:set.clouds},uWaveNormal:{value:wave},
      uHeight:{value:set.height},uDisp:{value:near?1:0},uHasHeight:{value:near?1:0},uSea:{value:moon?0.5:0.25},
      uSunDir:{value:new THREE.Vector3(1,0,0)},uSunDirObj:{value:new THREE.Vector3(1,0,0)},uSunColor:{value:new THREE.Vector3(1,1,1)},uPlanetCenter:{value:new THREE.Vector3()},
      uAtmo:{value:sh.atmo_amount},uSkyColor:{value:v3(sh.sky_color)},uTwilightColor:{value:v3(sh.twilight_color)},uShallow:{value:v3(sh.shallow_color)},uDeep:{value:v3(sh.deep_color)},
      uCloudAlt:{value:S.clouds?.altitude_frac??0},uCloudShadow:{value:near&&S.clouds?S.clouds.shadow_strength:0},uCloudOn:{value:!near&&S.clouds?1:0},
      uNightLights:{value:sh.night_lights},uEmissiveDayKeep:{value:sh.emissive_day_keep},uGlintRough:{value:sh.glint_roughness},uWaveStrength:{value:sh.wave_strength},uTime:{value:0},uIsMoon:{value:moon?1:0},
      uParentDir:{value:new THREE.Vector3(0,1,0)},uParentTint:{value:new THREE.Vector3(0.6,0.7,1)},uEarthshine:{value:sh.earthshine},uAlpha:{value:1}};}
  function create(type:string,variant:{lonDeg:number;tiltDeg:number;spinDegPerS:number;cloudLonDeg:number}){
    const S=PLANET_SHADING[type];const far=getSet(type,'512x256');let near:TexSet|null=null;
    const farMat=new THREE.ShaderMaterial({uniforms:uniformsFor(type,far,false),vertexShader:PLANET_VERT,fragmentShader:PLANET_FRAG,transparent:true,depthWrite:true});
    const mesh=new THREE.Mesh(geoFar,farMat);mesh.rotation.order='ZYX';mesh.userData.planetType=type;
    let nearMesh:THREE.Mesh|null=null,cloudMesh:THREE.Mesh|null=null;
    const makeNear=()=>{near=getSet(type,'2048x1024');
      const m=new THREE.ShaderMaterial({uniforms:uniformsFor(type,near,true),vertexShader:PLANET_VERT,fragmentShader:PLANET_FRAG,transparent:true,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-2,polygonOffsetUnits:-2});
      nearMesh=new THREE.Mesh(geoNear,m);nearMesh.renderOrder=1;nearMesh.visible=false;mesh.add(nearMesh);
      if(S.clouds){const cm=new THREE.ShaderMaterial({uniforms:{uClouds:{value:near.clouds},uSunDir:m.uniforms.uSunDir,uSunColor:m.uniforms.uSunColor,uSkyColor:m.uniforms.uSkyColor,uTwilightColor:m.uniforms.uTwilightColor,uAtmo:m.uniforms.uAtmo,uAlpha:{value:1}},
        vertexShader:'varying vec2 vUv; varying vec3 vWorldN; varying vec3 vWorldPos; void main(){ vUv=uv; vWorldN=normalize(mat3(modelMatrix)*normal); vec4 w=modelMatrix*vec4(position,1.0); vWorldPos=w.xyz; gl_Position=projectionMatrix*viewMatrix*w; }',
        fragmentShader:CLOUD_FRAG,transparent:true,depthWrite:false});
        cloudMesh=new THREE.Mesh(geoNear,cm);cloudMesh.scale.setScalar(1+S.clouds.altitude_frac);cloudMesh.renderOrder=2;cloudMesh.visible=false;mesh.add(cloudMesh);}};
    // atmosphere rim shell (additive, analytic path length)
    let atmo:THREE.Mesh|null=null;
    if(S.atmosphere){const U=S.atmosphere;const am=new THREE.ShaderMaterial({uniforms:{uPlanetCenter:{value:new THREE.Vector3()},uPlanetR:{value:1},uShellR:{value:S.shell||1.045},uSunDir:{value:new THREE.Vector3(1,0,0)},uSunColor:{value:new THREE.Vector3(1,1,1)},
      uSkyColor:{value:new THREE.Vector3(...(U.uSkyColor as [number,number,number]))},uTwilightColor:{value:new THREE.Vector3(...(U.uTwilightColor as [number,number,number]))},uDensity:{value:U.uDensity},uMie:{value:U.uMie},uOpacity:{value:0}},
      vertexShader:ATMO_VERT,fragmentShader:ATMO_FRAG,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false});
      atmo=new THREE.Mesh(geoShell,am);atmo.scale.setScalar(S.shell||1.045);atmo.renderOrder=3;atmo.visible=false;mesh.add(atmo);}
    // far point sprite (star_glow tinted by the type's mean albedo)
    const tint=SPRITE_TINT[type];const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTex('white'),color:new THREE.Color(tint[0],tint[1],tint[2]),blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,sizeAttenuation:false}));mesh.add(sprite);
    const v=new THREE.Vector3(),inv=new THREE.Matrix4(),sd=new THREE.Vector3(),cen=new THREE.Vector3();
    function setSun(u:any,mesh_:THREE.Object3D,ctx:PlanetCtx,dirW:THREE.Vector3,col:THREE.Vector3){u.uSunDir.value.copy(dirW);u.uSunColor.value.copy(col);u.uPlanetCenter.value.copy(cen);
      inv.copy(mesh_.matrixWorld).invert();u.uSunDirObj.value.copy(dirW).transformDirection(inv);}
    function update(ctx:PlanetCtx){
      const R=mesh.scale.x;mesh.getWorldPosition(cen);const d=ctx.cam.position.distanceTo(cen);const lod=planetLod(d,R,ctx.cam.fov);
      mesh.rotation.set(0,(variant.lonDeg+variant.spinDegPerS*ctx.t)*Math.PI/180,variant.tiltDeg*Math.PI/180);mesh.updateMatrixWorld(true);
      sd.copy(ctx.sunPos).sub(cen).normalize();
      // the star is the only light: Cory's blackbody colour, 35% toward white for the light (sun_light_recipe), x1.25, x inverse-square exposure
      const c=ctx.sunColor,k=1.25*ctx.exposure;const col=v.set(c.r+(1-c.r)*0.35,c.g+(1-c.g)*0.35,c.b+(1-c.b)*0.35).multiplyScalar(k).clone();
      if(lod.s>0.2&&!nearMesh)makeNear();
      const u=farMat.uniforms;setSun(u,mesh,ctx,sd,col);u.uTime.value=ctx.t;
      const farReady=far.ready;u.uAlpha.value=farReady?lod.farAlpha:0;farMat.depthWrite=lod.farAlpha>0.5;farMat.transparent=lod.farAlpha<0.999;
      const nearOn=!!nearMesh&&near!.ready&&lod.nearAlpha>0.002;
      if(nearMesh){nearMesh.visible=nearOn;if(nearOn){const nu=(nearMesh.material as THREE.ShaderMaterial).uniforms;setSun(nu,nearMesh,ctx,sd,col);nu.uTime.value=ctx.t;nu.uAlpha.value=lod.nearAlpha;(nearMesh.material as THREE.ShaderMaterial).depthWrite=lod.nearAlpha>0.99;}}
      if(cloudMesh){cloudMesh.visible=nearOn;if(nearOn){cloudMesh.rotation.y=(variant.cloudLonDeg-variant.lonDeg+(S.clouds.rotation_deg_per_min/60)*ctx.t)*Math.PI/180;cloudMesh.updateMatrixWorld(true);
        const cu=(cloudMesh.material as THREE.ShaderMaterial).uniforms;cu.uSunDir.value.copy(sd);cu.uSunColor.value.copy(col);cu.uAlpha.value=lod.nearAlpha;}}
      if(atmo){const au=(atmo.material as THREE.ShaderMaterial).uniforms;const on=lod.atmo>0.002;atmo.visible=on;if(on){au.uPlanetCenter.value.copy(cen);au.uPlanetR.value=R;au.uShellR.value=R*(S.shell||1.045);au.uSunDir.value.copy(sd);au.uSunColor.value.copy(col);au.uOpacity.value=lod.atmo;
        (atmo.material as THREE.ShaderMaterial).side=d<R*(S.shell||1.045)?THREE.BackSide:THREE.FrontSide;}}
      sprite.visible=lod.sprite>0.002||!farReady;(sprite.material as THREE.SpriteMaterial).opacity=farReady?lod.sprite:1;
      const px=9;sprite.scale.setScalar(px/Math.max(1,ctx.viewH)*2*Math.tan(ctx.cam.fov*Math.PI/360)/Math.max(1e-6,R));
      mesh.userData.lod=lod;
    }
    return{mesh,update};
  }
  return{create,glowTex};
}
