// P1 post shaders. Technique from GENESIS X (GODRAY_SHADER, OPTICS_SHADER), rewritten for the one-sun chain:
// - god rays ADD to the frame (final = base + rays * exposure * sunVisible); GENESIS X multiplied the whole frame, which dimmed it
//   and went black at sunset. The rays only gather pixels above the bright gate, so they come from the sun disc, never the companion
//   disc (which is dim by design) and never from grass.
// - optics grain is seeded per frame (uGrainSeed from a hashed frame counter), not from a random call.
export const GOD_RAYS_FRAG=(samples)=>`
uniform sampler2D tDiffuse;uniform vec2 uSunPos;uniform float uDensity,uDecay,uWeight,uExposure,uSunVisible;uniform vec2 uGate;varying vec2 vUv;
void main(){vec4 base=texture2D(tDiffuse,vUv);if(uSunVisible<=0.0){gl_FragColor=base;return;}
 vec2 tc=vUv;vec2 dt=(vUv-uSunPos)*(1.0/${samples.toFixed(1)})*uDensity;float decay=1.0;vec3 rays=vec3(0.0);
 for(int i=0;i<${Math.max(1,samples|0)};i++){tc-=dt;vec3 s=texture2D(tDiffuse,clamp(tc,0.0,1.0)).rgb;float l=dot(s,vec3(0.2126,0.7152,0.0722));
  rays+=s*smoothstep(uGate.x,uGate.y,l)*decay*uWeight;decay*=uDecay;}
 gl_FragColor=vec4(base.rgb+rays*uExposure*uSunVisible,base.a);}`;
export const OPTICS_FRAG=`
uniform sampler2D tDiffuse;uniform float uAberration,uGrain,uVignette,uEdgeBlur,uGamma,uGrainSeed;varying vec2 vUv;
float h(vec2 p){p=fract(p*vec2(443.897,441.423)+uGrainSeed*17.0);p+=dot(p,p.yx+19.19);return fract((p.x+p.y)*p.x);}
void main(){vec2 c=vUv-0.5;float d=length(c);float ab=uAberration*0.02*(1.0+d);
 vec3 col;col.r=texture2D(tDiffuse,vUv+c*ab).r;col.g=texture2D(tDiffuse,vUv).g;col.b=texture2D(tDiffuse,vUv-c*ab).b;
 if(uEdgeBlur>0.0){float b=smoothstep(0.25,0.75,d)*uEdgeBlur*0.01;col=(col+texture2D(tDiffuse,vUv+vec2(b,0.0)).rgb+texture2D(tDiffuse,vUv-vec2(b,0.0)).rgb+texture2D(tDiffuse,vUv+vec2(0.0,b)).rgb)/4.0;}
 col*=mix(1.0,smoothstep(0.85,0.2,d*1.2),uVignette);col+=(h(vUv)-0.5)*uGrain*max(0.15,dot(col,vec3(0.33)));
 col=pow(max(col,0.0),vec3(1.0/max(0.01,uGamma)));gl_FragColor=vec4(col,1.0);}`;
export const PASS_VERT='varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}';
