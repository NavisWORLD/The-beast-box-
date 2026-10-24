#!/usr/bin/env python3
"""Convert Cosmo's planets pack (cosmo-study/universe/planets) to the web set in public/universe/planets.
Lossless webp for data maps (height, ocean mask, emissive), q90 for normals, q92 for roughness; wire layer skipped.
Usage: python3 scripts/planets-pack-convert.py /workspace/cosmo-study/universe/planets"""
import sys,os,shutil,json
from PIL import Image
src=sys.argv[1];out=os.path.join(os.path.dirname(__file__),'..','public','universe','planets');os.makedirs(out,exist_ok=True)
OPT={'normal':dict(quality=90),'rough':dict(quality=92)}
for t in ['temperate','desert','ice','volcanic','moon']:
  for res in ['2048x1024','512x256']:
    for k in ['albedo','clouds','normal','roughness','height','ocean_mask','emissive']:
      for ext in ('webp','png'):
        f=f'{src}/textures/{t}_{k}_{res}.{ext}'
        if os.path.exists(f):break
      else:continue
      o=f'{out}/{t}_{k}_{res}.webp'
      if f.endswith('.webp'):shutil.copy(f,o);continue
      im=Image.open(f);kw=dict(lossless=True)
      if k=='normal':kw=dict(quality=90)
      if k=='roughness':kw=dict(quality=92)
      im.save(o,'WEBP',**kw)
shutil.copy(f'{src}/models.json',f'{out}/models.json');shutil.copy(f'{src}/planet_assignments.json',f'{out}/planet_assignments.json')
for n in ['star_glow_white_256.png','star_glow_yellow_256.png','star_glow_orange_256.png','star_glow_blue_white_256.png']:shutil.copy(f'{src}/sun/{n}',f'{out}/{n}')
shutil.copy('/workspace/cosmo-study/livingworld/landforms/ocean/water_normal_1024.png',f'{out}/water_normal_1024.png')
