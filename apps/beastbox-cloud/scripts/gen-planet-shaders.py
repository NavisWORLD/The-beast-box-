#!/usr/bin/env python3
"""Builds lib/universe/planet-glsl.ts and planet-shading.mjs from Cosmo's pack (cosmo-study/universe/planets/glsl + models.json).
The GLSL is Cosmo's verbatim; ADDED lines are marked '// ADDED'. Usage: python3 scripts/gen-planet-shaders.py <pack dir>"""
import sys,os,json
P=sys.argv[1];G=P+'/glsl/';here=os.path.dirname(os.path.abspath(__file__))+'/../lib/universe/'
r=lambda n:open(G+n).read()
bd=r('biome_detail.glsl')
# Cosmo's handoff pack (planets/handoff): night lift + a tile-detail fade so sub-pixel tiles do not turn into stripes / grid / moire
nl=open(P+'/handoff/glsl/night_lift.glsl').read()
OLD='  return mix(baseAlbedo, baseAlbedo * mix(vec3(1.0), detail, 0.85), uDetailFade);'
assert OLD in bd
bd=bd.replace(OLD,'  vec2 tc = uv * vec2(uTilesPerRadius, uTilesPerRadius * 0.5);\n  float cyc = max(length(dFdx(tc)), length(dFdy(tc))); // ADDED: tile cycles per pixel\n  float aa = 1.0 - smoothstep(0.18, 0.55, cyc);        // ADDED: sub-pixel tiles repeat as stripes/grid, so fade to the base colour (the tile mean)\n  return mix(baseAlbedo, baseAlbedo * mix(vec3(1.0), detail, 0.85), uDetailFade * aa);')
common=r('common.glsl');term=r('terminator.glsl');ocean=r('ocean.glsl');cs=r('cloud_shadow.glsl');moon=r('phase_moon.glsl')
frag=r('planet_surface.frag').replace('precision highp float;\n','')
frag=frag.replace('uniform vec3  uParentDir;','uniform float uAlpha; // ADDED: LOD cross-fade\nuniform vec3 uOccC; uniform float uOccR; // ADDED: one analytic eclipse occluder (moon on planet, planet on moon); uOccR=0 is off\nuniform vec3  uParentDir;')
frag=frag.replace("  // night lights / lava / crystals","""  // ADDED: shore foam (the globe's foam rule): a lacy white band where the depth channel is ~0 (shore), lit by the sun
  if (ocean > 0.01) {
    float shore = 1.0 - smoothstep(0.0, 0.08, om.g);
    float lace = 0.6 + 0.4 * sin(uTime * 1.3 + vUv.x * 420.0 + vUv.y * 260.0) * sin(vUv.x * 310.0 - vUv.y * 470.0 - uTime * 0.9); // crossed low-frequency waves: lacy cells, no stripe moire when magnified
    col += uSunColor * shore * ocean * lace * 0.32 * tw;
  }
  // night lights / lava / crystals""")
frag=frag.replace("  vec3 col = alb * uSunColor * diff * shadow;","  if (uOccR > 0.0) shadow *= sphereShadow(vWorldPos, L, uOccC, uOccR, 0.012); // ADDED: eclipse\n  vec3 col = alb * uSunColor * diff * shadow;")
frag=frag.replace("gl_FragColor = vec4(linearToSrgb(col), 1.0);","gl_FragColor = vec4(linearToSrgb(col), uAlpha);")
assert 'uAlpha);' in frag and 'shore foam' in frag
OLDN='  col += alb * uSkyColor * (0.012 + 0.07 * uAtmo * tw);'
assert OLDN in frag
frag=frag.replace(OLDN,'  col += nightLiftGlobe(alb, Ng, L, V, uAtmo, tw);   // ADDED: Cosmo handoff night_lift.glsl (floor 0.105 night / 0.125 lit, cool tint)\n  col += alb * uSkyColor * (0.03 * uAtmo * tw);')
frag=frag.replace('  float ocean = om.r;','  float ocean = om.r;\n  if (uDetailFade > 0.001) alb = mix(biomeDetail(vUv, alb), alb, ocean); // ADDED: close-range biome tiles on land (ground hand-off, biome_detail.glsl)')
assert 'biomeDetail(vUv' in frag
# ADDED (terrain texture): slope rock, snow caps and a tile-derived bump on the near mesh. Pure texture lookups, no randomness.
TERRAIN='''
// ADDED: terrain texture layers (atlas tiles: id 8 = rock, id 9 = snow). uSnow 0..1 from the planet's recorded temperature.
uniform float uSnow; uniform sampler2D uHeight;
vec3 atlasTile(vec2 cell, vec2 tuv){ tuv = tuv * (254.0 / 256.0) + 1.0 / 256.0; return texture2D(uTileAtlas, (cell + tuv) * vec2(0.2, 0.25)).rgb; }
float atlasLum(vec2 cell, vec2 tuv){ return dot(atlasTile(cell, tuv), vec3(0.3, 0.59, 0.11)); }
'''
frag=frag.replace('  float nv = max(dot(Ng, V), 0.0);','''  if (uDetailFade > 0.001 && ocean < 0.95) {   // ADDED: terrain texture (rock on slopes, snow caps, micro relief)
    float land = 1.0 - ocean;
    float slope = clamp((1.0 - nm.z) * 4.0, 0.0, 1.0);
    float hgt = texture2D(uHeight, vUv).r;
    float lat = abs(vObjDir.y);
    vec2 tuv2 = fract(vUv * vec2(uTilesPerRadius * 2.3, uTilesPerRadius * 1.15));
    vec3 rockC = atlasTile(vec2(3.0, 1.0), tuv2);
    vec3 snowC = atlasTile(vec2(4.0, 1.0), tuv2);
    float rockAmt = smoothstep(0.22, 0.6, slope) * land * uDetailFade;
    alb = mix(alb, rockC * 0.85, rockAmt * 0.7);
    float line = 1.0 - 0.55 * uSnow;
    float cap = smoothstep(line - 0.1, line + 0.05, hgt + lat * 0.5 * uSnow - slope * 0.2) * smoothstep(0.02, 0.1, uSnow) * land * uDetailFade;
    alb = mix(alb, snowC * 1.05, cap);
    float id = floor(texture2D(uBiomeIdx, vUv).r * 255.0 + 0.5);
    vec2 cell = vec2(mod(id, 5.0), floor(id / 5.0));
    vec2 tuvb = fract(vUv * vec2(uTilesPerRadius * 4.0, uTilesPerRadius * 2.0));
    float e = 1.0 / 40.0;
    float l0 = atlasLum(cell, tuvb);
    vec2 gr = vec2(atlasLum(cell, fract(tuvb + vec2(e, 0.0))) - l0, atlasLum(cell, fract(tuvb + vec2(0.0, e))) - l0);
    N = normalize(N - (T * gr.x + B * gr.y) * 1.2 * uDetailFade * land * (1.0 - cap * 0.6));
    rough = mix(rough, 0.95, rockAmt);
  }
  float nv = max(dot(Ng, V), 0.0);''')
assert 'terrain texture (rock' in frag
FRAG='precision highp float;\n'+'\n'.join([common,term,nl,ocean,cs,moon,bd+TERRAIN,frag])
vert=r('planet_surface.vert')
vert=vert.replace("varying vec2 vUv;","uniform sampler2D uHeight; uniform float uDisp; uniform float uHasHeight; uniform float uSea; // ADDED: near-mesh displacement (h-0.25)*0.02, sea flat\nvarying vec2 vUv;",1)
vert=vert.replace("  vObjDir = normalize(position);","  float hh = uHasHeight > 0.5 ? texture2D(uHeight, uv).r : uSea;\n  float dh = hh - uSea; if (uSea < 0.3) dh = max(dh, 0.0); // ADDED: sea flat on water worlds, signed relief on the moon (centred 0.5)\n  vec3 pos = position * (1.0 + uDisp * dh * 0.02);\n  vObjDir = normalize(position);")
vert=vert.replace("vec4 w = modelMatrix * vec4(position, 1.0);","vec4 w = modelMatrix * vec4(pos, 1.0);")
VERT=vert
CLOUDF='''precision highp float;
varying vec2 vUv; varying vec3 vWorldN; varying vec3 vWorldPos;
uniform sampler2D uClouds; uniform vec3 uSunDir, uSunColor, uSkyColor, uTwilightColor; uniform float uAtmo, uAlpha;
void main(){ // ADDED: the NEAR cloud shell (ZOOM_GUIDE: second mesh at 1+cloudAlt, alpha = cloud.a), shading from cloud_shadow.glsl cloudComposite
  vec3 Ng = normalize(vWorldN); vec3 L = normalize(uSunDir);
  float width = mix(0.015, 0.12, uAtmo); float tw = terminatorWeight(Ng, L, width); float ndl = dot(Ng, L);
  vec4 cl = texture2D(uClouds, vUv);
  vec3 tint = twilightBand(Ng, L, width, uTwilightColor, 0.5 * uAtmo);
  vec3 col = cloudComposite(vec3(0.0), vec4(cl.rgb, 1.0), uSunColor, tw, ndl, uSkyColor, tint);
  gl_FragColor = vec4(linearToSrgb(col), cl.a * uAlpha);
}'''
CLOUDF=CLOUDF.replace('precision highp float;\n','precision highp float;\n'+common+'\n'+term+'\n'+cs+'\n',1)
am=r('atmosphere_rim.glsl');am=am[am.index('precision highp float;'):]
ATMOF=am.replace('precision highp float;\n','precision highp float;\n'+common+'\n',1)
ATMOV='varying vec3 vWorld; void main(){ vec4 w = modelMatrix * vec4(position,1.0); vWorld = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }'
def js(s):return '`'+s.replace('\\','\\\\').replace('`','\\`').replace('${','\\${')+'`'
open(here+'planet-glsl.ts','w').write('// GENERATED by scripts/gen-planet-shaders.py from Cosmo\'s planets pack (glsl/). Do not edit by hand.\n/* eslint-disable */\n'+
 f'export const PLANET_VERT={js(VERT)};\nexport const PLANET_FRAG={js(FRAG)};\nexport const CLOUD_FRAG={js(CLOUDF)};\nexport const ATMO_VERT={js(ATMOV)};\nexport const ATMO_FRAG={js(ATMOF)};\n')
m=json.load(open(P+'/models.json'));out={}
for t,v in m['types'].items():
  out[t]=dict(shading=v['shading'],clouds=v.get('clouds'),atmosphere=(v.get('atmosphere') or {}).get('uniforms'),shell=(v.get('atmosphere') or {}).get('shell_radius_frac'))
open(here+'planet-shading.mjs','w').write('// GENERATED from Cosmo\'s planets pack models.json (shading, clouds, atmosphere per type).\nexport const PLANET_SHADING='+json.dumps(out,indent=1)+';\nexport const PLANET_LOD='+json.dumps(m['lod'])+';\n')
