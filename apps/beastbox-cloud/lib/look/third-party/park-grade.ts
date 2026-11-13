/*
 * THIRD-PARTY (MIT) — technique ported from pallet-town-3d by Paulius, src/core/PostFX.ts (the Grade pass:
 * lift/gain split tone, contrast + saturation, highlight rolloff, vignette) and its SMAA-last ordering.
 * Copyright (c) 2026 Paulius. Licensed under the MIT License; see apps/beastbox-cloud/THIRD_PARTY_NOTICES.md.
 * Changes for The Beast Box: runs after our OutputPass (ACES stays the one tone map, in the OutputPass), so it grades
 * display-referred colour with gentler numbers; no grain here (our optics pass already has seeded grain); tier-scaled.
 * Label: SEEDED look, a designed screen grade (not a camera or physics model).
 */
export const PARK_GRADE_LABEL='Screen grade · third-party technique (pallet-town-3d, MIT) · designed';

/** Per tier: LOW none (no post chain at all), MED grade only, HIGH/GOD grade + SMAA. */
export function parkGradeBudget(tier:string){
 if(tier==='LOW')return {grade:false,smaa:false,contrast:1,saturation:1,vignette:0};
 if(tier==='MED')return {grade:true,smaa:false,contrast:1.03,saturation:1.04,vignette:.14};
 return {grade:true,smaa:true,contrast:1.05,saturation:1.07,vignette:.2};
}

export const PARK_GRADE_FRAG=`uniform sampler2D tDiffuse;uniform float uContrast,uSaturation,uVignette;uniform vec3 uLift,uGain;varying vec2 vUv;
float luma(vec3 c){return dot(c,vec3(.2126,.7152,.0722));}
void main(){vec4 t=texture2D(tDiffuse,vUv);vec3 c=t.rgb;
 float l=luma(c);
 c+=uLift*(1.0-smoothstep(0.0,.55,l));                 /* cool lift in the shadows */
 c*=mix(vec3(1.0),uGain,smoothstep(.25,1.0,l));        /* warm gain in the highlights: lit by a real sun, not a flat ambient */
 c=(c-.5)*uContrast+.5;float g=luma(c);c=mix(vec3(g),c,uSaturation);
 c=c/(1.0+max(vec3(0.0),c-1.0)*.6);                    /* highlight rolloff keeps saturated greens off neon */
 vec2 q=vUv-.5;float r2=dot(q,q)*2.0;c*=1.0-uVignette*smoothstep(.15,.78,r2);
 gl_FragColor=vec4(clamp(c,0.0,1.0),t.a);}`;
