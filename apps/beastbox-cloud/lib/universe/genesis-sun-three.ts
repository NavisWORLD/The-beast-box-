// Three.js side of Cory's CodePen sun/light port (see genesis-sun.mjs for provenance). Shaders are copied from
// "Genesis Engine: The Definitive Core" (createStarCorona, createAtmosphere, createStarTexture); the only additions are
// marked ADDED: atmosphere thickness from the recorded planet.atmosphere, and the night-side-only glow map.
import * as THREE from 'three';
import {coronaParams} from './genesis-sun.mjs';
export function starTexture(opaque=false):THREE.CanvasTexture{ // createStarTexture, verbatim; opaque=true paints the corners orange so the sphere's poles are not black (the map is wrapped on a sphere)
  const size=256,c=document.createElement('canvas');c.width=size;c.height=size;const x=c.getContext('2d')!;
  const g=x.createRadialGradient(size/2,size/2,0,size/2,size/2,size/2);
  g.addColorStop(0,'rgba(255,255,255,1)');g.addColorStop(0.2,'rgba(255,255,200,1)');g.addColorStop(0.4,'rgba(255,200,0,1)');g.addColorStop(1,'rgba(255,150,0,0)');
  if(opaque){x.fillStyle='rgb(255,150,0)';x.fillRect(0,0,size,size);}
  x.fillStyle=g;x.fillRect(0,0,size,size);return new THREE.CanvasTexture(c);
}
export function glowTexture():THREE.CanvasTexture{ // soft radial falloff for the universe origin (replaces the map-less flat square sprite)
  const s=128,c=document.createElement('canvas');c.width=s;c.height=s;const x=c.getContext('2d')!;
  const g=x.createRadialGradient(s/2,s/2,0,s/2,s/2,s/2);g.addColorStop(0,'rgba(255,255,255,1)');g.addColorStop(0.25,'rgba(255,255,255,.45)');g.addColorStop(0.6,'rgba(255,255,255,.1)');g.addColorStop(1,'rgba(255,255,255,0)');
  x.fillStyle=g;x.fillRect(0,0,s,s);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;
}
export function coronaMesh(color:THREE.Color,temp:number,size:number):THREE.Mesh{ // createStarCorona, verbatim shader
  const p=coronaParams(temp);
  const mat=new THREE.ShaderMaterial({uniforms:{time:{value:0},baseColor:{value:color},intensity:{value:p.intensity},noiseScale:{value:p.noiseScale}},
    vertexShader:`varying vec3 vPos; varying vec3 vNormal; void main(){ vPos = position; vNormal = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
    fragmentShader:`varying vec3 vPos; varying vec3 vNormal; uniform vec3 baseColor; uniform float intensity; uniform float noiseScale; uniform float time;
      float noise(vec3 p){ return fract(sin(dot(p, vec3(12.9898,78.233,151.7182))) * 43758.5453); }
      float fbm(vec3 p){ float f=0.0; f += 0.5000*noise(p); p*=2.02; f += 0.2500*noise(p+time*0.05); p*=2.03; f += 0.1250*noise(p-time*0.04); return f; }
      void main(){ float rim = pow(1.0 - abs(dot(vNormal, vec3(0.0,0.0,1.0))), 3.0); float n = fbm(vPos * noiseScale); vec3 c = baseColor * (0.6 + 0.6*n) * intensity; gl_FragColor = vec4(c, rim * (0.4 + 0.6*n)); }`,
    blending:THREE.AdditiveBlending,transparent:true,depthWrite:false,side:THREE.BackSide});
  const m=new THREE.Mesh(new THREE.SphereGeometry(size*1.3,48,32),mat);m.userData.isStarCorona=true;return m;
}
export function atmosphereMesh(thick:number):THREE.Mesh{ // createAtmosphere, verbatim shader; radius 1.15 x planet (scaled by its parent mesh)
  const mat=new THREE.ShaderMaterial({uniforms:{time:{value:0},cameraPos:{value:new THREE.Vector3()},lightDir:{value:new THREE.Vector3(0,1,0)},
    betaRay:{value:new THREE.Vector3(5.5e-6,13.0e-6,22.4e-6)},betaMie:{value:new THREE.Vector3(21e-6,21e-6,21e-6)},mieG:{value:0.76},intensityBoost:{value:1},auroraIntensity:{value:0},thick:{value:thick}},
    vertexShader:`varying vec3 vWorldPos; varying vec3 vNormal; void main(){ vNormal = normalize(normalMatrix * normal); vec4 world = modelMatrix * vec4(position, 1.0); vWorldPos = world.xyz; gl_Position = projectionMatrix * viewMatrix * world; }`,
    fragmentShader:`precision highp float; varying vec3 vWorldPos; varying vec3 vNormal; uniform vec3 cameraPos; uniform vec3 lightDir; uniform vec3 betaRay; uniform vec3 betaMie; uniform float mieG; uniform float intensityBoost; uniform float auroraIntensity; uniform float thick;
      float rayleighPhase(float cosTheta){ return 3.0/(16.0*3.14159265) * (1.0 + cosTheta*cosTheta); }
      float hgPhase(float cosTheta, float g){ float g2 = g*g; float denom = pow(1.0 + g2 - 2.0*g*cosTheta, 1.5); return (1.0 - g2) / (4.0*3.14159265*denom); }
      void main(){ vec3 viewDir = normalize(vWorldPos - cameraPos); float mu = dot(viewDir, normalize(lightDir)); float pr = rayleighPhase(mu); float pm = hgPhase(mu, mieG);
        vec3 scatter = betaRay * pr + betaMie * pm; float horizon = clamp(1.0 - abs(vNormal.y), 0.0, 1.0);
        vec3 color = scatter * (0.5 + 0.5*horizon) * intensityBoost * 5.0;
        float aur = smoothstep(0.7, 1.0, horizon) * auroraIntensity; color = mix(color, vec3(0.3, 0.9, 0.7), aur);
        gl_FragColor = vec4(color, 0.9 * (0.7 + 0.3*horizon) * thick); }`, // ADDED: * thick (recorded planet.atmosphere)
    blending:THREE.AdditiveBlending,side:THREE.BackSide,transparent:true,depthWrite:false});
  const m=new THREE.Mesh(new THREE.SphereGeometry(1.15,32,24),mat);m.userData.isAtmosphere=true;return m;
}
// ADDED: the globe's night glow rule (living-world: glow = 1-smoothstep(-.1,.25,dot(n,sun))): the biome glow map shows only
// where the real star is not lighting the ground. uSunV is the direction to the star in view space, set each frame.
export function nightGlowOnly(mat:THREE.MeshStandardMaterial):{value:THREE.Vector3}{
  const u={value:new THREE.Vector3(0,1,0)};
  mat.onBeforeCompile=(sh)=>{sh.uniforms.uSunV=u;
    sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\nuniform vec3 uSunV;')
      .replace('#include <emissivemap_fragment>','#include <emissivemap_fragment>\ntotalEmissiveRadiance *= 1.0 - smoothstep(-0.1, 0.25, dot(normalize(vNormal), uSunV));');};
  mat.customProgramCacheKey=()=>'nightGlowOnly';return u;
}
